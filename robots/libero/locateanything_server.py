"""RPC server owning the local LocateAnything-3B open-vocabulary localiser.

Run manually with::

    LOCATEANYTHING_MODEL_PATH=/path/to/LocateAnything-3B \
        python -m robots.libero.locateanything_server \
        --transport http --host 127.0.0.1 --port 8115

The service exposes a ``locate`` RPC method over either HTTP or socket
transport, mirroring ``sam3_server``'s contract (same ``RpcFacade``, same
``healthz``, same base64-image wire format).

What it does NOT mirror: SAM3 returns a pixel mask, LocateAnything returns
boxes and points. There is no mask in the response and it is therefore not a
drop-in ``segment`` backend -- the geometry layer's ``_mask_to_world`` reduces
mask pixels, and ``rim``/``interior``/``looks_hollow`` are mask-derived. This
server answers "where is X, and is there more than one of it", which is the
question SAM3's identity failures are about.

Two properties of the underlying model drive the design:

- **Coordinates are normalised token indices, not pixels.** The model emits
  ``<box><x1><x2><y1><y2></box>`` where each coordinate is a discrete token in
  ``<0>..<1000>``. Note the ordering: both x values precede both y values,
  which is NOT the ``x1,y1,x2,y2`` the model card's prose implies. This server
  converts to pixel coordinates on the way out so callers never see the
  convention.
- **Multiple instances come back for one query, by design.** A query names a
  category (``"bottle"``) or a referring expression (``"the dark bottle"``) and
  the model returns every match it finds. That is the useful part here: a
  caller can see "three bottles at these three places" rather than one
  collapsed answer, so instance multiplicity is reported, never reduced.
"""

from __future__ import annotations

import argparse
import base64
import io
import logging
import os
import re
import threading
from typing import Any

from pydantic import BaseModel, Field, model_validator

from rpent.utils.logging import get_logger
from rpent.utils.rpc import RpcFacade

logger = get_logger("locateanything_server")

# The model's coordinate tokens span <0>..<1000> inclusive.
COORD_MAX = 1000.0

# Category separator in a multi-category query, per the release code's
# batch_infer.py ("person</c>car").
CATEGORY_SEP = "</c>"


class LocateRequest(BaseModel):
    """Wire request for open-vocabulary localisation."""

    image_base64: str
    query: str
    max_instances: int = Field(default=20, ge=1, le=200)
    mode: str = Field(default="box", pattern="^(box|point)$")
    max_new_tokens: int = Field(default=2048, ge=16, le=8192)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    repetition_penalty: float = Field(default=1.1, ge=1.0, le=2.0)

    @model_validator(mode="after")
    def _clean_query(self) -> "LocateRequest":
        if not self.query or not self.query.strip():
            raise ValueError("query must be a non-empty string")
        self.query = self.query.strip()
        return self


class Instance(BaseModel):
    """One located instance, in pixel coordinates of the input image."""

    label: str
    box: list[float] | None = None      # [x1, y1, x2, y2] pixels
    point: list[float] | None = None    # [x, y] pixels
    center: list[float]                 # [x, y] pixels -- box centre or the point
    box_normalised: list[float] | None = None   # [x1, y1, x2, y2] in 0..1


class LocateResponse(BaseModel):
    """Wire response carrying every instance the model reported."""

    found: bool
    n_instances: int = 0
    instances: list[Instance] = Field(default_factory=list)
    labels: list[str] = Field(default_factory=list)
    image_size: list[int] | None = None   # [width, height]
    raw_response: str | None = None
    reason: str | None = None


def _decode_image(image_base64: str):
    from PIL import Image

    raw = base64.b64decode(image_base64)
    return Image.open(io.BytesIO(raw)).convert("RGB")


# The model writes each coordinate as its own token, e.g. "<box><123><456><78><90></box>".
_BOX_BLOCK = re.compile(r"<box>(.*?)</box>", re.DOTALL)
_COORD_TOKEN = re.compile(r"<(\d{1,4})>")


