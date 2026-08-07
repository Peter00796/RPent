"""Transport-independent client for RPent's LocateAnything localisation service.

Mirrors :mod:`rpent.utils.sam3_client`: same ``RpcClient`` injection, same
``image_path``-in / dataclass-out shape, same ``[row, col]`` image convention
for every pixel coordinate it hands back.

The convention conversion matters and is done here, once. The model speaks
normalised ``x, y``; the server converts to pixel ``x, y``; this client converts
to ``[row, col]`` so a caller can index a world map as ``world[row, col]``
without knowing anything about the model's coordinate order.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rpent.utils.rpc import RpcClient


@dataclass(frozen=True)
class LocatedInstance:
    """One located instance, in RPent's ``[row, col]`` image convention."""

    label: str
    center_rc: list[float]                    # [row, col]
    box_rc: list[float] | None = None         # [row_min, col_min, row_max, col_max]
    box_xyxy: list[float] | None = None       # [x1, y1, x2, y2], as the server sent it

    @property
    def center_row_col_int(self) -> list[int]:
        """Nearest integer ``[row, col]``, ready to index an array."""
        return [int(round(self.center_rc[0])), int(round(self.center_rc[1]))]


@dataclass(frozen=True)
class LocateResult:
    """Every instance the model reported for one query.

    ``n_instances`` is deliberately not reduced to a single best answer. A query
    for "bottle" in a scene with three bottles returns three instances, and that
    multiplicity is the signal a caller needs to detect an ambiguous noun.
    """

    found: bool
    n_instances: int = 0
    instances: list[LocatedInstance] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    image_size: tuple[int, int] | None = None   # (width, height)
    raw_response: str | None = None
    reason: str | None = None


class LocateAnythingClient:
    """Client wrapping the LocateAnything service over any :class:`RpcClient`."""

    def __init__(self, client: RpcClient, *, timeout_s: float = 180.0) -> None:
        self._client = client
        self._timeout_s = timeout_s

    def locate(
        self,
        image_path: str | Path,
        *,
        query: str,
        max_instances: int = 20,
        mode: str = "box",
        max_new_tokens: int = 2048,
        temperature: float = 0.0,
        repetition_penalty: float = 1.1,
    ) -> LocateResult:
        """Locate every instance matching ``query`` in ``image_path``.

        ``query`` is a category name ("bottle"), a referring expression ("the
        dark bottle on the left"), or several categories joined by ``</c>``
        ("bottle</c>basket"). Returned coordinates use ``[row, col]``.
        """
        if not query or not query.strip():
            raise ValueError("locate requires a non-empty query")
        if mode not in ("box", "point"):
            raise ValueError("mode must be 'box' or 'point'")

        image_bytes = Path(image_path).read_bytes()
        body: dict[str, Any] = {
            "image_base64": base64.b64encode(image_bytes).decode("ascii"),
            "query": query.strip(),
            "max_instances": int(max_instances),
            "mode": mode,
            "max_new_tokens": int(max_new_tokens),
            "temperature": float(temperature),
            "repetition_penalty": float(repetition_penalty),
        }

        payload = self._client.call("locate", kwargs=body, timeout_s=self._timeout_s)
        return self._parse(payload)

    @staticmethod
    def _parse(payload: dict[str, Any]) -> LocateResult:
        """Convert the wire payload to ``[row, col]`` dataclasses."""
        size = payload.get("image_size") or None
        instances: list[LocatedInstance] = []
        for raw in payload.get("instances") or []:
            cx, cy = raw["center"]                  # server sends pixel x, y
            box_rc = None
            box = raw.get("box")
            if box:
                x1, y1, x2, y2 = box
                box_rc = [y1, x1, y2, x2]           # row_min, col_min, row_max, col_max
            instances.append(LocatedInstance(
                label=raw.get("label") or "",
                center_rc=[cy, cx],                 # row = y, col = x
                box_rc=box_rc,
                box_xyxy=box,
            ))
        return LocateResult(
            found=bool(payload.get("found")),
            n_instances=int(payload.get("n_instances") or len(instances)),
            instances=instances,
            labels=list(payload.get("labels") or []),
            image_size=(int(size[0]), int(size[1])) if size else None,
            raw_response=payload.get("raw_response"),
            reason=payload.get("reason"),
        )
