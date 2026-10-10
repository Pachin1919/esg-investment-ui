"""Optional solver initialization must not make concurrent recommendations fail."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from time import sleep
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from esgx.portfolio import optimize


@pytest.mark.parametrize("partial_module", [False, True], ids=["failed-native-import", "partial-module"])
def test_concurrent_first_calls_keep_feasible_fallback_after_unavailable_backend(monkeypatch, partial_module):
    workers = 8
    gate = Barrier(workers)
    import_calls = []

    def unavailable_import(name):
        import_calls.append(name)
        sleep(0.05)  # hold first initialization while every request reaches the same path
        if partial_module:
            return SimpleNamespace()  # observed failure: cvxpy exists but Variable is absent
        raise ImportError("native dependency DLL blocked by application control policy")

    monkeypatch.setattr(optimize, "_CVXPY_BACKEND", optimize._CVXPY_UNLOADED)
    monkeypatch.setattr(optimize, "import_module", unavailable_import)
    mu = pd.Series([0.1, 0.08, 0.02], index=["A", "B", "C"])
    covariance = pd.DataFrame(np.eye(3) * 0.05, index=mu.index, columns=mu.index)

    def recommend(_):
        gate.wait(timeout=10)
        return optimize.mean_variance_green(mu, covariance, gamma=5.0, w_max=0.5)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        portfolios = list(executor.map(recommend, range(workers)))
    assert import_calls == ["cvxpy"]  # one initialization attempt, including when it failed
    # Interior optimum for diagonal Sigma: w_i = (mu_i - multiplier)/(gamma*0.05).
    expected = np.full(3, 1 / 3) + (mu.to_numpy() - mu.mean()) / 0.25
    for weights in portfolios:
        assert np.isfinite(weights).all()
        assert weights.sum() == pytest.approx(1.0, abs=1e-8)
        assert (weights >= 0).all() and (weights <= 0.5).all()
        assert weights.to_numpy() == pytest.approx(expected, abs=1e-6)