def parse_response(text: str, width: int, height: int) -> tuple[list[dict], list[str]]:
    """Parse the model's raw text into pixel-space instances.

    The response interleaves label text with ``<box>`` blocks. Each block holds
    either four coordinate tokens (a box, ordered ``x1 x2 y1 y2``) or two (a
    point, ordered ``x y``); ``<box>none</box>`` means the model found nothing
    for the preceding label.

    Labels are carried forward: the model emits a label once and may follow it
    with several boxes, one per instance.
    """
    instances: list[dict] = []
    labels: list[str] = []
    cursor = 0
    current_label = ""

    for match in _BOX_BLOCK.finditer(text):
        # Text between the previous block and this one names what follows.
        gap = text[cursor:match.start()]
        cleaned = _clean_label(gap)
        if cleaned:
            current_label = cleaned
            if cleaned not in labels:
                labels.append(cleaned)
        cursor = match.end()

        body = match.group(1).strip()
        if "none" in body.lower():
            continue

        coords = [int(v) for v in _COORD_TOKEN.findall(body)]
        if not coords:
            # Fall back to bare comma-separated numbers, which the autoregressive
            # path can produce instead of coordinate tokens.
            coords = [int(round(float(v))) for v in re.findall(r"-?\d+(?:\.\d+)?", body)]

        if len(coords) >= 4:
            # Token order is x1, x2, y1, y2 -- both x before both y.
            x1, x2, y1, y2 = coords[0], coords[1], coords[2], coords[3]
            nx1, nx2 = min(x1, x2) / COORD_MAX, max(x1, x2) / COORD_MAX
            ny1, ny2 = min(y1, y2) / COORD_MAX, max(y1, y2) / COORD_MAX
            px1, px2 = nx1 * width, nx2 * width
            py1, py2 = ny1 * height, ny2 * height
            instances.append({
                "label": current_label,
                "box": [px1, py1, px2, py2],
                "point": None,
                "center": [(px1 + px2) / 2.0, (py1 + py2) / 2.0],
                "box_normalised": [nx1, ny1, nx2, ny2],
            })
        elif len(coords) >= 2:
            px = coords[0] / COORD_MAX * width
            py = coords[1] / COORD_MAX * height
            instances.append({
                "label": current_label,
                "box": None,
                "point": [px, py],
                "center": [px, py],
                "box_normalised": None,
            })

    return instances, labels


def _dedupe(instances: list[dict], *, tol_px: float = 2.0) -> list[dict]:
    """Drop repeated boxes, keeping first occurrence and preserving order.

    Greedy decoding on this model reliably degenerates: after emitting the real
    instances it repeats the last box until the token budget runs out. Those
    repeats are an artefact of decoding, not detections, and leaving them in
    would inflate the instance count -- which is the one number a caller is
    meant to trust for "is this noun ambiguous".
    """
    kept: list[dict] = []
    for inst in instances:
        cx, cy = inst["center"]
        if any(abs(cx - k["center"][0]) <= tol_px and abs(cy - k["center"][1]) <= tol_px
               and inst["label"] == k["label"]
               for k in kept):
            continue
        kept.append(inst)
    return kept


def _clean_label(fragment: str) -> str:
    """Strip chat-template and structural tokens from a label fragment."""
    text = re.sub(r"<\|[^|]*\|>", " ", fragment)   # <|im_start|> etc.
    text = re.sub(r"</?ref>", " ", text)
    text = re.sub(r"<[^>]*>", " ", text)           # any remaining tag
    text = text.replace(CATEGORY_SEP, " ")
    text = re.sub(r"[\s,;:.]+", " ", text)
    return text.strip()


class LocateAnythingEngine:
    """Own the model and serve one localisation request at a time.

    Serialised with a lock for the same reason ``Sam3Engine`` is: a turn's tool
    calls run concurrently in the caller's process, and a single CUDA model is
    not reentrant.
    """

    def __init__(self, model_path: str, *, attn: str = "sdpa", device: str | None = None):
        self._model_path = model_path
        self._attn = attn
        self._device = device
        self._lock = threading.Lock()
        self._model = None
        self._processor = None

    def load(self) -> None:
        """Load weights and processor. Called once, before serving."""
        import torch
        from transformers import AutoConfig, AutoModel, AutoProcessor

        logger.info("loading LocateAnything checkpoint from %s (attn=%s)",
                    self._model_path, self._attn)
        # The release ships custom modelling code in the checkpoint directory;
        # trust_remote_code is required to pick it up.
        self._processor = AutoProcessor.from_pretrained(
            self._model_path, trust_remote_code=True
        )
        # The bundled Qwen2 code implements only 'magi' (its own CUDA kernel,
        # not built here) and 'sdpa'; anything else -- including transformers'
        # 'eager' default -- reaches a NotImplementedError inside the decoder
        # layer at generate time, not at load time. Pin it on the config, which
        # is what the modelling code actually reads.
        config = AutoConfig.from_pretrained(self._model_path, trust_remote_code=True)
        config._attn_implementation = self._attn
        for sub in ("text_config", "llm_config", "vision_config"):
            inner = getattr(config, sub, None)
            if inner is not None and hasattr(inner, "_attn_implementation"):
                inner._attn_implementation = self._attn
        self._model = AutoModel.from_pretrained(
            self._model_path,
            config=config,
            trust_remote_code=True,
            torch_dtype=torch.bfloat16,
        )
        device = self._device or ("cuda" if torch.cuda.is_available() else "cpu")
        self._model = self._model.to(device).eval()
        self._device_resolved = device
        logger.info("LocateAnything ready on %s", device)

    def locate(self, request: LocateRequest) -> LocateResponse:
        """Localise every instance matching ``request.query``."""
        import torch

        image = _decode_image(request.image_base64)
        width, height = image.size

        with self._lock:
            try:
                text = self._generate(image, request)
            except Exception as exc:                      # noqa: BLE001
                logger.exception("locate failed")
                return LocateResponse(
                    found=False,
                    image_size=[width, height],
                    reason=f"{type(exc).__name__}: {exc}",
                )

        instances, labels = parse_response(text, width, height)
        instances = _dedupe(instances)
        if request.mode == "point":
            for inst in instances:
                if inst["point"] is None and inst["box"] is not None:
                    inst["point"] = list(inst["center"])
        instances = instances[: request.max_instances]

        if not instances:
            return LocateResponse(
                found=False,
                image_size=[width, height],
                raw_response=text,
                labels=labels,
                reason="model reported no box for this query",
            )
        return LocateResponse(
            found=True,
            n_instances=len(instances),
            instances=[Instance(**inst) for inst in instances],
            labels=labels,
            image_size=[width, height],
            raw_response=text,
        )

    def _generate(self, image, request: LocateRequest) -> str:
        """Run the model and return its raw decoded text."""
        import torch

        messages = [{
            "role": "user",
            "content": [
                {"type": "image"},
                {"type": "text", "text": request.query},
            ],
        }]
        prompt = self._processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._processor(
            text=[prompt], images=[image], return_tensors="pt"
        ).to(self._device_resolved)

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": request.max_new_tokens,
            # The release's modelling code asserts on this: its parallel box
            # decoding path indexes the KV cache directly and refuses to run
            # without it.
            "use_cache": True,
            # 'hybrid' decodes boxes in parallel and falls back to
            # autoregressive on a malformed block; 'fast' never falls back.
            "generation_mode": "hybrid",
        }
        # The release's own CLI defaults to sampling with a repetition penalty;
        # pure greedy decoding degenerates into repeating the last box.
        if request.temperature > 0.0:
            gen_kwargs["do_sample"] = True
            gen_kwargs["temperature"] = request.temperature
            gen_kwargs["top_p"] = 0.9
        gen_kwargs["repetition_penalty"] = request.repetition_penalty

        # This is the checkpoint's own generate(), not HF's: it takes the
        # tokenizer explicitly, consumes image_grid_hws from the processor, and
        # returns DECODED TEXT rather than token ids -- so there is no decode
        # step and no prompt to strip here.
        with torch.inference_mode():
            out = self._model.generate(
                tokenizer=self._processor.tokenizer,
                **inputs,
                **gen_kwargs,
            )

        if isinstance(out, str):
            return out
        # Defensive: a future revision returning ids should still work.
        if hasattr(out, "ndim"):
            seq = out[0] if out.ndim == 2 else out
            return self._processor.tokenizer.decode(seq, skip_special_tokens=False)
        return str(out)


