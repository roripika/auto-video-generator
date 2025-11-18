from __future__ import annotations

import logging
from typing import List, Optional

from .cache import AssetCache
from .clients import PexelsClient, PixabayClient
from .generators import StableDiffusionClient
from .types import AssetKind, DownloadedAsset, RemoteAsset


class AssetFetcher:
    """High-level orchestration for searching/downloading background assets."""

    def __init__(
        self,
        *,
        cache: Optional[AssetCache] = None,
        pexels: Optional[PexelsClient] = None,
        pixabay: Optional[PixabayClient] = None,
        ai_generator: Optional[StableDiffusionClient] = None,
    ) -> None:
        self.cache = cache or AssetCache()
        self.pexels = pexels or PexelsClient()
        self.pixabay = pixabay or PixabayClient()
        self.ai_generator = ai_generator
        self.logger = logging.getLogger(self.__class__.__name__)

    def fetch(
        self,
        keyword: str,
        *,
        kind: AssetKind = AssetKind.VIDEO,
        max_results: int = 3,
        allow_ai: bool = True,
        provider_order: Optional[list[str]] = None,
    ) -> List[DownloadedAsset]:
        remote_assets = self._search(
            keyword,
            kind=kind,
            max_results=max_results,
            provider_order=provider_order,
        )
        downloaded: List[DownloadedAsset] = []
        for asset in remote_assets:
            downloaded.append(
                self.cache.ensure(
                    keyword,
                    asset,
                    downloader=self._download_asset,
                )
            )

        if not downloaded and allow_ai and kind == AssetKind.IMAGE and self.ai_generator:
            self.logger.info("Falling back to Stable Diffusion for %s", keyword)
            asset, blob = self.ai_generator.generate_image(keyword)
            downloaded.append(
                self.cache.store_binary(keyword, asset, blob, extension=".png")
            )
        return downloaded

    def _search(
        self,
        keyword: str,
        *,
        kind: AssetKind,
        max_results: int,
        provider_order: Optional[list[str]] = None,
    ) -> List[RemoteAsset]:
        assets: List[RemoteAsset] = []
        order = provider_order or ["pexels", "pixabay"]

        for provider in order:
            if provider == "pexels":
                if kind == AssetKind.VIDEO:
                    assets.extend(self._safe_search(self.pexels.search_videos, keyword, max_results))
                else:
                    assets.extend(self._safe_search(self.pexels.search_images, keyword, max_results))
            elif provider == "pixabay":
                if kind == AssetKind.VIDEO:
                    assets.extend(self._safe_search(self.pixabay.search_videos, keyword, max_results))
                else:
                    assets.extend(self._safe_search(self.pixabay.search_images, keyword, max_results))

        if not assets:
            self.logger.warning("No assets found for '%s' (%s)", keyword, kind.value)
        return assets[:max_results]

    def _safe_search(self, func, keyword: str, max_results: int) -> List[RemoteAsset]:
        try:
            return func(keyword, max_results)
        except Exception as err:  # pragma: no cover - network failure fallback
            self.logger.warning("Asset search failed via %s: %s", func.__qualname__, err)
            return []

    def _download_asset(self, asset: RemoteAsset) -> bytes:
        client = None
        if asset.provider == "pexels":
            client = self.pexels
        elif asset.provider == "pixabay":
            client = self.pixabay
        if not client:
            raise RuntimeError(f"No downloader configured for provider '{asset.provider}'.")
        return client.download(asset.url)
