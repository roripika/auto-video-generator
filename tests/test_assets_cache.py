from __future__ import annotations

from pathlib import Path

from src.assets.cache import AssetCache
from src.assets.types import AssetKind, RemoteAsset


def test_asset_cache_store_and_retrieve(tmp_path: Path) -> None:
    cache = AssetCache(base_dir=tmp_path / "cache")
    asset = RemoteAsset(
        id="123",
        provider="pexels",
        kind=AssetKind.IMAGE,
        url="https://example.com/sample.jpg",
        keywords=["test"],
    )

    stored = cache.store_binary("テスト", asset, b"abc", extension=".jpg")
    assert stored.path.exists()
    assert stored.metadata_path.exists()

    cached = cache.get_cached("テスト", asset)
    assert cached is not None
    assert cached.path.read_bytes() == b"abc"
