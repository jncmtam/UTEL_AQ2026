from itertools import product
import numpy as np
import pytest
from agqo.research.finite_budget import expected_minimum, decision_metrics, hit_probability


def exhaustive(values, probabilities, shots, incumbent=None):
    result = 0.
    for indices in product(range(len(values)), repeat=shots):
        probability = np.prod([probabilities[i] for i in indices])
        score = min(values[i] for i in indices)
        result += probability*min(score, incumbent) if incumbent is not None else probability*score
    return result


@pytest.mark.parametrize("shots", [1, 2, 4])
def test_expected_minimum_matches_all_ordered_draws_with_ties_and_failure(shots):
    f, p = [2., .2, .2, .8], [.15, .1, .25, .5]
    assert expected_minimum(f, p, shots) == pytest.approx(exhaustive(f, p, shots))
    assert expected_minimum(f, p, shots, .35) == pytest.approx(exhaustive(f, p, shots, .35))


def test_mean_and_best_sampler_rankings_can_reverse():
    # Safer mean versus occasional optimal candidate. No Monte Carlo is needed.
    f = [0., .4, 1.]
    safe, varied = [0., 1., 0.], [.2, 0., .8]
    assert expected_minimum(f, safe, 1) < expected_minimum(f, varied, 1)
    assert expected_minimum(f, safe, 8) > expected_minimum(f, varied, 8)


def test_failure_probability_and_conditional_best_keep_invalid_mass():
    r = decision_metrics([.2, .8, 2], [.1, .2, .7], [True, True, False], 2, .5)
    expected = (.2*(1-.9**2)+.8*(.9**2-.7**2))/(1-.7**2)
    assert r["no_feasible_probability"] == pytest.approx(.7**2)
    assert r["conditional_feasible_minimum"] == pytest.approx(expected)
    assert r["expected_with_incumbent"] == pytest.approx(exhaustive([.2,.8,2],[.1,.2,.7],2,.5))
    assert decision_metrics([2.], [1.], [False], 10)["conditional_feasible_minimum"] is None
    assert hit_probability(0, 10) == 0 and hit_probability(1, 10) == 1
    assert decision_metrics([.2, 2.], [1e-20, 1.], [True, False], 64)["conditional_feasible_minimum"] == pytest.approx(.2)


@pytest.mark.parametrize("scores,p,shots", [([],[],1),([1],[.9],1),([1,2],[1.1,-.1],1),([float('nan')],[1],1),([1],[1],True),([1],[1],0)])
def test_invalid_distribution_rejected(scores,p,shots):
    with pytest.raises(ValueError): expected_minimum(scores,p,shots)
