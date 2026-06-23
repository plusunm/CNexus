"""Tests for direct image CLIP embedding and vector index."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.asset_vector_index import AssetVectorIndex, hash_embedding  # noqa: E402
from core.clip_embed import ClipEmbedder  # noqa: E402


def _tiny_png() -> bytes:
    # 1x1 red PNG
    return bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
        "de0000000c4944415408d763f8cfc0000000030001ae0f9e7a000000004945"
        "4e44ae426082"
    )


def main():
    clip = ClipEmbedder(enabled=True)
    vec_a, backend_a = clip.embed_image(_tiny_png())
    assert vec_a and backend_a in ("clip_onnx_image", "visual_grid", "visual_bytes"), backend_a

    with tempfile.TemporaryDirectory() as tmp:
        index_path = os.path.join(tmp, "vector_index.json")
        idx = AssetVectorIndex(
            index_path,
            embed_fn=lambda text: hash_embedding(text, dim=64),
            clip_embedder=clip,
        )

        meta_code = {"id": "a" * 64, "type": "code", "filename": "auth.py", "summary": "user login handler"}
        meta_img = {"id": "b" * 64, "type": "image", "filename": "red.png"}

        idx.index_asset(meta_code["id"], meta_code)
        idx.index_asset(meta_img["id"], meta_img, image_bytes=_tiny_png())

        code_hits = idx.search("login authentication", kind="code", limit=5)
        assert code_hits and code_hits[0]["asset_id"] == meta_code["id"], code_hits

        image_hits = idx.search(image_bytes=_tiny_png(), kind="image", limit=5)
        assert image_hits and image_hits[0]["asset_id"] == meta_img["id"], image_hits
        assert image_hits[0]["embed_mode"] == "clip_image"

        text_on_image = idx.search("red pixel", kind="image", limit=5)
        assert text_on_image == [] or clip.unified_space

        status = idx.status()
        assert status["clip_image_count"] == 1, status

        print("image_backend:", backend_a)
        print("image_hits:", len(image_hits))
        print("\nCLIP EMBED TEST PASSED")


if __name__ == "__main__":
    main()
