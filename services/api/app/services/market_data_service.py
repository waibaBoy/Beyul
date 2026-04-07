from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import re

import httpx


@dataclass(frozen=True)
class MarketReferenceSnapshot:
    provider: str
    reference_asset: str | None = None
    reference_symbol: str | None = None
    reference_price: str | None = None
    reference_timestamp: str | None = None
    reference_label: str | None = None
    reference_source_label: str | None = None
    source_reference_url: str | None = None

    def as_contract_metadata(self) -> dict[str, object]:
        return {
            key: value
            for key, value in {
                "reference_asset": self.reference_asset,
                "reference_symbol": self.reference_symbol,
                "reference_price": self.reference_price,
                "reference_timestamp": self.reference_timestamp,
                "reference_label": self.reference_label,
                "reference_source_label": self.reference_source_label,
                "market_data_provider": self.provider,
            }.items()
            if value is not None
        }


class MarketDataService:
    async def get_reference_snapshot(
        self,
        *,
        template_key: str | None,
        template_config: Mapping[str, object] | None,
        contract_metadata: Mapping[str, object],
    ) -> MarketReferenceSnapshot | None:
        raise NotImplementedError


class NoopMarketDataService(MarketDataService):
    async def get_reference_snapshot(
        self,
        *,
        template_key: str | None,
        template_config: Mapping[str, object] | None,
        contract_metadata: Mapping[str, object],
    ) -> MarketReferenceSnapshot | None:
        reference_asset = _clean_text(contract_metadata.get("reference_asset"))
        reference_label = _clean_text(contract_metadata.get("reference_label"))
        reference_source_label = _clean_text(contract_metadata.get("reference_source_label"))
        if not reference_asset and not reference_label and not reference_source_label:
            return None
        return MarketReferenceSnapshot(
            provider="none",
            reference_asset=reference_asset,
            reference_label=reference_label,
            reference_source_label=reference_source_label,
            reference_timestamp=_utcnow_iso(),
        )


class BinanceMarketDataService(MarketDataService):
    def __init__(self, api_base_url: str) -> None:
        self._api_base_url = api_base_url.rstrip("/")

    async def get_reference_snapshot(
        self,
        *,
        template_key: str | None,
        template_config: Mapping[str, object] | None,
        contract_metadata: Mapping[str, object],
    ) -> MarketReferenceSnapshot | None:
        if template_key not in {"price_above", "price_below", "up_down_interval"}:
            return None

        reference_asset = _clean_text(contract_metadata.get("reference_asset"))
        if not reference_asset:
            return None

        symbol = _to_binance_symbol(reference_asset)
        if symbol is None:
            return None

        price = await self._fetch_spot_price(symbol)
        timestamp = _utcnow_iso()
        return MarketReferenceSnapshot(
            provider="binance",
            reference_asset=reference_asset,
            reference_symbol=symbol,
            reference_price=price,
            reference_timestamp=timestamp,
            reference_label=_clean_text(contract_metadata.get("reference_label")) or f"{reference_asset} spot price",
            reference_source_label="Binance Spot",
            source_reference_url=f"https://www.binance.com/en/trade/{symbol}",
        )

    async def _fetch_spot_price(self, symbol: str) -> str:
        async with httpx.AsyncClient(base_url=self._api_base_url, timeout=10.0) as client:
            response = await client.get("/api/v3/ticker/price", params={"symbol": symbol})
            response.raise_for_status()
            payload = response.json()
        return str(payload["price"])


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _utcnow_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _to_binance_symbol(reference_asset: str) -> str | None:
    normalized = re.sub(r"[^A-Za-z0-9/]", "", reference_asset.strip().upper())
    if not normalized:
        return None
    if "/" in normalized:
        base, quote = normalized.split("/", 1)
        if quote == "USD":
            quote = "USDT"
        normalized = f"{base}{quote}"
    return normalized or None
