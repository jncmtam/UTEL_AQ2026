"""Frozen structural test suite and model/data/feedback ablations.

Separate from the opened pilot. Live runs are opt-in, budgeted and resumable;
disabled mode records not_run rather than inventing benchmark accuracy.
"""
from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
import json
import numpy as np

from agqo.repair.data import synthetic_data, make_window
from .profile import data_profile, digest
from .search import SearchConfig, run_search
from .client import SynthesisClient, PROMPT_VERSION
from .budget import BudgetLedger


def test_cases():
    result=[]
    for n in (4,6,8):
        for index, family in enumerate(('new_seed','decorrelated','cluster_shift','unseen_constraints')):
            data=synthetic_data(seed=770001+n*100+index,n=n,periods=240)
            if family=='decorrelated':
                rng=np.random.default_rng(660+n)
                data.returns=rng.normal(0,.01,data.returns.shape)
                data.benchmark=data.returns.mean(axis=1)
            elif family=='cluster_shift':
                rng=np.random.default_rng(550+n)
                factor=rng.normal(0,.012,(240,2))
                data.returns=np.column_stack([factor[:,i%2]+rng.normal(0,.002,240) for i in range(n)])
                data.benchmark=data.returns.mean(axis=1)
            text=f'Hold {n//2} assets'
            if family=='unseen_constraints':
                text+='; Exclude S00; Must hold '+data.tickers[-1]+'; Turnover at most 160%'
            p,*_=make_window(data,n=n,k=n//2,text=text)
            result.append((f'{family}_n{n}',family,p))
    return result


def run_suite(directory,model='next80',mode='disabled',variants=('full',),feedback_levels=('full',),config=SearchConfig()):
    if any(v not in {'full','constraints_only','no_correlation','shuffled'} for v in variants):
        raise ValueError('Unknown variant')
    path=Path(directory);path.mkdir(parents=True,exist_ok=True)
    suite=test_cases()
    protocol={'version':'synthesis-structural-suite-v1','prompt_version':PROMPT_VERSION,'model':model,
              'variants':list(variants),'feedback_levels':list(feedback_levels),'search':asdict(config),
              'cases':[{'id':key,'family':family,'problem_hash':p.fingerprint()} for key,family,p in suite],
              'split':'structural_test_recipes_not_used_in_pilot','qualification':'requires_actual_executions_no_not_run_as_success'}
    protocol_path=path/'suite_protocol.json'
    if protocol_path.exists() and json.loads(protocol_path.read_text())!=protocol:
        raise ValueError('Existing frozen suite differs; use new directory.')
    protocol_path.write_text(json.dumps(protocol,indent=2))
    client=SynthesisClient(model,mode,path/'inference',ledger=BudgetLedger('results/synthesis/budget.json'))
    records=[]
    for index,(key,family,p) in enumerate(suite):
        donor=data_profile(suite[(index+1)%len(suite)][2])
        # Donor must match N to keep ablation dimensions meaningful.
        donor=data_profile(next(pp for kk,ff,pp in suite if pp.n==p.n and kk!=key))
        for variant in variants:
            for feedback in feedback_levels:
                run_dir=path/key/variant/feedback
                output=run_search(p,run_dir,client,config,variant,feedback,donor)
                records.append({'case_id':key,'family':family,'variant':variant,'feedback':feedback,'status':output['status'],
                                'total_shots':output['total_shots'],'path':str(run_dir/'search.json'),
                                'origin':mode,'winner':output['winner_id']})
                (path/'suite_results.json').write_text(json.dumps({'protocol_hash':digest(protocol),'records':records},indent=2))
                # A failure to launch all candidates should stop, not burn credit
                # repeating the same unavailable deployment on every instance.
                statuses=[c['inference'].get('status') for c in output['candidates']]
                if statuses and all(s in {'budget_blocked','error'} for s in statuses):
                    return records
    return records
