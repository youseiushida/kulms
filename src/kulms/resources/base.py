from __future__ import annotations

from collections.abc import Iterable
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from kulms.client import KULMSClient


class BaseResource:
    def __init__(self, client: "KULMSClient") -> None:
        self._client = client

    @property
    def direct(self):
        return self._client.direct

    @staticmethod
    def _params(**kwargs: Any) -> dict[str, Any]:
        return {key: value for key, value in kwargs.items() if value is not None}

    @staticmethod
    def _items(data: Any, *preferred_keys: str) -> list[Any]:
        if isinstance(data, list):
            return data
        if not isinstance(data, dict):
            return []
        keys = [*preferred_keys, "items", "collection", "data"]
        keys.extend(key for key in data if key.endswith("_collection"))
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
        return [data]

    @staticmethod
    def _flatten_dicts(value: Any) -> Iterable[dict[str, Any]]:
        if isinstance(value, list):
            for item in value:
                yield from BaseResource._flatten_dicts(item)
            return
        if not isinstance(value, dict):
            return
        yield value
        for key, child in value.items():
            if key.endswith("_collection") and isinstance(child, list):
                yield from BaseResource._flatten_dicts(child)
        for key in ("children", "items", "resources", "files", "members"):
            child = value.get(key)
            if isinstance(child, list):
                yield from BaseResource._flatten_dicts(child)
