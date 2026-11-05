"""Preregistered paired model pilot, repairs, negative controls and honest qualification."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from time import perf_counter
import json
import numpy as np

from agqo.repair.data import synthetic_data, make_window
from agqo.repair.solvers import exact_solve, milp_solve
from agqo.repair.circuits import CircuitSpec, run_qaoa
from .builders import build_rule
from .client import SynthesisClient, request_for, PROMPT_VERSION
from .compiler import verify, export_artifacts
from .optimizer import optimize
from .profile import data_profile, hamiltonian_ir, digest
from .search import _rank
from .thresholds import Targets, quality, assess


def cases():
    output = []
    for n in (4, 6, 8):
        text = f"Hold {n//2} assets" + ("" if n == 4 else "; Exclude S00")
        p,*_ = make_window(synthetic_data(seed=20261031+n, n=n), n=n, k=n//2, text=text)
        output.append((f"n{n}", p))
    return output


def freeze(directory):
    path = Path(directory); path.mkdir(parents=True, exist_ok=True)
    definition = {"version": "paired-pilot-v1", "targets": Targets().to_dict(), "prompt_version": PROMPT_VERSION,
                  "cases": [{"case_id": key, "n": p.n, "problem_hash": p.fingerprint()} for key,p in cases()],
                  "models": ["next80", "coder30"], "evaluation_seeds": [11,23,47],
                  "evaluations": 16, "shots": 128, "max_repair_rounds": 2,
                  "purpose": "development_diagnostic_not_holdout", "sources": "docs/SYNTHESIS_THRESHOLDS.md"}
    target = path / "pilot_protocol.json"
    if target.exists() and json.loads(target.read_text()) != definition:
        raise ValueError("Existing pilot protocol differs; use a new directory/version.")
    target.write_text(json.dumps(definition, indent=2))
    return definition


def negative_controls():
    key,p = cases()[0]
    h,c = hamiltonian_ir(p); ir = build_rule(p,h,data_profile(p))
    faults = {}
    bad=deepcopy(ir);bad['problem_hash']='changed';faults['identity']=bad
    bad=deepcopy(ir);del bad['layers'][0]['cost'];faults['missing_cost']=bad
    bad=deepcopy(ir);bad['layers'][0]['mixer'][0]['qubits']=[0,999];faults['qubit_bounds']=bad
    bad=deepcopy(ir);bad['layers'][0]['mixer'].pop(1);faults['broken_exchange']=bad
    bad=deepcopy(ir);bad['layers'][0]['mixer'][0]['angle']['parameter']='not_declared';faults['unknown_parameter']=bad
    bad=deepcopy(ir);bad['layers'][0]['cost']['parameter']='beta_0';faults['cost_parameter_kind']=bad
    bad=deepcopy(ir);bad['initialization']=[{'op':'H','qubits':[0],'angle':None}];faults['initial_cardinality_leak']=bad
    records=[{'fault':name,'rejected':not verify(bad,p,h,c)['valid']} for name,bad in faults.items()]
    altered=deepcopy(c);altered['energies'][1]+=.1
    records.append({'fault':'cost_table_tampering','rejected':not verify(ir,p,h,altered)['valid']})
    return records


def evaluate_model(model, directory, mode='modal', repair_rounds=2, progress=print):
    if not 0 <= repair_rounds <= 2:
        raise ValueError('At most 2 repair rounds.')
    path=Path(directory);protocol=freeze(path)
    from .budget import BudgetLedger
    client=SynthesisClient(model,mode,path,ledger=BudgetLedger('results/synthesis/budget.json'))
    references={}; context={}; records=[]
    for key,p in cases():
        h,c=hamiltonian_ir(p);context[key]=(p,h,c)
        references[key]={'exact':exact_solve(p),'milp':milp_solve(p)}
    feedback_by_case={};pending=list(context)
    for round_index in range(1+repair_rounds):
        if not pending: break
        requests=[request_for(context[key][0],context[key][1],seed=11+round_index,feedback=feedback_by_case.get(key)) for key in pending]
        progress(f'{model}: round {round_index}, batch {len(requests)}',flush=True)
        try:
            answers=client.batch(requests)
        except ValueError as exc:
            answers=[{'status':'budget_blocked','reason':str(exc)} for _ in requests]
        next_pending=[]
        for key,request,answer in zip(pending,requests,answers,strict=True):
            p,h,c=context[key]
            record={'case_id':key,'round':round_index,'inference':answer,'request_hash':request['request_hash']}
            if answer.get('status')=='ok' and isinstance(answer.get('response'),dict):
                ir=answer['response'];record['gate_ir']=ir
                report=verify(ir,p,h,c);record['verification']=report
                if report['valid']:
                    runs=[optimize(ir,p,c,seed,16,128) for seed in protocol['evaluation_seeds']]
                    record['seed_runs']=runs
                    # All seeds retained, failures count against feasibility/quality.
                    aggregate=dict(runs[0])
                    aggregate['sampled_feasible_probability']=float(np.median([r['sampled_feasible_probability'] for r in runs]))
                    aggregate['total_shots']=sum(r['total_shots'] for r in runs)
                    record['evaluation']=aggregate
                    record['seed_quality']=[quality(p,c,r) for r in runs]
                    record['quality']=quality(p,c,aggregate)
                    record['quality']['normalized_gap']=float(np.median([1.0 if q['normalized_gap'] is None else q['normalized_gap'] for q in record['seed_quality']]))
                    record['quality']['aggregation']='median_across_seeds_with_failed_seed_gap_1'
                    record['chosen']=True
                    representative=runs[0]
                    export_artifacts(ir,c,representative['angles'],path/model/key,report)
                else:
                    next_pending.append(key)
                    feedback_by_case[key]=[{'candidate':ir,'errors':report['errors'],'warnings':report['warnings']}]
            else:
                record['verification']={'valid':False,'errors':[{'code':answer.get('status','error'),'message':answer.get('reason',answer.get('finish_reason','No executable response'))}]}
                if answer.get('status') not in {'not_run','error','budget_blocked'}:
                    next_pending.append(key)
                    feedback_by_case[key]=[{'errors':record['verification']['errors'],'instruction':'Produce a shorter complete GateIR with one layer and sparse exchange edges.'}]
            records.append(record)
        pending=next_pending
        (path/(model+'_pilot_checkpoint.json')).write_text(json.dumps({'protocol':protocol,'records':records,'pending':pending},ensure_ascii=False,indent=2,allow_nan=False))
    baselines=[]
    for key,p in cases():
        h,c=context[key][1:]
        attempts=[r for r in records if r['case_id']==key]
        total=sum(r.get('evaluation',{}).get('total_shots',0) for r in attempts)
        # Baselines receive >= one-run budget even if the LLM produced no valid circuit;
        # that case cannot count as an LLM win.
        calls=max(16,total//(3*128)-1)
        for name in ('fixed_gate_ir','fixed_depth1_superposition','correlation_rule','legacy_fixed_xy'):
            if name=='legacy_fixed_xy':
                runs=[run_qaoa(p,CircuitSpec('XY','ring',2,'previous'),seed,evaluations=calls,shots=128) for seed in protocol['evaluation_seeds']]
                verification=None
            else:
                ir=build_rule(p,h,data_profile(p),fixed=name in {'fixed_gate_ir','fixed_depth1_superposition'},
                              depth=1 if name=='fixed_depth1_superposition' else 2)
                verification=verify(ir,p,h,c)
                runs=[optimize(ir,p,c,seed,calls,128) for seed in protocol['evaluation_seeds']]
            baselines.append({'case_id':key,'method':name,'runs':runs,'quality':[quality(p,c,r) for r in runs],
                              'verification':verification,'total_shots':sum(r['total_shots'] for r in runs)})
    # Explicit failed winner placeholders keep unsuccessful instances in G2 denominators.
    assessment_records=list(records)
    for key,p in cases():
        if not any(r.get('chosen') for r in records if r['case_id']==key):
            _,_,c=context[key]
            assessment_records.append({'case_id':key,'round':99,'chosen':True,'verification':{'valid':False},
                                       'evaluation':{'sampled_feasible_probability':0,'feasible':False},
                                       'quality':quality(p,c,{'feasible':False})})
    assessment=assess(assessment_records,3)
    comparisons=[]
    for key,p in cases():
        winner=next((r for r in records if r['case_id']==key and r.get('chosen')),None)
        # Also compare a shallow non-LLM circuit so depth-1 LLM wins cannot be
        # attributed merely to choosing fewer layers than a depth-2 reference.
        fixed_candidates=[r for r in baselines if r['case_id']==key and r['method'] in {'fixed_gate_ir','fixed_depth1_superposition'}]
        fixed=min(fixed_candidates,key=lambda b:(-float(np.median([r['sampled_feasible_probability'] for r in b['runs']])),
                    float(np.median([1. if q['normalized_gap'] is None else q['normalized_gap'] for q in b['quality']])),
                    b['verification']['resources']['transpiled_cx']))
        if winner:
            llm_gap=winner['quality']['normalized_gap']
            fixed_gap=float(np.median([1.0 if q['normalized_gap'] is None else q['normalized_gap'] for q in fixed['quality']]))
            reference_cx=fixed['verification']['resources']['transpiled_cx']
            llm_cx=winner['verification']['resources']['transpiled_cx']
            feasibility_change=winner['evaluation']['sampled_feasible_probability']-float(np.median([r['sampled_feasible_probability'] for r in fixed['runs']]))
            improvement=None if fixed_gap<=1e-14 else (fixed_gap-llm_gap)/fixed_gap
            reduction=(reference_cx-llm_cx)/max(1,reference_cx)
            comparisons.append({'case_id':key,'relative_gap_improvement':improvement,'relative_cx_reduction':reduction,
                                'reference_method':fixed['method'],
                                'normalized_gap_change':llm_gap-fixed_gap,'feasible_probability_change':feasibility_change,
                                'G3_case_met':bool((improvement is not None and improvement>=.2 and feasibility_change>=-.01) or (reduction>=.2 and llm_gap-fixed_gap<=.01 and feasibility_change>=-.01))})
        else:
            comparisons.append({'case_id':key,'G3_case_met':False,'reason':'No verified LLM circuit; no improvement claimed.'})
    output={'model':model,'protocol':protocol,'protocol_hash':digest(protocol),'records':records,'baselines':baselines,'paired_comparisons':comparisons,
            'references':references,'negative_controls':negative_controls(),'assessment':assessment,
            'total_shots':sum(r.get('evaluation',{}).get('total_shots',0) for r in records),
            'independent_instances':3,'claims':{'qualified':False,'holdout':False,'quantum_advantage':False}}
    output['source_sha256']=digest({p.name:p.read_text() for p in sorted(Path(__file__).parent.glob('*.py'))})
    (path/(model+'_pilot.json')).write_text(json.dumps(output,ensure_ascii=False,indent=2,allow_nan=False))
    progress(json.dumps({'model':model,**assessment},ensure_ascii=False),flush=True)
    return output


def report_pilot(directory):
    path=Path(directory)
    outputs=[json.loads(p.read_text()) for p in sorted(path.glob('*_pilot.json'))]
    lines=['# GateIR — kết quả pilot Modal','',
           'Ba instance N=4,6,8 là tập phát triển chẩn đoán. Ngưỡng được ghi trước khi gọi model; cần ít nhất 10 instance độc lập để xét qualification.',
           '', '| Model | Đúng lần đầu | Có mạch sau sửa | Median feasibility | Median normalized gap | Qualification |',
           '|---|---:|---:|---:|---:|---|']
    for output in outputs:
        a=output['assessment']
        fmt=lambda v:'—' if v is None else f'{100*v:.1f}%'
        lines.append(f"| {output['model']} | {fmt(a['first_valid_rate'])} | {fmt(a['valid_instance_rate'])} | {fmt(a['median_feasible_probability'])} | {fmt(a['median_normalized_gap'])} | Chưa đủ mẫu |")
    lines+=['','## Chi tiết từng trường hợp','']
    for output in outputs:
        lines+=['### '+output['model'],'']
        for row in output['records']:
            v=row['verification'];status='đạt verifier' if v['valid'] else 'bị từ chối'
            reason='; '.join(e['message'][:350] for e in v.get('errors',[]))
            lines.append(f"- {row['case_id']}, vòng {row['round']}: {status}. {reason}")
        lines+=['','| Case | Feasibility (median seed) | Normalized gap | CX sau lowering | Active / declared parameters |',
                '|---|---:|---:|---:|---:|']
        for row in output['records']:
            if row.get('chosen'):
                v=row['verification']; q=row['quality']; e=row['evaluation']
                lines.append(f"| {row['case_id']} | {100*e['sampled_feasible_probability']:.1f}% | {100*q['normalized_gap']:.2f}% | {v['resources']['transpiled_cx']} | {v['active_parameters']}/{v['declared_parameters']} |")
        lines+=['','| Case | Giảm gap so fixed | Giảm CX so fixed | G3 ở case |','|---|---:|---:|---|']
        for row in output.get('paired_comparisons',[]):
            fmt=lambda v:'—' if v is None else f'{100*v:.1f}%'
            lines.append(f"| {row['case_id']} | {fmt(row.get('relative_gap_improvement'))} | {fmt(row.get('relative_cx_reduction'))} | {'đạt mục tiêu case' if row['G3_case_met'] else 'chưa đạt'} |")
        lines+=['','Các seed được báo trong JSON riêng; không coi seed là thêm instance tài chính độc lập. Cổng G3 ở một case chỉ là tín hiệu pilot, không đủ cho tuyên bố tổng quát.','']
    lines+=['## Cách đọc và kết luận','',
            '- G0 kiểm nghĩa/phase/register; G1 đo tỷ lệ sinh đúng; G2 đo nghiệm; G3 cần đối chứng tài nguyên/chất lượng trên tập chưa mở.',
            '- Đề xuất lỗi, cắt ngắn và instance không có mạch đúng không bị bỏ khỏi mẫu.',
            '- Bảng trên không khẳng định model đủ chính xác cho mọi mạch. Model lớn hơn chỉ thắng nếu các phép đo ủng hộ.',
            '- Oracle COST vẫn cần 2^N giá trị dựng trên CPU; chưa có cơ sở cho quantum advantage.',
            '- Reservation trong budget.json là cận bảo thủ; hóa đơn billing được chụp riêng, có thể cập nhật trễ.',
            '', 'Nguồn và cơ sở ngưỡng: [SYNTHESIS_THRESHOLDS](../../../docs/SYNTHESIS_THRESHOLDS.md).']
    (path/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    if outputs:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        catalog=[]
        labels=[o['model'] for o in outputs]
        x=np.arange(len(outputs));width=.34
        fig,ax=plt.subplots(figsize=(8,4))
        ax.bar(x-width/2,[100*o['assessment']['first_valid_rate'] for o in outputs],width,label='First attempt')
        ax.bar(x+width/2,[100*o['assessment']['valid_instance_rate'] for o in outputs],width,label='After repair')
        ax.axhline(80,color='gray',linestyle='--',label='First-attempt target 80%')
        ax.set(xticks=x,xticklabels=labels,ylim=(0,105),ylabel='Verified instances (%)',title='GateIR correctness · diagnostic pilot (3 cases per model)');ax.legend(fontsize=8)
        fig.tight_layout();fig.savefig(path/'01_correctness.png',dpi=160);plt.close(fig)
        catalog.append({'path':'01_correctness.png','title':'Tỷ lệ mạch đúng trước/sau sửa','caption':'Ba bài N=4,6,8 mỗi model; đề xuất lỗi/cắt ngắn vẫn ở mẫu. Đường 80% là mục tiêu dự án, không phải kết quả paper hay chứng nhận tổng quát.'})
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        for output in outputs:
            valid=[r for r in output['records'] if r.get('chosen')]
            axes[0].plot([int(r['case_id'][1:]) for r in valid],[100*r['evaluation']['sampled_feasible_probability'] for r in valid],'o-',label=output['model'])
            axes[1].plot([int(r['case_id'][1:]) for r in valid],[100*r['quality']['normalized_gap'] for r in valid],'o-',label=output['model'])
        axes[0].axhline(90,color='gray',linestyle='--');axes[1].axhline(5,color='gray',linestyle='--')
        axes[0].set(xlabel='Assets/qubits',ylabel='Median feasible shots (%)',ylim=(0,105))
        axes[1].set(xlabel='Assets/qubits',ylabel='Median normalized objective gap (%)')
        for ax in axes:ax.set_xticks([4,6,8]);ax.legend(fontsize=8)
        fig.tight_layout();fig.savefig(path/'02_quality.png',dpi=160);plt.close(fig)
        catalog.append({'path':'02_quality.png','title':'Khả thi và chất lượng theo quy mô','caption':'Chỉ case có mạch được verifier chấp nhận mới có đường biểu diễn; case không có mạch bị tính là failure trong bảng G2. Median qua ba seed, chưa là ba bài độc lập. Đường mục tiêu: 90% feasibility, 5% normalized gap.'})
        (path/'figure_catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2))
        with (path/'REPORT.md').open('a',encoding='utf-8') as handle:
            for i,item in enumerate(catalog,1):
                handle.write(f"\n\n![{item['title']}]({item['path']})\n\n**Hình {i}. {item['title']}.** {item['caption']} Nguồn: synthetic factor fixtures; không có kết quả QPU.\n")
    return outputs
