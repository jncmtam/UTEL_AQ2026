"""One bounded v2 follow-up on the opened development cases; never a holdout."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np

from agqo.repair.solvers import exact_solve, milp_solve
from .budget import BudgetLedger, MODELS, billing_snapshot
from .client import SynthesisClient
from .compiler import verify, export_artifacts
from .optimizer import optimize
from .pilot import cases
from .profile import data_profile, hamiltonian_ir, digest
from .thresholds import Targets, quality, assess
from .typed import VERSION, domain, typed_request, lower, baseline_program


def run(directory='results/synthesis/typed_pilot', mode='modal'):
    path=Path(directory);path.mkdir(parents=True,exist_ok=True)
    context={key:(p,*hamiltonian_ir(p)) for key,p in cases()}
    requests=[typed_request(p,h) for p,h,c in context.values()]
    protocol={'version':VERSION,'purpose':'opened_development_followup_not_holdout',
              'prior_evidence':'results/synthesis/pilot/*_pilot.json',
              'hypothesis':'Typed exchanges prevent the gate-arity, pairing and basis-cardinality errors seen in v1.',
              'cases':[{ 'case_id':key,'problem_hash':p.fingerprint()} for key,(p,h,c) in context.items()],
              'models':MODELS,'request_hashes':[r['request_hash'] for r in requests],
              'seeds':[11,23,47],'evaluations':16,'shots':128,'proposals_per_case':1,'repair_rounds':0,
              'targets':Targets().to_dict(),'max_additional_gpu_reservation_usd':4.90,
              'baseline_methods':['fixed_path','correlation_path','random_path'],
              'baseline_contract':'Identical typed domain, fixed preparation angle, one layer, one architecture per method; same optimizer calls and seeds.',
              'stop_rule':'One batch per model; no automatic paid retries or new credit assumption.'}
    target=path/'protocol.json'
    if target.exists() and json.loads(target.read_text())!=protocol:
        raise ValueError('Protocol changed; create a separate output directory.')
    target.write_text(json.dumps(protocol,ensure_ascii=False,indent=2))
    baselines=[];references={}
    for key,(p,h,c) in context.items():
        references[key]={'exact':exact_solve(p),'milp':milp_solve(p)}
        for name in protocol['baseline_methods']:
            program=baseline_program(p,data_profile(p),seed=101 if name=='random_path' else None,
                                     correlation=name=='correlation_path')
            ir=lower(program,p,h);verification=verify(ir,p,h,c)
            if not verification['valid']:raise ValueError('Baseline failed independent verifier.')
            runs=[optimize(ir,p,c,s,16,128) for s in protocol['seeds']]
            baselines.append({'case_id':key,'method':name,'program':program,'verification':verification,
                              'seed_runs':runs,'seed_quality':[quality(p,c,r) for r in runs]})
    (path/'baselines.json').write_text(json.dumps({'protocol':protocol,'records':baselines,'references':references},indent=2))
    outputs=[]
    for model in protocol['models']:
        print(f'{VERSION}: {model}, one batch of {len(requests)}, no repair',flush=True)
        client=SynthesisClient(model,mode,path,ledger=BudgetLedger('results/synthesis/budget.json'))
        answers=client.batch(requests);records=[]
        for (key,(p,h,c)),request,answer in zip(context.items(),requests,answers,strict=True):
            record={'case_id':key,'round':0,'inference':answer,'request_hash':request['request_hash'],
                    'chosen':True,'verification':{'valid':False,'errors':[]},
                    'evaluation':{'sampled_feasible_probability':0,'feasible':False},
                    'quality':quality(p,c,{'feasible':False})}
            if answer.get('status')=='ok':
                try:
                    program=answer['response'];ir=lower(program,p,h);v=verify(ir,p,h,c)
                    if 'gamma_0' in v.get('inactive_parameters',[]):
                        v['valid']=False
                        v['errors'].append({'code':'inactive_cost','message':'Gamma is numerically inactive after preparation.'})
                    record.update(program=program,gate_ir=ir,verification=v)
                    if v['valid']:
                        runs=[optimize(ir,p,c,s,16,128) for s in protocol['seeds']]
                        qs=[quality(p,c,r) for r in runs]
                        record.update(seed_runs=runs,seed_quality=qs,
                                      evaluation={**runs[0],'sampled_feasible_probability':float(np.median([r['sampled_feasible_probability'] for r in runs])),
                                                  'total_shots':sum(r['total_shots'] for r in runs)},
                                      quality={**qs[0],'normalized_gap':float(np.median([1. if q['normalized_gap'] is None else q['normalized_gap'] for q in qs]))})
                        artifact=path/model/key
                        export_artifacts(ir,c,runs[0]['angles'],artifact,v)
                        (artifact/'typed_program.json').write_text(json.dumps(program,indent=2))
                        (artifact/'design_provenance.json').write_text(json.dumps({
                            'llm_owned':['preparation_edge','ordered mixer edge IDs','beta sharing groups','rationale'],
                            'compiler_owned':['basis bits','include/exclude frozen qubits','COST','parameter names','RXX/RYY decomposition'],
                            'domain':domain(p),'request_hash':request['request_hash']},indent=2))
                except (ValueError,TypeError,KeyError) as exc:
                    record['verification']={'valid':False,'errors':[{'code':'typed_program','message':str(exc)}]}
            else:
                record['verification']['errors']=[{'code':answer.get('status','error'),'message':answer.get('reason','No complete model output')}]
            records.append(record)
        output={'model':model,'protocol':protocol,'records':records,'assessment':assess(records,len(context)),
                'source_sha256':digest({f.name:f.read_text() for f in sorted(Path(__file__).parent.glob('*.py'))}),
                'claims':{'qualified':False,'holdout':False,'quantum_advantage':False}}
        (path/(model+'_pilot.json')).write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False))
        outputs.append(output)
        print(json.dumps({'model':model,**output['assessment']},ensure_ascii=False),flush=True)
    if mode=='modal':
        (path/'billing_after.json').write_text(json.dumps(billing_snapshot(),indent=2))
    return outputs


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--mode',choices=['modal','replay','disabled'],default='disabled')
    parser.add_argument('--output',default='results/synthesis/typed_pilot')
    args=parser.parse_args();run(args.output,args.mode)
