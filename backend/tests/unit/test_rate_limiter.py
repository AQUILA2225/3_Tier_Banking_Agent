from concurrent.futures import ThreadPoolExecutor

import pytest

from app.core.rate_limiter import (
    SlidingWindowRateLimiter
)


pytestmark = pytest.mark.unit


class FakeClock:

    def __init__(self):

        self.now = 0.0

    def __call__(self):

        return self.now

    def advance(self, seconds):

        self.now += seconds


@pytest.fixture
def clock():

    return FakeClock()


@pytest.fixture
def limiter(clock):

    return SlidingWindowRateLimiter(
        window_seconds=60,
        max_keys=100,
        clock=clock
    )


def test_first_request_allowed(limiter):

    result = limiter.check("login:client1", 3)

    assert result.allowed is True
    assert result.remaining == 2
    assert result.retry_after == 0


def test_requests_allowed_until_limit(limiter):

    for _ in range(3):

        result = limiter.check("login:client1", 3)

        assert result.allowed is True

    assert result.remaining == 0


def test_excess_request_rejected(limiter):

    limiter.check("login:client1", 1)

    result = limiter.check("login:client1", 1)

    assert result.allowed is False
    assert result.remaining == 0
    assert result.retry_after == 60


def test_retry_after_decreases(limiter, clock):

    limiter.check("login:client1", 1)

    clock.advance(20)

    result = limiter.check("login:client1", 1)

    assert result.allowed is False
    assert result.retry_after == 40


def test_request_allowed_after_window(
    limiter,
    clock
):

    limiter.check("login:client1", 1)

    clock.advance(60)

    result = limiter.check("login:client1", 1)

    assert result.allowed is True


def test_sliding_window_behavior(limiter, clock):

    limiter.check("login:client1", 2)

    clock.advance(30)

    limiter.check("login:client1", 2)

    clock.advance(30)

    result = limiter.check("login:client1", 2)

    assert result.allowed is True

    blocked = limiter.check("login:client1", 2)

    assert blocked.allowed is False
    assert blocked.retry_after == 30


def test_different_clients_are_independent(limiter):

    limiter.check("login:client1", 1)

    assert not limiter.check(
        "login:client1", 1
    ).allowed

    assert limiter.check(
        "login:client2", 1
    ).allowed


def test_different_actions_are_independent(limiter):

    limiter.check("login:client1", 1)

    assert not limiter.check(
        "login:client1", 1
    ).allowed

    assert limiter.check(
        "register:client1", 1
    ).allowed


def test_rejected_requests_do_not_extend_window(
    limiter,
    clock
):

    limiter.check("login:client1", 1)

    clock.advance(50)

    assert not limiter.check(
        "login:client1", 1
    ).allowed

    clock.advance(10)

    assert limiter.check(
        "login:client1", 1
    ).allowed


def test_capacity_limit(clock):

    limiter = SlidingWindowRateLimiter(
        window_seconds=60,
        max_keys=2,
        clock=clock
    )

    assert limiter.check("client1", 1).allowed
    assert limiter.check("client2", 1).allowed

    assert not limiter.check("client3", 1).allowed

    assert not limiter.check("client1", 1).allowed


def test_expired_keys_release_capacity(clock):

    limiter = SlidingWindowRateLimiter(
        window_seconds=60,
        max_keys=1,
        clock=clock
    )

    limiter.check("client1", 1)

    clock.advance(60)

    assert limiter.check("client2", 1).allowed


def test_reset_clears_request_history(limiter):

    limiter.check("client1", 1)

    assert not limiter.check("client1", 1).allowed

    limiter.reset()

    assert limiter.check("client1", 1).allowed


def test_concurrent_requests_respect_limit(limiter):

    def make_request(_):

        return limiter.check(
            "login:client1",
            10
        ).allowed

    with ThreadPoolExecutor(max_workers=8) as executor:

        results = list(
            executor.map(make_request, range(50))
        )

    assert sum(results) == 10


@pytest.mark.parametrize(
    "window_seconds, max_keys",
    [(0, 100), (-1, 100), (60, 0), (60, -1)]
)
def test_invalid_configuration(
    window_seconds,
    max_keys
):

    with pytest.raises(ValueError):

        SlidingWindowRateLimiter(
            window_seconds=window_seconds,
            max_keys=max_keys
        )


@pytest.mark.parametrize(
    "key, limit",
    [("", 10), ("client1", 0), ("client1", -1)]
)
def test_invalid_request_parameters(
    limiter,
    key,
    limit
):

    with pytest.raises(ValueError):

        limiter.check(key, limit)