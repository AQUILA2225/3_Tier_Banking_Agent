from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from math import ceil
from threading import Lock
from time import monotonic

@dataclass(frozen=True)
class RateLimitResult:

    allowed: bool
    remaining: int
    retry_after: int = 0

class SlidingWindowRateLimiter:
    def __init__(
        self,
        window_seconds: int = 60,
        max_keys: int = 10000,
        clock: Callable[[], float] = monotonic
    ):

        if window_seconds <= 0 or max_keys <= 0:

            raise ValueError(
                "Rate limiter configuration must be positive."
            )

        self.window_seconds = window_seconds
        self.max_keys = max_keys
        self._clock = clock
        self._requests: dict[
            str,
            deque[float]
        ] = {}

        self._lock = Lock()

        self._next_cleanup = 0.0

    def _prune(
        self,
        timestamps: deque[float],
        now: float
    ) -> None:

        cutoff = now - self.window_seconds

        while timestamps and timestamps[0] <= cutoff:

            timestamps.popleft()

    def _cleanup(self, now: float) -> None:

        expired_keys = []

        for key, timestamps in self._requests.items():

            self._prune(timestamps, now)

            if not timestamps:

                expired_keys.append(key)

        for key in expired_keys:
            del self._requests[key]

        self._next_cleanup = (
            now + self.window_seconds
        )

    def check(
        self,
        key: str,
        limit: int
    ) -> RateLimitResult:

        if not key or limit <= 0:

            raise ValueError(
                "A valid key and positive limit are required."
            )

        with self._lock:

            now = self._clock()

            if now >= self._next_cleanup:

                self._cleanup(now)

            timestamps = self._requests.get(key)

            if timestamps is None:

                if len(self._requests) >= self.max_keys:

                    self._cleanup(now)

                if len(self._requests) >= self.max_keys:

                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        retry_after=self.window_seconds
                    )

                timestamps = deque()

                self._requests[key] = timestamps

            self._prune(timestamps, now)

            if len(timestamps) >= limit:

                retry_after = max(
                    1,
                    ceil(
                        timestamps[0]
                        + self.window_seconds
                        - now
                    )
                )

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    retry_after=retry_after
                )

            timestamps.append(now)

            return RateLimitResult(
                allowed=True,
                remaining=limit - len(timestamps)
            )

    def reset(self) -> None:

        with self._lock:

            self._requests.clear()

            self._next_cleanup = 0.0