"""Small, versioned local knowledge base used to ground the AGQO prompt.

This deliberately uses a transparent lexical retriever instead of downloading
documents at inference time. The corpus contains project-specific definitions,
data caveats and primary QAOA method notes; retrieved snippets and source links
are serialized into every decision context for auditability.
"""

from __future__ import annotations

from typing import Any


CORPUS_VERSION = "agqo-local-rag-v3-finance-qaoa-grounding"

_NOTES: tuple[dict[str, Any], ...] = (
    {
        "id": "AGQO-METRICS-01",
        "title": "Definitions of the financial evaluation metrics",
        "tags": ("finance", "metrics", "sharpe", "sortino", "cagr", "drawdown", "cvar", "turnover", "fees"),
        "text": (
            "Use these project definitions. Net monthly return includes the modeled buy and sell fees. "
            "CAGR=(product(1+r_month))^(12/month_count)-1. Annualized Sharpe=sqrt(12)*mean(monthly excess return)/"
            "sample standard deviation(monthly excess return); monthly risk-free rate is assumed to be 0. "
            "Sortino uses sqrt(mean(min(excess_return,0)^2)) as monthly downside deviation and the same sqrt(12) "
            "annualization. Maximum drawdown is the minimum of compounded wealth divided by its prior running peak, "
            "minus 1. Monthly CVaR95 is the mean return among observations at or below the empirical 5th percentile; "
            "more negative is worse. Mean two-way turnover is the average total absolute portfolio weight traded "
            "per rebalance, including liquidation of holdings outside the candidate universe. Higher Sharpe/CAGR "
            "and lower drawdown/CVaR/turnover are not interchangeable objectives; read them together."
        ),
        "source": "Project implementation: agqo/evaluation.py and agqo/problem.py",
    },
    {
        "id": "AGQO-FEATURES-01",
        "title": "Meaning and units of the VN30 and cross-sectional fields",
        "tags": ("features", "volatility", "trend", "correlation", "dispersion", "liquidity", "vn30", "banks", "market"),
        "text": (
            "Interpret market fields as follows. VN30 annualized volatility over 20/60/120 sessions is the sample standard "
            "deviation of daily VN30 returns multiplied by sqrt(252). VN30 return_20d and return_60d are cumulative "
            "compounded returns. volatility_ratio_20d_to_120d above 1 means recent 20-session volatility exceeds its "
            "120-session level; it describes change, not direction of prices. mean_pairwise_correlation_252d and its "
            "90th percentile summarize correlations among eligible-stock returns in the trailing 252-session estimation "
            "window; higher correlation can reduce diversification but does not prove causation. "
            "cross_sectional_20d_return_dispersion is the sample standard deviation across stocks of their cumulative "
            "20-session returns; fraction_stocks_positive_20d is the share with a positive cumulative return. "
            "bank_fraction_of_eligible_stocks and candidate_group_fraction describe the current data snapshot's group mix. "
            "candidate_*_daily_traded_value_proxy_vnd is close multiplied by volume, averaged over the prior 20 sessions; "
            "it is denominated in VND and is only a liquidity proxy, not verified executable capacity."
        ),
        "source": "Project implementation: agqo/walkforward.py and agqo/walkforward.py::_eligible_universe",
    },
    {
        "id": "AGQO-REGIME-01",
        "title": "Limits and reliability of the volatility-regime submodel",
        "tags": ("submodel", "classifier", "logistic", "regime", "brier", "reliability", "volatility", "forecast", "ai"),
        "text": (
            "The logistic submodel estimates the probability that forward 21-session realized VN30 volatility exceeds "
            "the 70th percentile of the initial training-period volatility distribution. It does not predict return sign, "
            "stock returns, or profitability. The reported Brier score evaluates prior monthly probabilities against "
            "matured outcomes; lower is better. Brier skill is 1 - model Brier / expanding training-prevalence Brier; "
            "negative skill means the model lost to that baseline. Monthly forecasts overlap in their 21-session labels, "
            "so they are not independent observations. If fewer than six monthly forecasts have matured or skill is "
            "negative, regard the latest probability as weak, do not increase risk or QAOA depth because of it, and rely "
            "on measured policy outcomes and the deterministic supervisor."
        ),
        "source": "Project implementation: agqo/ai.py and agqo/walkforward.py",
    },
    {
        "id": "AGQO-OBJECTIVE-01",
        "title": "Portfolio objective and parameter meaning",
        "tags": ("objective", "risk", "lambda", "shrinkage", "alpha", "covariance", "expected return", "cost", "rebalance"),
        "text": (
            "The solver minimizes lambda*(x^T Sigma_alpha x)/K^2 - (mu^T x)/K + annualized modeled transaction cost, "
            "subject to exactly K selected assets. x is a binary selection vector. Sigma_alpha=(1-alpha)*sample_covariance "
            "+ alpha*diagonal(sample_covariance); alpha is diagonal shrinkage, not a return forecast. Lambda controls the "
            "risk penalty relative to the expected-return term; it is not a probability. Costs use the previous portfolio, "
            "per-asset fee rates, and 12 rebalances per year in this experiment. These estimates use historical data and "
            "do not guarantee future returns."
        ),
        "source": "Project implementation: agqo/estimators.py and agqo/problem.py",
    },
    {
        "id": "AGQO-QAOA-01",
        "title": "QAOA depth, mixers and feasibility",
        "tags": ("qaoa", "quantum", "qubit", "mixer", "xy", "x", "depth", "p", "layout", "gate", "feasible", "cardinality"),
        "text": (
            "N candidate assets map to N logical qubits and the portfolio constraint is exactly K selected assets. "
            "The X mixer can leave the feasible-cardinality subspace, so this implementation adds a penalty and records "
            "the measured feasible-sample rate. The XY mixer preserves Hamming weight and can remain in the K-feasible "
            "subspace when initialized there. p is the number of alternating cost/mixer layers; greater p and denser "
            "mixer layouts increase logical circuit work and do not by themselves prove better solutions or hardware "
            "advantage. The reported logical two-qubit gate proxy counts nonzero cost couplings per layer; an XY mixer "
            "adds two logical gates (RXX and RYY) per mixer edge and layer. It excludes hardware transpilation, routing "
            "and error correction. Ring, linear, complete and correlation layouts are empirical alternatives to compare under the "
            "same instances, shots, seeds and objective."
        ),
        "source": "Farhi, Goldstone & Gutmann (2014), https://arxiv.org/abs/1411.4028; Hadfield et al. (2019), https://arxiv.org/abs/1709.03489",
    },
    {
        "id": "AGQO-BENCHMARK-01",
        "title": "How to interpret QAOA solution quality",
        "tags": ("benchmark", "exact", "regret", "feasible", "shots", "seed", "classical", "optimality", "solver"),
        "text": (
            "For each small portfolio instance, exact enumeration is the classical optimum reference. The reported normalized "
            "objective regret is (best feasible sampled QAOA objective - exact minimum) divided by the objective range over "
            "feasible portfolios; lower is better and 0 means the sampled solution matched the exact optimum. Feasible-sample "
            "probability is the fraction of measured shots with exactly K selections, not the probability of financial profit. "
            "Report the distribution across seeds and dates, plus logical gate counts and wall time. Compare with exact, greedy "
            "and simulated annealing on the same objective; exact being faster at these N is a valid result, not a failure to report."
        ),
        "source": "Project implementation: agqo/walkforward.py and agqo/simulator.py",
    },
    {
        "id": "AGQO-DATA-01",
        "title": "Vietnam equity dataset limitations",
        "tags": ("dataset", "vn30", "ohlcv", "survivorship", "history", "data", "liquidity", "corporate action", "dividend"),
        "text": (
            "This experiment uses daily Vietnamese equity OHLCV and a snapshot of current VN30 members applied to historical "
            "dates. This creates survivorship and constituent-history bias. The local source has not been confirmed as fully "
            "adjusted for dividends, splits and other corporate actions; close*volume is only a traded-value proxy. The backtest "
            "uses a short monthly evaluation sample and modeled fees/capacity, not confirmed executable fills. Treat historical "
            "results as research evidence, not a claim of deployable profit."
        ),
        "source": "Project data manifest and experiment configuration",
    },
)


