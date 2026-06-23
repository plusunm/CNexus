"""Direct image embedding for multimodal asset search (CLIP ONNX or visual fallback)."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import struct
from io import BytesIO
from typing import List, Optional, Tuple
from urllib import error as urlerror
from urllib import request as urlrequest


def _env_truthy(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() not in ("0", "false", "no", "")


def _l2_normalize(vector: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm <= 0:
        return vector
    return [v / norm for v in vector]


def _byte_histogram_embed(data: bytes, dim: int = 256) -> List[float]:
    vec = [0.0] * dim
    if not data:
        return vec
    for byte in data[:65536]:
        vec[byte % dim] += 1.0
    vec[dim // 2] += math.log1p(len(data))
    return _l2_normalize(vec)


def _pil_grid_embed(data: bytes, dim: int = 512) -> Optional[List[float]]:
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        image = Image.open(BytesIO(data)).convert("RGB")
        image = image.resize((16, 16))
        pixels = list(image.getdata())
        vec = []
        for r, g, b in pixels:
            vec.extend([r / 255.0, g / 255.0, b / 255.0])
        if len(vec) < dim:
            vec.extend([0.0] * (dim - len(vec)))
        return _l2_normalize(vec[:dim])
    except Exception:
        return None


def _onnx_clip_embed(data: bytes, model_path: str) -> Optional[List[float]]:
    try:
        import numpy as np
        import onnxruntime as ort
        from PIL import Image
    except ImportError:
        return None
    if not model_path or not os.path.isfile(model_path):
        return None
    try:
        image = Image.open(BytesIO(data)).convert("RGB").resize((224, 224))
        arr = np.asarray(image).astype("float32") / 255.0
        arr = arr.transpose(2, 0, 1)[None, :, :, :]
        session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: arr})
        vector = outputs[0].reshape(-1).astype("float32").tolist()
        return _l2_normalize(vector)
    except Exception:
        return None


def _onnx_clip_text_embed(text: str, model_path: str) -> Optional[List[float]]:
    try:
        import onnxruntime as ort
    except ImportError:
        return None
    if not model_path or not os.path.isfile(model_path):
        return None
    try:
        session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: [str(text or "")]})
        vector = outputs[0].reshape(-1).astype("float32").tolist()
        return _l2_normalize(vector)
    except Exception:
        return None


class ClipEmbedder:
    """
    Direct image vectors for asset indexing.
    Prefers CLIP ONNX (image + optional text encoders in the same space).
    Falls back to PIL grid / byte histogram without description text.
    """

    def __init__(
        self,
        *,
        image_onnx_path: Optional[str] = None,
        text_onnx_path: Optional[str] = None,
        ollama_base: Optional[str] = None,
        ollama_text_model: Optional[str] = None,
        enabled: Optional[bool] = None,
    ):
        self.image_onnx_path = image_onnx_path or os.environ.get("CNEXUS_CLIP_IMAGE_ONNX", "")
        self.text_onnx_path = text_onnx_path or os.environ.get("CNEXUS_CLIP_TEXT_ONNX", "")
        self.ollama_base = (ollama_base or os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")).rstrip("/")
        self.ollama_text_model = ollama_text_model or os.environ.get("CNEXUS_CLIP_TEXT_MODEL", "nomic-embed-text")
        self.enabled = enabled if enabled is not None else _env_truthy("CNEXUS_CLIP_ENABLE", True)
        self._last_backend = "disabled"

    @property
    def unified_space(self) -> bool:
        return bool(self.image_onnx_path and self.text_onnx_path and os.path.isfile(self.text_onnx_path))

    def embed_image(self, data: bytes) -> Tuple[List[float], str]:
        if not self.enabled:
            return [], "disabled"
        raw = bytes(data or b"")
        if not raw:
            return [], "empty"

        vector = _onnx_clip_embed(raw, self.image_onnx_path)
        if vector:
            self._last_backend = "clip_onnx_image"
            return vector, self._last_backend

        vector = _pil_grid_embed(raw, dim=512)
        if vector:
            self._last_backend = "visual_grid"
            return vector, self._last_backend

        self._last_backend = "visual_bytes"
        return _byte_histogram_embed(raw, dim=512), self._last_backend

    def embed_text(self, text: str) -> Tuple[List[float], str]:
        if not self.enabled:
            return [], "disabled"
        text = str(text or "").strip()
        if not text:
            return [], "empty"

        if self.unified_space:
            vector = _onnx_clip_text_embed(text, self.text_onnx_path)
            if vector:
                self._last_backend = "clip_onnx_text"
                return vector, self._last_backend

        vector = self._ollama_text_embed(text)
        if vector:
            self._last_backend = "ollama_text"
            return vector, self._last_backend

        self._last_backend = "text_hash"
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vec = [b / 255.0 for b in digest] * 16
        return _l2_normalize(vec[:512]), self._last_backend

    def _ollama_text_embed(self, text: str) -> Optional[List[float]]:
        body = json.dumps({"model": self.ollama_text_model, "input": text}).encode("utf-8")
        req = urlrequest.Request(
            f"{self.ollama_base}/api/embed",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=12) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
        except (urlerror.URLError, urlerror.HTTPError, TimeoutError, json.JSONDecodeError):
            return None
        rows = payload.get("embeddings") or []
        if rows and isinstance(rows[0], list):
            return _l2_normalize([float(v) for v in rows[0]])
        if isinstance(payload.get("embedding"), list):
            return _l2_normalize([float(v) for v in payload["embedding"]])
        return None

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "unified_space": self.unified_space,
            "image_onnx": bool(self.image_onnx_path and os.path.isfile(self.image_onnx_path)),
            "text_onnx": bool(self.text_onnx_path and os.path.isfile(self.text_onnx_path)),
            "last_backend": self._last_backend,
            "ollama_text_model": self.ollama_text_model,
        }
