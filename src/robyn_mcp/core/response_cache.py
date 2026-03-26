from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any


def _safe_copy(value: Any) -> Any:
    try:
        return copy.deepcopy(value)
    except Exception:
        return value


def normalize_tag(tag: str) -> str:
    return str(tag).strip().lower()


def normalize_tags(tags: list[str] | set[str] | tuple[str, ...] | None) -> set[str]:
    if not tags:
        return set()
    return {normalize_tag(tag) for tag in tags if str(tag).strip()}


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at: float
    created_at: float
    tags: set[str] = field(default_factory=set)


class ToolResponseCache:
    def __init__(self, *, enabled: bool, default_ttl_seconds: int, max_entries: int) -> None:
        self.enabled = enabled
        self.default_ttl_seconds = default_ttl_seconds
        self.max_entries = max_entries
        self._entries: dict[str, CacheEntry] = {}
        self._tag_index: dict[str, set[str]] = {}
        self._lock = threading.RLock()

    def _remove_key_locked(self, key: str) -> bool:
        entry = self._entries.pop(key, None)
        if entry is None:
            return False

        for tag in entry.tags:
            key_set = self._tag_index.get(tag)
            if key_set is None:
                continue
            key_set.discard(key)
            if not key_set:
                self._tag_index.pop(tag, None)
        return True

    def _prune_expired_locked(self, now: float) -> None:
        stale = [key for key, entry in self._entries.items() if entry.expires_at <= now]
        for key in stale:
            self._remove_key_locked(key)

    def _evict_if_needed_locked(self) -> None:
        overflow = len(self._entries) - self.max_entries
        if overflow <= 0:
            return

        oldest = sorted(self._entries.items(), key=lambda item: item[1].created_at)[:overflow]
        for key, _entry in oldest:
            self._remove_key_locked(key)

    def build_key(
        self,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        tenant_id: str | None,
        principal_id: str | None,
        client_id: str | None,
        session_id: str | None,
        scopes: list[str] | set[str] | tuple[str, ...] | None,
    ) -> str:
        payload = {
            "tool": tool_name,
            "arguments": arguments,
            "tenant_id": tenant_id,
            "principal_id": principal_id,
            "client_id": client_id,
            "session_id": session_id,
            "scopes": sorted(str(scope) for scope in (scopes or [])),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any | None:
        if not self.enabled:
            return None

        now = time.time()
        with self._lock:
            self._prune_expired_locked(now)
            entry = self._entries.get(key)
            if entry is None:
                return None
            return _safe_copy(entry.value)

    def set(
        self,
        key: str,
        value: Any,
        *,
        tags: list[str] | set[str] | tuple[str, ...] | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        if not self.enabled:
            return

        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        if ttl <= 0:
            return

        norm_tags = normalize_tags(tags)
        now = time.time()
        entry = CacheEntry(
            value=_safe_copy(value),
            expires_at=now + ttl,
            created_at=now,
            tags=norm_tags,
        )

        with self._lock:
            self._prune_expired_locked(now)
            self._remove_key_locked(key)
            self._entries[key] = entry

            for tag in norm_tags:
                self._tag_index.setdefault(tag, set()).add(key)

            self._evict_if_needed_locked()

    def invalidate_tags(self, tags: list[str] | set[str] | tuple[str, ...] | None) -> int:
        if not self.enabled:
            return 0

        norm_tags = normalize_tags(tags)
        if not norm_tags:
            return 0

        with self._lock:
            keys = set()
            for tag in norm_tags:
                keys.update(self._tag_index.get(tag, set()))

            removed = 0
            for key in keys:
                if self._remove_key_locked(key):
                    removed += 1
            return removed

    def clear(self) -> int:
        if not self.enabled:
            return 0
        with self._lock:
            removed = len(self._entries)
            self._entries.clear()
            self._tag_index.clear()
            return removed

    def snapshot(self) -> dict[str, Any]:
        if not self.enabled:
            return {"enabled": False, "entries": 0, "tags": 0}

        now = time.time()
        with self._lock:
            self._prune_expired_locked(now)
            return {
                "enabled": True,
                "entries": len(self._entries),
                "tags": len(self._tag_index),
                "defaultTtlSeconds": self.default_ttl_seconds,
                "maxEntries": self.max_entries,
            }
