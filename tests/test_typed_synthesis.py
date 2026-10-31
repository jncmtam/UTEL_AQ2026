from copy import deepcopy
import pytest
from agqo.synthesis.pilot import cases
from agqo.synthesis.profile import hamiltonian_ir,data_profile
from agqo.synthesis.compiler import verify
from agqo.synthesis.typed import baseline_program,domain,lower,typed_request


@pytest.mark.parametrize('case_index',[0,1,2])
def test_typed_lowering_preserves_mandate_and_canonical_cost(case_index):
    _,p=cases()[case_index];h,c=hamiltonian_ir(p)
    program=baseline_program(p,data_profile(p));ir=lower(program,p,h)
    result=verify(ir,p,h,c)
    assert result['valid'],result
    assert 'gamma_0' not in result['inactive_parameters']
    assert p.feasible(ir['initial_bits'])
    assert ir['layers'][0]['cost']['hamiltonian_hash']==h['hamiltonian_hash']
    frozen=set(domain(p)['frozen_zero']+domain(p)['frozen_one'])
    assert all(not frozen.intersection(g['qubits']) for g in ir['initialization']+ir['layers'][0]['mixer'])


def test_typed_rejects_invalid_edge_and_disconnected_graph_without_repair():
    _,p=cases()[0];h,c=hamiltonian_ir(p);program=baseline_program(p,data_profile(p))
    bad=deepcopy(program);bad['mixer'][0]['edge']='e0_999'
    with pytest.raises(ValueError):lower(bad,p,h)
    bad=deepcopy(program);bad['mixer']=[{'edge':e,'group':0} for e in ('e0_1','e0_2','e1_2')]
    with pytest.raises(ValueError,match='disconnected'):lower(bad,p,h)
    bad=deepcopy(program);bad['mixer'][1]=deepcopy(bad['mixer'][0])
    with pytest.raises(ValueError,match='Repeated'):lower(bad,p,h)


def test_typed_request_is_separate_and_bounded():
    _,p=cases()[1];h,c=hamiltonian_ir(p);r=typed_request(p,h)
    assert r['max_tokens']==1536
    assert r['payload']['prompt_version']=='typed-exchange-v2'
    assert 'objective_coefficients' in r['payload']['financial_ir']
    assert r==typed_request(p,h)


def test_expanded_budget_requires_authorization_and_keeps_finite_cap(tmp_path):
    from datetime import datetime,timezone
    from agqo.synthesis.budget import BudgetLedger
    with pytest.raises(ValueError):BudgetLedger(tmp_path/'bad.json',limit=150,monthly_allowance=None)
    ledger=BudgetLedger(tmp_path/'expanded.json',limit=150,monthly_allowance=None,
                        authorization='User explicitly expanded Modal usage in this session.')
    snap={'metered_cost':100.,'checked_utc':datetime.now(timezone.utc).isoformat()}
    job=ledger.reserve(100,'bounded_large_model',snap)
    ledger.finish(job,'completed')
    with pytest.raises(ValueError,match='Budget blocked'):ledger.reserve(51,'over_cap',snap)
    # Reopening cannot raise an existing ceiling, even under expanded policy.
    reopened=BudgetLedger(tmp_path/'expanded.json',limit=200,monthly_allowance=None,
                           authorization='User explicitly expanded Modal usage in this session.')
    assert reopened.state()['limit_usd']==150


def test_large_model_reservation_counts_all_gpus():
    from agqo.synthesis.budget import job_reservation,MODELS
    snapshot={'rates':{'gpu_hour_cost_h200':4.54,'cpu_hour_cost':.0473,'mem_gib_hour_cost':.008}}
    assert job_reservation('coder480',snapshot)>4*4.54*(1800+900)/3600
    assert set(MODELS)=={'next80','coder30'}
