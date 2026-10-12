import numpy as np
import pandas as pd

from agqo.ai import (
    build_daily_features,
    diagonal_shrinkage,
    fit_regime_model,
    forward_volatility,
    regime_controls,
)
from agqo.estimators import (
    build_ledoit_wolf_problem,
    build_regime_problem,
    estimate_annual_inputs,
)
from agqo.problem import PortfolioProblem, build_qubo, exact_solve, synthetic_problem, to_ising
from agqo.simulator import optimize_qaoa, statevector


def make_problem(n=8, k=3):
    rng = np.random.Generator(np.random.PCG64(22))
    factor = rng.normal(size=(n, 2)) * 0.02
    covariance = factor @ factor.T + np.diag(np.full(n, 0.04))
    mu = rng.uniform(-0.05, 0.12, n)
    return PortfolioProblem(tuple(f"A{i}" for i in range(n)), mu, covariance, k=k)


def test_original_qubo_and_ising_match_all_bitstrings():
    problem = make_problem()
    for mixer in ("X", "XY"):
        qubo = build_qubo(problem, mixer=mixer)
        ising = to_ising(qubo)
        for state in range(1 << problem.n):
            bits = np.array([(state >> i) & 1 for i in range(problem.n)])
            spins = 1 - 2 * bits
            energy = ising.constant + ising.fields @ spins
            energy += sum(ising.couplings[i, j] * spins[i] * spins[j]
                          for i in range(problem.n) for j in range(i + 1, problem.n))
            assert abs(qubo.energy(bits) - energy) < 1e-10
            if bits.sum() == problem.k:
                assert abs(problem.score(bits) - qubo.energy(bits)) < 1e-10


def test_xy_mixer_preserves_cardinality_and_state_norm():
    problem = make_problem()
    qubo = build_qubo(problem, mixer="XY")
    initial_index = (1 << 0) | (1 << 2) | (1 << 5)
    state = statevector(qubo, "XY", np.array([0.37, -0.61]), depth=1, initial_index=initial_index)
    assert np.isclose(np.linalg.norm(state), 1.0)
    assert all(abs(value) < 1e-10 for i, value in enumerate(state) if i.bit_count() != problem.k)


def test_x_mixer_penalty_makes_exact_qubo_ground_state_feasible():
    problem = make_problem()
    qubo = build_qubo(problem, mixer="X")
    energies = []
    for state in range(1 << problem.n):
        bits = np.array([(state >> i) & 1 for i in range(problem.n)])
        energies.append((qubo.energy(bits), bits))
    minimum, bits = min(energies, key=lambda item: item[0])
    _, exact_score = exact_solve(problem)
    assert bits.sum() == problem.k
    assert np.isclose(minimum, exact_score)


def test_exact_and_local_qaoa_return_feasible_choices():
    problem = make_problem()
    exact_bits, exact_score = exact_solve(problem)
    assert exact_bits.sum() == problem.k
    assert np.isclose(problem.score(exact_bits), exact_score)
    for mixer in ("X", "XY"):
        result = optimize_qaoa(problem, mixer=mixer, seed=11, max_evaluations=6, shots=64)
        assert result.evaluations <= 6
        assert 0.0 <= result.sampled_feasible_probability <= 1.0
        assert 0.0 <= result.ideal_feasible_probability <= 1.0
        assert result.best_bits is None or sum(result.best_bits) == problem.k


def test_regime_controls_and_diagonal_shrinkage_are_bounded():
    assert regime_controls(-1) == (2.0, 0.1)
    assert regime_controls(2) == (10.0, 0.7)
    covariance = np.array([[1.0, 0.4], [0.4, 2.0]])
    shrunk = diagonal_shrinkage(covariance, 0.5)
    assert np.allclose(shrunk, [[1.0, 0.2], [0.2, 2.0]])


def test_proposal_synthetic_seed_is_reproducible():
    first, second = synthetic_problem(20261012), synthetic_problem(20261012)
    assert np.array_equal(first.mu, second.mu)
    assert np.array_equal(first.covariance, second.covariance)


def test_ai_label_uses_only_the_next_21_observations_and_drops_unmatured_tail():
    dates = pd.bdate_range("2020-01-01", periods=90)
    values = np.linspace(-0.03, 0.04, len(dates))
    returns = pd.Series(values, index=dates)
    target = forward_volatility(returns, horizon=21)
    assert np.isclose(target.iloc[0], returns.iloc[1:22].std(ddof=1) * np.sqrt(252))
    assert target.iloc[-21:].isna().all()


