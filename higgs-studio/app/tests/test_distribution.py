from collections import Counter

import pytest

from studio.distribution import DistributionError, assign


def test_balanced_equal_plus_minus_one():
    a = assign([None] * 20, ["a", "b", "c"], "balanced", seed=1)
    c = Counter(a)
    assert sum(c.values()) == 20 and max(c.values()) - min(c.values()) <= 1


def test_balanced_respects_pins():
    pins = ["b"] * 4 + [None] * 16
    a = assign(pins, ["a", "b", "c", "d"], "balanced", seed=2)
    assert a[:4] == ["b"] * 4
    assert set(Counter(a).values()) == {5}


def test_weighted_counts():
    a = assign([None] * 100, ["a", "b"], "weighted", {"a": 70, "b": 30}, seed=3)
    assert Counter(a) == {"a": 70, "b": 30}


def test_uniform_and_reproducible():
    x = assign([None] * 50, ["a", "b", "c"], "uniform", seed=9)
    assert x == assign([None] * 50, ["a", "b", "c"], "uniform", seed=9)
    assert x != assign([None] * 50, ["a", "b", "c"], "uniform", seed=10)
    p = [None, "c", None]
    assert assign(p, ["a", "b", "c"], "uniform", seed=1)[1] == "c"


def test_errors():
    with pytest.raises(DistributionError):
        assign(["zz"], ["a"], "balanced")
    with pytest.raises(DistributionError):
        assign([None], ["a"], "weighted", {"a": 0})
