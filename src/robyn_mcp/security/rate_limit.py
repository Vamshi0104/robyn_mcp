from __future__ import annotations

import time
from dataclasses import dataclass


class RateLimitExceeded(Exception):
    pass


@dataclass(slots=True)
class Bucket:
    tokens: float
    updated_at: float


class TokenBucketLimiter:
    def __init__(self, capacity: int, refill_per_second: float) -> None:
        self.capacity = float(capacity)
        self.refill_per_second = float(refill_per_second)
        self._buckets: dict[str, Bucket] = {}

    def consume(self, key: str, amount: float = 1.0) -> None:
        now = time.monotonic()
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = Bucket(tokens=self.capacity, updated_at=now)
            self._buckets[key] = bucket

        elapsed = max(0.0, now - bucket.updated_at)
        bucket.tokens = min(self.capacity, bucket.tokens + elapsed * self.refill_per_second)
        bucket.updated_at = now
        if bucket.tokens < amount:
            raise RateLimitExceeded(f"Rate limit exceeded for key={key}")
        bucket.tokens -= amount