def test_market_features_are_causal_and_ai_model_respects_time_splits():
    rng = np.random.Generator(np.random.PCG64(8))
    dates = pd.bdate_range("2018-01-01", periods=1200)
    sigma = np.where((np.arange(len(dates)) // 60) % 2 == 0, 0.008, 0.022)
    market = pd.Series(rng.normal(size=len(dates)) * sigma, index=dates)
    features = pd.DataFrame(
        {"vol_proxy": pd.Series(market.to_numpy(), index=dates).rolling(20).std().bfill(),
         "noise": rng.normal(size=len(dates))},
        index=dates,
    )
    model = fit_regime_model(
        features,
        market,
        train_end=str(dates[620].date()),
        validation_start=str(dates[650].date()),
        validation_end=str(dates[1000].date()),
        c_values=(0.1, 1.0),
    )
    probability = model.predict_probability(features.iloc[1001:1004])
    assert probability.shape == (3,)
    assert np.isfinite(probability).all()
    assert model.chosen_c in (0.1, 1.0)

    assets = pd.DataFrame(rng.normal(size=(150, 3)) * 0.01, index=dates[:150], columns=list("ABC"))
    traded = pd.DataFrame(rng.uniform(1e6, 1e7, size=(150, 3)), index=assets.index, columns=assets.columns)
    first = build_daily_features(market.iloc[:150], assets, traded)
    altered_market = market.iloc[:150].copy()
    altered_market.iloc[130:] = 0.5
    altered = build_daily_features(altered_market, assets, traded)
    assert np.allclose(first.iloc[120], altered.iloc[120], equal_nan=True)


def test_synthetic_ai_to_controls_to_qaoa_pipeline_runs_end_to_end():
    rng = np.random.Generator(np.random.PCG64(33))
    dates = pd.bdate_range("2018-01-01", periods=1200)
    market_sigma = np.where((np.arange(len(dates)) // 45) % 2 == 0, 0.008, 0.025)
    market = pd.Series(rng.normal(size=len(dates)) * market_sigma, index=dates)
    features = pd.DataFrame(
        {"volatility_proxy": pd.Series(market.to_numpy(), index=dates).rolling(20).std().bfill(),
         "trend_proxy": market.rolling(20).sum().bfill()},
        index=dates,
    )
    model = fit_regime_model(
        features, market, str(dates[680].date()), str(dates[710].date()), str(dates[1050].date()),
        c_values=(0.1, 1.0),
    )
    probability = float(model.predict_probability(features.iloc[[-1]])[0])
    asset_returns = pd.DataFrame(
        rng.normal(0, 0.012, size=(252, 8)), columns=[f"S{i}" for i in range(8)]
    )
    problem, controls = build_regime_problem(
        asset_returns, tuple(asset_returns.columns), probability, k=6
    )
    exact_bits, exact_score = exact_solve(problem)
    qaoa = optimize_qaoa(problem, mixer="XY", seed=11, max_evaluations=5, shots=64)
    assert 0.0 <= probability <= 1.0
    assert 2.0 <= controls["risk_aversion"] <= 10.0
    assert exact_bits.sum() == 6 and np.isfinite(exact_score)
    assert qaoa.best_bits is not None and sum(qaoa.best_bits) == 6


def test_financial_estimators_annualize_sample_covariance_and_shrinkage():
    rng = np.random.Generator(np.random.PCG64(4))
    returns = pd.DataFrame(rng.normal(0, 0.01, size=(300, 3)))
    mu, covariance = estimate_annual_inputs(returns, diagonal_alpha=0.4)
    assert mu.shape == (3,)
    assert covariance.shape == (3, 3)
    assert np.allclose(covariance, covariance.T)
    assert np.linalg.eigvalsh(covariance).min() >= 0


def test_ai_probability_flows_into_portfolio_risk_controls():
    rng = np.random.Generator(np.random.PCG64(12))
    returns = pd.DataFrame(rng.normal(0, 0.01, size=(260, 8)), columns=[f"S{i}" for i in range(8)])
    problem, controls = build_regime_problem(
        returns, tuple(returns.columns), probability_high_volatility=0.70, k=6
    )
    assert problem.risk_aversion == 7.6
    assert np.isclose(controls["diagonal_alpha"], 0.52)
    fixed, fixed_controls = build_regime_problem(
        returns, tuple(returns.columns), probability_high_volatility=0.1, k=6, ai_enabled=False
    )
    assert fixed.risk_aversion == 5.0
    assert fixed_controls["diagonal_alpha"] == 0.4
    lambda_only, lambda_controls = build_regime_problem(
        returns, tuple(returns.columns), 0.70, k=6, adaptive_shrinkage=False
    )
    alpha_only, alpha_controls = build_regime_problem(
        returns, tuple(returns.columns), 0.70, k=6, adaptive_lambda=False
    )
    assert lambda_only.risk_aversion == 7.6 and lambda_controls["diagonal_alpha"] == 0.4
    assert alpha_only.risk_aversion == 5.0 and np.isclose(alpha_controls["diagonal_alpha"], 0.52)
    assert build_ledoit_wolf_problem(returns, tuple(returns.columns)).covariance.shape == (8, 8)