def retrieve_method_notes(payload: dict[str, Any], top_k: int = 6) -> list[dict[str, str]]:
    """Return project-specific notes most relevant to this signal and action set.

    The financial definitions and data caveat are always included. Remaining
    slots are ranked with a deterministic term matcher so no external service,
    embeddings endpoint or unpinned knowledge source is involved at runtime.
    """
    if top_k < 5:
        raise ValueError("At least five method notes are required for grounded guidance.")
    market = payload.get("market", {}) if isinstance(payload.get("market"), dict) else {}
    policies = payload.get("policy_candidates", [])
    policy_text = " ".join(
        f"{row.get('mixer', '')} {row.get('layout', '')} {row.get('p', '')} {row.get('n', '')}"
        for row in policies if isinstance(row, dict)
    )
    query_terms: set[str] = {"finance", "metrics", "dataset", "vn30", "ohlcv"}
    high_vol = market.get("ai_high_volatility_probability")
    vol_ratio = market.get("volatility_ratio_20d_to_120d")
    correlation = market.get("mean_pairwise_correlation_252d")
    dispersion = market.get("cross_sectional_20d_return_dispersion")
    if isinstance(high_vol, (int, float)) and high_vol >= 0.55:
        query_terms.update(("risk", "volatility"))
    if isinstance(vol_ratio, (int, float)) and vol_ratio >= 1.25:
        query_terms.update(("risk", "volatility"))
    if isinstance(correlation, (int, float)) and correlation >= 0.55:
        query_terms.update(("covariance", "mixer"))
    if isinstance(dispersion, (int, float)) and dispersion >= 0.04:
        query_terms.update(("expected return", "portfolio"))
    if any(word in policy_text.lower() for word in ("xy", "x", "ring", "linear", "complete", "correlation")):
        query_terms.update(("qaoa", "quantum", "depth", "layout", "feasible", "cardinality", "objective", "lambda", "shrinkage"))
    if any(
        isinstance(row, dict) and int(row.get("closed_periods", 0) or 0) > 0
        for row in payload.get("evidence", {}).values()
    ):
        query_terms.update(("benchmark", "exact", "regret", "shots", "seed"))

    pinned = {
        "AGQO-METRICS-01",
        "AGQO-DATA-01",
        "AGQO-BENCHMARK-01",
        "AGQO-FEATURES-01",
        "AGQO-REGIME-01",
    }
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for note in _NOTES:
        if note["id"] in pinned:
            continue
        tags = set(note["tags"])
        score = sum(3 if tag in query_terms else 1 for tag in tags if tag in query_terms)
        ranked.append((score, note["id"], note))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = [next(note for note in _NOTES if note["id"] == key) for key in sorted(pinned)]
    selected.extend(item[2] for item in ranked[: max(0, top_k - len(selected))])
    return [
        {
            "id": note["id"],
            "title": note["title"],
            "text": note["text"],
            "source": note["source"],
        }
        for note in selected
    ]
