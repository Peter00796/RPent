"""The ``LiberoPrimitives`` core: env/policy handles, observation cache, recording.

The primitives themselves live next door, split by kind — scripted OSC motion in
:mod:`robots.libero.tools.motion`, Pi0.5 closed-loop skills in
:mod:`robots.libero.tools.vla`, and SAM3 segmentation in
:mod:`robots.libero.tools.perception`. This module supplies what all three need:
the env/model clients, the cached observation fields refreshed by
:meth:`LiberoPrimitives.set_obs`, the cancellation-checked ``_step_env``, and the
``_vlm_chunk`` policy rollout.
"""
from __future__ import annotations

import os
from collections.abc import Callable

import imageio.v2 as imageio
import numpy as np

from robots.libero.env_client import LiberoEnvClient
from rpent.utils.sam3_client import Sam3Client
from rpent.utils.vla_client import VLAClient

from robots.libero.tools.motion import MotionMixin
from robots.libero.tools.perception import SegmentMixin
from robots.libero.tools.vla import VlaMixin


class LiberoPrimitives(MotionMixin, VlaMixin, SegmentMixin):
    """Wraps a single-env LIBERO-shaped env + VLA policy with primitive-
    level methods.

    ``pi0_pick`` and ``pi0_doubled`` override ``obs['task_descriptions']``
    with a sub-instruction. ``move_to`` and friends are scripted (no VLM
    call) and drive the underlying OSC controller directly.
    """

    def __init__(
        self,
        env: LiberoEnvClient,
        model: VLAClient,
        sam3_client: Sam3Client,
        check_cancelled: Callable[[], None],
    ):
        self.env = env
        self.model = model
        self._sam3_client = sam3_client
        self._check_cancelled = check_cancelled
        self._last_obs = None
        self._last_obs_eef_pos = None
        self._last_obs_eef_z = None
        self._last_obs_gripper = None
        # Per-env-step frame buffer for diagnostic video rendering.
        # Toggled via start_recording() / stop_recording_and_save().
        self._recording = False
        self._frames = []

    def start_recording(self):
        self._recording = True
        self._frames = []

    def record_frame(self, obs):
        """Append one agentview frame extracted from ``obs`` to the buffer."""
        self._frames.append(np.ascontiguousarray(np.asarray(obs["main_images"])))

    def recorded_frame_count(self) -> int:
        return len(self._frames)

    def stop_recording_and_save(self, path: str, fps: int = 20):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        n = len(self._frames)
        if n > 0:
            imageio.mimwrite(path, self._frames, fps=fps)
        self._recording = False
        self._frames = []
        return {"path": path, "n_frames": n}

    def save_frame_slice(self, start: int, path: str, fps: int = 20):
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        frames = list(self._frames[int(start):])
        n = len(frames)
        if n > 0:
            imageio.mimwrite(path, frames, fps=fps)
        return {"path": path, "n_frames": n, "fps": fps}

    def set_obs(self, obs):
        self._last_obs = obs
        states_arr = np.asarray(obs["states"])
        self._last_obs_eef_pos = np.asarray(states_arr[:3], dtype=np.float32)
        self._last_obs_eef_z = float(self._last_obs_eef_pos[2])
        # robosuite 2f85: qpos[6] in [~0, ~0.04], qpos[7] in [~-0.04, ~0].
        # Use |qpos[6]| + |qpos[7]| ≈ finger separation proxy.
        # When open ≈ 0.08; when closed ≈ 0.
        gp = np.asarray(states_arr[6:8], dtype=np.float32)
        self._last_obs_gripper = float(abs(gp[0]) + abs(gp[1]))

    def reset(self):
        obs, info = self.env.reset()
        self.set_obs(obs)
        return self._last_obs, info

    def _step_env(self, action) -> None:
        """Execute one env action between cancellation checkpoints."""
        self._check_cancelled()
        obs, _r, _t, _tr, _i = self.env.step(action)
        self.set_obs(obs)
        if self._recording:
            self.record_frame(obs)

    def _vlm_chunk(self, instruction: str):
        """One model forward + ``chunk_size`` env steps. Overrides prompt."""
        self._check_cancelled()
        original_task = self._last_obs.get("task_descriptions")
        try:
            self._last_obs["task_descriptions"] = instruction
            self._last_obs.setdefault("extra_view_images", None)

            actions, _ = self.model.predict_action_batch(self._last_obs, mode="eval")
            self._check_cancelled()

            if not self._recording:
                chunk_obs,  _r, _t, _tr, _i = self.env.chunk_step(actions)
                obs = chunk_obs[-1] if self.env.return_all_frames else chunk_obs
            else:
                chunk_obs,  _r, _t, _tr, _i = self.env.chunk_step(
                    actions, return_all_frames=True
                )
                for obs in chunk_obs:
                    self.record_frame(obs)
                obs = chunk_obs[-1]
            self.set_obs(obs)
            return self._last_obs
        finally:
            if original_task is not None:
                self._last_obs["task_descriptions"] = original_task
