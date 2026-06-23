"""Tests for asset vector index."""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from core.asset_vector_index import AssetVectorIndex, hash_embedding  # noqa: E402
from core.clip_embed import ClipEmbedder  # noqa: E402


def main():
    with tempfile.TemporaryDirectory() as tmp:
        index_path = os.path.join(tmp, "vector_index.json")
        idx = AssetVectorIndex(index_path, embed_fn=lambda text: hash_embedding(text, dim=64))
        clip = ClipEmbedder(enabled=True)
        idx = AssetVectorIndex(
            index_path,
            embed_fn=lambda text: hash_embedding(text, dim=64),
            clip_embedder=clip,
        )

        meta_a = {"id": "a" * 64, "type": "code", "filename": "auth.py", "summary": "user login handler"}
        meta_b = {"id": "b" * 64, "type": "image", "filename": "diagram.png"}

        idx.index_asset(meta_a["id"], meta_a)
        idx.index_asset(meta_b["id"], meta_b, image_bytes=b"\x89PNG\r\n\x1a\nfake-image-bytes")

        hits = idx.search("login authentication", kind="code", limit=5)
        assert hits, hits
        assert hits[0]["asset_id"] == meta_a["id"]

        hits_img = idx.search(image_bytes=b"\x89PNG\r\n\x1a\nfake-image-bytes", kind="image", limit=5)
        assert hits_img and hits_img[0]["asset_id"] == meta_b["id"]

        print("semantic_hits:", len(hits))
        print("\nASSET VECTOR INDEX TEST PASSED")


if __name__ == "__main__":
    main()
