"""Semantic faults, independent execution, finance identity, budgets and search accounting."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
import numpy as np
import pytest

from agqo.repair.data import synthetic_data, make_window
from agqo.synthesis.profile import data_profile, financial_ir, hamiltonian_ir, digest
from agqo.synthesis.builders import build_rule, rotation
from agqo.synthesis.ir import SCHEMA, Limits, check_ir
from agqo.synthesis.compiler import execute, qiskit_lower, mapped_indices, verify
from agqo.synthesis.optimizer import optimize
from agqo.synthesis.budget import BudgetLedger, job_reservation
from agqo.synthesis.client import SynthesisClient, request_for
from agqo.synthesis.search import run_search, SearchConfig
from agqo.synthesis.thresholds import quality, assess


def fixture(n=4, seed=11):
    p,*_ = make_window(synthetic_data(seed=seed, n=n), n=n, k=n//2, text=f'Hold {n//2} assets')
    h,c = hamiltonian_ir(p)
    return p,h,c,build_rule(p,h,data_profile(p))


@pytest.mark.parametrize('n',[4,6,8])
def test_generated_schedule_crosschecks_independent_backends_and_counts_cost(n):
    p,h,c,ir=fixture(n)
    report=verify(ir,p,h,c)
    assert report['valid'], report['errors']
    assert min(report['crosscheck_state_fidelities']) >= 1-1e-9
    assert report['maximum_cardinality_leak'] <= 1e-9
    assert report['active_parameters'] == len(ir['parameters'])
    assert report['resources']['transpiled_cx'] > 2*n
    assert report['resources']['includes_lowered_cost']


@pytest.mark.parametrize('op,targets',[('H',[0]),('X',[1]),('RX',[0]),('RY',[1]),('RZ',[2]),('CX',[1,2]),('RXX',[0,2]),('RYY',[1,3]),('RZZ',[0,3])])
def test_each_gate_matches_qiskit_even_after_qubit_permutation(op,targets):
    from qiskit.quantum_info import Statevector
    p,h,c,ir=fixture()
    ir['mode']='penalty'
    ir['qubit_to_asset']=[2,0,3,1]
    angle=None if op in {'H','X','CX'} else {'parameter':None,'scale':0,'offset':0.713}
    ir['initialization']=[{'op':'H','qubits':[q],'angle':None} for q in range(p.n)]
    ir['initialization'] += [{'op':op,'qubits':targets,'angle':angle}]
    angles=np.linspace(.13,.8,len(ir['parameters']))
    expected=execute(ir,c['energies'],angles)
    actual=Statevector.from_instruction(qiskit_lower(ir,c['energies'],angles)[0]).data
    assert abs(np.vdot(actual,expected))**2 == pytest.approx(1,abs=1e-10)
    assert sorted(mapped_indices(ir)) == list(range(1<<p.n))


@pytest.mark.parametrize('fault', ['wrong_hash','missing_cost','wrong_qubit','unpaired_exchange','wrong_angle','unknown_parameter','cost_parameter_in_mixer','extra_field','boolean_qubit'])
def test_semantic_faults_are_rejected_before_optimizer(fault):
    p,h,c,ir=fixture()
    if fault=='wrong_hash': ir['hamiltonian_hash']='bad'
    if fault=='missing_cost': del ir['layers'][0]['cost']
    if fault=='wrong_qubit': ir['layers'][0]['mixer'][0]['qubits']=[0,99]
    if fault=='unpaired_exchange': ir['layers'][0]['mixer'].pop(1)
    if fault=='wrong_angle': ir['layers'][0]['mixer'][1]['angle']['scale']=-2
    if fault=='unknown_parameter': ir['layers'][0]['mixer'][0]['angle']['parameter']='phantom'
    if fault=='cost_parameter_in_mixer': ir['layers'][0]['mixer'][0]['angle']['parameter']='gamma_0'
    if fault=='extra_field': ir['execute_python']='print(1)'
    if fault=='boolean_qubit': ir['layers'][0]['mixer'][0]['qubits']=[False,1]
    assert not verify(ir,p,h,c)['valid']


def test_tampered_cost_table_is_rejected_and_inactive_gamma_is_visible():
    p,h,c,ir=fixture()
    altered=deepcopy(c); altered['energies'][0]+=.01
    assert not verify(ir,p,h,altered)['valid']
    ir=build_rule(p,h,data_profile(p),depth=1,basis_init=True)
    report=verify(ir,p,h,c)
    assert report['valid']
    assert 'gamma_0' in report['inactive_parameters']
    assert any(w['code']=='inactive_first_cost' for w in report['warnings'])


def test_register_mapping_and_sampled_solution_are_in_asset_order():
    p,h,c,ir=fixture()
    ir['qubit_to_asset']=[3,2,1,0]
    r=optimize(ir,p,c,evaluations=7,shots=32)
    assert r['total_shots'] <= 8*32
    assert r['bits'] is not None and p.feasible(r['bits'])
    assert r['objective'] == pytest.approx(p.score(r['bits']))


def test_profiles_are_causal_handle_constant_assets_and_preserve_exact_coefficients():
    p,h,c,ir=fixture()
    returns=p.returns.copy(); returns[:,0]=0
    pp=replace(p,returns=returns)
    profile=data_profile(pp)
    assert 0 in profile['zero_variance_assets']
    assert profile['condition_number'] is None
    json.dumps(profile,allow_nan=False)
    assert financial_ir(p)['objective_coefficients']['linear']==p.objective_qubo().linear.tolist()
    req=request_for(p,h)
    assert 'energies' not in req['payload']['hamiltonian_ir']
    assert 'exact_reference' not in json.dumps(req)
    ablation=request_for(p,h,ablation='constraints_only')
    assert 'objective_coefficients' not in ablation['payload']['financial_ir']
    assert ablation['payload']['data_profile']['feature_ids']==[]


def snapshot(cost=0):
    return {'checked_utc':datetime.now(timezone.utc).isoformat(),'metered_cost':cost,
            'rates':{'gpu_hour_cost_h200':4.54,'gpu_hour_cost_a100_80gb':2.5,'cpu_hour_cost':.0473,'mem_gib_hour_cost':.008}}


def test_budget_sequential_failed_jobs_charged_and_cap_cannot_be_raised(tmp_path):
    path=tmp_path/'budget.json'; ledger=BudgetLedger(path,limit=4)
    job=ledger.reserve(2,'first',snapshot())
    with pytest.raises(ValueError,match='already reserved'): ledger.reserve(1,'second',snapshot())
    ledger.finish(job,'failed_reservation_charged')
    with pytest.raises(ValueError,match='Budget blocked'): BudgetLedger(path,limit=25).reserve(3,'raise_cap',snapshot())
    with pytest.raises(ValueError,match='Budget blocked'): ledger.reserve(1,'no_credit',snapshot(29))
    assert ledger.state()['jobs'][0]['reserved_usd']==2
    assert job_reservation('next80',snapshot()) > 4.54*(1500/3600)


def test_disabled_mode_never_fabricates_live_llm_and_search_charges_all_trials(tmp_path):
    p,h,c,ir=fixture()
    client=SynthesisClient(mode='disabled',directory=tmp_path/'client')
    answer=client.batch([request_for(p,h)])[0]
    assert answer['status']=='not_run' and 'response' not in answer
    config=SearchConfig(initial_proposals=2,repair_rounds=1,proposals_per_repair=1,screen_evaluations=3,screen_shots=16,final_evaluations=4,final_shots=16,finalists=1)
    output=run_search(p,tmp_path/'search',config=config)
    assert output['total_shots']==3*4*16+5*16
    assert output['total_shots']<=output['shot_budget_cap']
    assert (tmp_path/'search/winner/circuit.qasm').exists()
    disabled=run_search(p,tmp_path/'disabled',client=client,config=config)
    assert disabled['status']=='no_verified_candidate' and disabled['total_shots']==0


def test_failures_are_not_excluded_from_qualification_and_tiny_pilot_cannot_qualify():
    p,h,c,ir=fixture()
    assert quality(p,c,{'feasible':False})['normalized_gap'] is None
    report=assess([{'case_id':'a','verification':{'valid':True},'round':0}],independent_instances=3)
    assert report['valid_instance_rate']==pytest.approx(1/3)
    assert report['qualified'] is False


def test_diagonal_register_permutation_preserves_financial_energy_for_every_basis():
    p,h,c,ir=fixture()
    ir['qubit_to_asset']=[3,0,2,1]
    mapping=mapped_indices(ir)
    for physical in range(1<<p.n):
        asset_bits=np.zeros(p.n,dtype=int)
        for q,asset in enumerate(ir['qubit_to_asset']):
            asset_bits[asset]=(physical>>q)&1
        assert c['objective'][mapping[physical]]==pytest.approx(p.score(asset_bits))


def test_structural_test_suite_is_independent_of_opened_pilot_and_has_frozen_families():
    from agqo.synthesis.benchmark import test_cases
    from agqo.synthesis.pilot import cases
    opened={p.fingerprint() for _,p in cases()}
    suite=test_cases()
    assert len(suite)==12
    assert len({p.fingerprint() for _,_,p in suite})==12
    assert not opened & {p.fingerprint() for _,_,p in suite}
    assert {family for _,family,_ in suite}=={'new_seed','decorrelated','cluster_shift','unseen_constraints'}


def test_search_feedback_contains_counterexample_and_never_changes_problem(tmp_path):
    p,h,c,ir=fixture()
    class RepairingClient:
        mode='fixture_not_live'
        def __init__(self): self.calls=[]
        def batch(self, requests):
            self.calls.append(requests)
            answer=deepcopy(ir)
            if len(self.calls)==1:
                answer['layers'][0]['mixer'].pop(1)
            return [{'status':'ok','response':deepcopy(answer),'execution':'test_fixture_not_llm'} for _ in requests]
    client=RepairingClient()
    cfg=SearchConfig(initial_proposals=1,repair_rounds=1,proposals_per_repair=1,screen_evaluations=2,screen_shots=8,final_evaluations=3,final_shots=8,finalists=1)
    output=run_search(p,tmp_path/'repair',client=client,config=cfg)
    assert output['candidates'][0]['verification']['valid'] is False
    assert output['candidates'][1]['verification']['valid'] is True
    assert client.calls[1][0]['payload']['feedback'][0]['verification']['errors']
    assert all(r['payload']['financial_ir']['problem_hash']==p.fingerprint() for batch in client.calls for r in batch)


def test_feature_ablation_does_not_relabel_changed_descriptors_as_original():
    p,h,c,ir=fixture()
    p2,*_=fixture(seed=31)
    donor=data_profile(p2)
    shifted=request_for(p,h,ablation='shuffled',donor=donor)['payload']['data_profile']
    assert shifted['correlation']==donor['correlation']
    assert shifted['ablation']=='correlation_descriptors_from_different_instance'
    no=request_for(p,h,ablation='no_correlation')['payload']['data_profile']
    assert 'correlation' not in no and 'CORRELATION' not in no['feature_ids']


def test_symbolic_cost_expansion_matches_full_diagonal_and_binds_parameters():
    from agqo.synthesis.compiler import qiskit_parameterized,walsh_coefficients
    from qiskit.quantum_info import Statevector
    p,h,c,ir=fixture()
    ir['qubit_to_asset']=[1,3,0,2]
    qc,parameters=qiskit_parameterized(ir,c['energies'])
    values=np.linspace(.23,.91,len(ir['parameters']))
    bound=qc.assign_parameters({parameters[p['id']]:float(v) for p,v in zip(ir['parameters'],values)})
    expected=execute(ir,c['energies'],values)
    assert abs(np.vdot(Statevector.from_instruction(bound).data,expected))**2==pytest.approx(1,abs=1e-10)
    coefficients=walsh_coefficients(c['energies'])
    for index,energy in enumerate(c['energies']):
        reconstructed=sum(value*(-1)**((index&mask).bit_count()) for mask,value in enumerate(coefficients))
        assert reconstructed==pytest.approx(energy,abs=1e-12)


def test_decoder_adapter_does_not_weaken_acceptance_of_duplicate_qubits():
    from agqo.synthesis.decoding import decoder_schema
    decoded=decoder_schema(SCHEMA)
    assert 'uniqueItems' not in json.dumps(decoded)
    assert 'uniqueItems' in json.dumps(SCHEMA)
    p,h,c,ir=fixture()
    ir['layers'][0]['mixer'][0]['qubits']=[0,0]
    assert not verify(ir,p,h,c)['valid']


def test_nonfinite_model_constants_are_rejected_as_data_not_an_exception():
    p,h,c,ir=fixture()
    ir['layers'][0]['mixer'][0]['angle']['offset']=float('nan')
    assert check_ir(ir,p,h)['valid'] is False


def test_cpu_prefetch_can_overlap_but_two_gpu_reservations_cannot(tmp_path):
    ledger=BudgetLedger(tmp_path/'ledger.json')
    gpu=ledger.reserve(3,'gpu1',snapshot())
    cpu=ledger.reserve(.25,'prefetch',snapshot(),resource='cpu')
    with pytest.raises(ValueError,match='already reserved'):
        ledger.reserve(2,'gpu2',snapshot())
    ledger.finish(gpu,'completed');gpu2=ledger.reserve(2,'gpu2',snapshot())
    assert gpu2!=gpu
    ledger.finish(cpu,'completed');ledger.finish(gpu2,'completed')