class LocateAnythingFacade(RpcFacade):
    """Expose :class:`LocateAnythingEngine` through the shared RPC transports."""

    def __init__(self, engine: LocateAnythingEngine) -> None:
        super().__init__()
        self._engine = engine

    def _dispatch(self, method: str, args: tuple, kwargs: dict) -> Any:
        if method == "locate":
            return self.locate(*args, **kwargs)
        raise ValueError(f"unknown RPC method: {method!r}")

    def locate(
        self,
        image_base64: str,
        *,
        query: str,
        max_instances: int = 20,
        mode: str = "box",
        max_new_tokens: int = 2048,
        temperature: float = 0.0,
        repetition_penalty: float = 1.1,
    ) -> dict[str, Any]:
        """Validate the wire request, run the engine, return a plain dict."""
        request = LocateRequest(
            image_base64=image_base64,
            query=query,
            max_instances=max_instances,
            mode=mode,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            repetition_penalty=repetition_penalty,
        )
        return self._engine.locate(request).model_dump()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--transport", choices=["http", "socket"], default="http")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8115)
    ap.add_argument("--model-path", default=os.environ.get("LOCATEANYTHING_MODEL_PATH"))
    ap.add_argument("--attn", default=os.environ.get("LOCATEANYTHING_ATTN", "sdpa"),
                    choices=["sdpa", "magi"],
                    help="attention backend. Only these two are implemented by "
                         "the bundled modelling code; 'magi' needs its CUDA "
                         "kernel built, which is not done here, so 'sdpa' is "
                         "the working default")
    ap.add_argument("--device", default=None)
    ap.add_argument("--cuda-device", default=None,
                    help="pin CUDA_VISIBLE_DEVICES before torch initialises")
    ap.add_argument("--parent-watch", action="store_true",
                    help="exit when the parent process dies (matches sam3_server)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
    if args.cuda_device is not None:
        target = str(args.cuda_device)
        prev = os.environ.get("CUDA_VISIBLE_DEVICES")
        if prev is not None and prev != target:
            logging.warning(
                "CUDA_VISIBLE_DEVICES=%s is already set; overriding with --cuda-device=%s",
                prev, args.cuda_device,
            )
        os.environ["CUDA_VISIBLE_DEVICES"] = target

    if not args.model_path:
        raise SystemExit(
            "set --model-path or LOCATEANYTHING_MODEL_PATH to the "
            "LocateAnything-3B checkpoint directory"
        )

    engine = LocateAnythingEngine(args.model_path, attn=args.attn, device=args.device)
    engine.load()
    facade = LocateAnythingFacade(engine)
    facade.serve(transport=args.transport, host=args.host, port=args.port,
                 parent_watch=args.parent_watch)


if __name__ == "__main__":
    main()
