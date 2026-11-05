"""Summarize immutable live inference records; never calls a model or optimizer."""
from pathlib import Path
import json
import numpy as np

from .pilot import cases
from .profile import hamiltonian_ir, data_profile
from .typed import domain


def median(rows,key):
    values=[r[key] for r in rows if r.get(key) is not None]
    return None if not values else float(np.median(values))


def write_report(directory='results/synthesis/typed_pilot'):
    path=Path(directory)
    outputs=[json.loads(f.read_text()) for f in sorted(path.glob('*_pilot.json'))]
    base=json.loads((path/'baselines.json').read_text())
    ledger=json.loads(Path('results/synthesis/budget.json').read_text())
    rows=[]; model_summary=[]; edge_evidence=[]
    problems=dict(cases())
    for output in outputs:
        for record in output['records']:
            v=record['verification'];runs=record.get('seed_runs',[])
            program=record['inference'].get('response')
            if isinstance(program,dict) and 'mixer' in program:
                p=problems[record['case_id']];d=domain(p);profile=data_profile(p);q=p.objective_qubo()
                gates=[('preparation',program.get('preparation_edge'))]+[('mixer',g.get('edge')) for g in program['mixer']]
                for stage,key in gates:
                    if key not in d['edges']:continue
                    i,j=d['edges'][key]
                    edge_evidence.append({'model':output['model'],'case_id':record['case_id'],'stage':stage,'edge':key,
                                          'assets':[p.tickers[i],p.tickers[j]],'correlation':profile['correlation'][i][j],
                                          'coefficient_id':f'J_{i}_{j}','quadratic_coefficient':float(q.quadratic[i,j]),
                                          'basis_bits':[d['initial_bits'][i],d['initial_bits'][j]],
                                          'interpretation':'Deterministic lookup; association only, not proof of causal use by LLM.'})
            rows.append({'method':output['model'],'case_id':record['case_id'],'valid':v['valid'],
                         'feasibility':median(runs,'sampled_feasible_probability') if runs else 0.,
                         'normalized_gap':record['quality']['normalized_gap'],
                         'probability_optimal':median(runs,'probability_optimal'),
                         'probability_near_optimal_5pct':median(runs,'probability_near_optimal_5pct'),
                         'encoded_energy_expectation':median(runs,'encoded_energy_expectation'),
                         'cx':v.get('resources',{}).get('transpiled_cx'),
                         'active_parameters':v.get('active_parameters'),
                         'declared_parameters':v.get('declared_parameters'),
                         'errors':v.get('errors',[])})
        model_summary.append({'model':output['model'],**output['assessment'],
                              'input_tokens':sum(r['inference'].get('usage',{}).get('input_tokens',0) for r in output['records']),
                              'output_tokens':sum(r['inference'].get('usage',{}).get('output_tokens',0) for r in output['records']),
                              'inference_batch_seconds':max(r['inference'].get('batch_elapsed_seconds',0) for r in output['records'])})
    for record in base['records']:
        v=record['verification'];runs=record['seed_runs']
        rows.append({'method':record['method'],'case_id':record['case_id'],'valid':v['valid'],
                     'feasibility':median(runs,'sampled_feasible_probability'),
                     'normalized_gap':float(np.median([1. if q['normalized_gap'] is None else q['normalized_gap'] for q in record['seed_quality']])),
                     'probability_optimal':median(runs,'probability_optimal'),
                     'probability_near_optimal_5pct':median(runs,'probability_near_optimal_5pct'),
                     'encoded_energy_expectation':median(runs,'encoded_energy_expectation'),
                     'cx':v['resources']['transpiled_cx'],
                     'active_parameters':v['active_parameters'],'declared_parameters':v['declared_parameters']})
    uniform=[]
    for key,p in cases():
        h,c=hamiltonian_ir(p);values=c['objective'][c['feasible']]
        count=len(values);span=float(np.ptp(values));opt=float(values.min())
        probability=float(np.mean(values<=opt+1e-12))
        uniform.append({'case_id':key,'feasible_states':count,'probability_optimal':probability,
                        'best_of_128_hits_optimum_probability':1-(1-probability)**128,
                        'normalized_expected_gap':0. if span<=1e-14 else float((values.mean()-opt)/span),
                        'role':'enumerated_uniform_feasible_distribution_diagnostic_not_paid_search'})
    comparisons=[]
    for row in rows:
        if row['method'] not in {'next80','coder30'}:continue
        refs=[r for r in rows if r['case_id']==row['case_id'] and r['method'] in base['protocol']['baseline_methods']]
        strongest=min(refs,key=lambda r:(-r['feasibility'],r['normalized_gap'],r['cx']))
        gap=row['normalized_gap'];fg=strongest['normalized_gap']
        reduction=None if row['cx'] is None else (strongest['cx']-row['cx'])/max(1,strongest['cx'])
        improvement=None if gap is None or fg<=1e-14 else (fg-gap)/fg
        feas_delta=row['feasibility']-strongest['feasibility']
        met=row['valid'] and feas_delta>=-.01 and ((improvement is not None and improvement>=.2) or
                    (reduction is not None and reduction>=.2 and gap-fg<=.01))
        comparisons.append({'model':row['method'],'case_id':row['case_id'],'reference':strongest['method'],
                            'relative_cx_reduction':reduction,'relative_gap_improvement':improvement,'G3_case_met':met,
                            'selection_rule':'strongest pilot baseline by feasibility, best gap, CX; not a claim against ADAPT or exhaustive search'})
    (path/'selected_edge_evidence.json').write_text(json.dumps(edge_evidence,ensure_ascii=False,indent=2))
    summary={'version':'live-evidence-v2','model_summary':model_summary,'rows':rows,'uniform_diagnostic':uniform,
             'paired_comparisons':comparisons,'reserved_usd_total':sum(j['reserved_usd'] for j in ledger['jobs']),
             'qualified':False,'holdout':False,'quantum_advantage':False}
    (path/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,allow_nan=False))
    def percent(x):
        if x is None:return '—'
        if 0<x<.001:return f'{100*x:.4f}%'
        if .9999<x<1:return '>99.99%'
        return f'{100*x:.1f}%'
    lines=['# Thực nghiệm Modal: GateIR tự do và typed exchange','',
           'Đây là kết quả phát triển trên ba instance synthetic N=4,6,8; không phải kiểm tra ngoài mẫu hoặc giao dịch thật.',
           'Raw inference, request hash, model revision, verifier và các seed được lưu cùng thư mục. Không loại failure khỏi tỷ lệ đạt.','',
           '## Kết luận về sinh đúng','',
           '| Protocol | Model | Đúng lần đầu | Có mạch sau sửa |','|---|---|---:|---:|']
    for model in ('next80','coder30'):
        v1=json.loads((Path('results/synthesis/pilot')/(model+'_pilot.json')).read_text())['assessment']
        lines.append(f"| GateIR v1, tối đa 2 sửa | {model} | {percent(v1['first_valid_rate'])} | {percent(v1['valid_instance_rate'])} |")
    for item in model_summary:
        lines.append(f"| Typed v2, không sửa | {item['model']} | {percent(item['first_valid_rate'])} | {percent(item['valid_instance_rate'])} |")
    lines+=['','V2 khóa cardinality/include/exclude và hạ EXCHANGE thành cặp RXX–RYY bằng compiler. Tỷ lệ đúng v2 không thể quy hoàn toàn cho model; v2 là task hẹp hơn. Chỉ có ba bài độc lập nên chưa model nào được qualification.',
            'Pilot chỉ gồm K-of-N và exclude S00 ở N=6,8; chưa kiểm tra live đầy đủ tổ hợp sector cap/turnover hay mandate mâu thuẫn. N=8 bị chặn bởi quy tắc thiết kế mixer liên thông của protocol; đồ thị không liên thông tự nó không có nghĩa mạch không unitary hoặc phá cardinality.',
            'Lượt khởi động đầu v1 gặp lỗi backend structured decoding không hỗ trợ uniqueItems trước khi sinh token. Đã sửa adapter, vẫn giữ strict validator. Lượt lỗi hạ tầng được tính ngân sách, tách khỏi tỷ lệ đúng ngữ nghĩa của các đề xuất model thực sự sinh ra.',
            'V1 từng có tín hiệu giảm CX khi so với fixed p=2. Sau đối chiếu thêm fixed p=1, tín hiệu đó biến mất; báo cáo hiện dùng baseline cùng độ sâu và không giữ kết luận giảm cổng cũ.','',
            '## Chất lượng và đối chứng cùng grammar','',
            'Mỗi phương pháp một kiến trúc; ba seed, 16 evaluations ×128 shots và 128 shots đo cuối mỗi seed. P(optimum) là xác suất lý tưởng của trạng thái cuối, không phải tần suất best-of-shots.','',
            '| Case | Phương pháp | Hợp lệ | Feasible shots | Best gap | P(optimum) | CX | Tham số active/tổng |',
            '|---|---|---|---:|---:|---:|---:|---:|']
    for row in sorted(rows,key=lambda r:(int(r['case_id'][1:]),r['method'])):
        parameters='—' if row['declared_parameters'] is None else f"{row['active_parameters']}/{row['declared_parameters']}"
        lines.append(f"| {row['case_id']} | {row['method']} | {'đạt' if row['valid'] else 'lỗi'} | {percent(row['feasibility'])} | {percent(row['normalized_gap'])} | {percent(row['probability_optimal'])} | {row['cx'] if row['cx'] is not None else '—'} | {parameters} |")
    for row in rows:
        if row.get('errors'):lines.append(f"\nLỗi {row['method']} {row['case_id']}: "+json.dumps(row['errors'],ensure_ascii=False))
    lines+=['','## Kiểm tra độ khó của chỉ số best-of-shots','',
            '| Case | Số nghiệm khả thi | P(optimum) nếu lấy đều | P(best-of-128 gặp optimum) |','|---|---:|---:|---:|']
    for r in uniform:
        lines.append(f"| {r['case_id']} | {r['feasible_states']} | {percent(r['probability_optimal'])} | {percent(r['best_of_128_hits_optimum_probability'])} |")
    lines+=['','Phân phối đều được tính bằng vét cạn để chẩn đoán benchmark nhỏ. Best gap=0 có thể dễ đạt mà không cần LLM hay QAOA; phải đọc thêm phân phối và chất lượng kỳ vọng. Không đổi ngưỡng v1 sau khi xem kết quả.',
            'File selected_edge_evidence.json tra lại tài sản, correlation và hệ số J thật của từng cạnh được chọn. Rationale tự do của LLM chưa được xác minh ngữ nghĩa: việc cite đúng feature ID không chứng minh giải thích đúng hoặc descriptor gây ra lựa chọn cạnh. Cần profile ablation trên tập độc lập.','',
            '## Điều kiện tăng thêm G3','']
    for r in comparisons:
        lines.append(f"- {r['model']} {r['case_id']}: {'đạt tín hiệu case' if r['G3_case_met'] else 'chưa đạt'}; so {r['reference']}; giảm CX {percent(r['relative_cx_reduction'])}; giảm gap tương đối {percent(r['relative_gap_improvement'])}.")
    lines+=['','Ngay cả một case đạt cũng chưa là cải thiện tổng quát. Chưa có đối chứng ADAPT, structure search nhiều ứng viên hoặc profile ablation live; không kết luận LLM vượt các phương pháp đó.','',
            '## Chi phí và khả năng tái lập','',
            f"Tổng reservation bảo thủ: **{summary['reserved_usd_total']:.2f}/25 USD**, gồm lượt lỗi hạ tầng và các lượt sửa v1. Đây không phải số tiền đã tính hóa đơn."]
    billing=path/'billing_after.json'
    if billing.exists():
        b=json.loads(billing.read_text());lines.append(f"Billing snapshot {b['checked_utc']}: metered cả tháng **{b['metered_cost']:.4f} USD**, billed **{b['billed_cost']:.2f} USD**; có thể điều chỉnh trễ, không phải chi phí riêng v2 hoặc số dư credit còn lại.")
    for item in model_summary:
        lines.append(f"- {item['model']}: {item['input_tokens']} input + {item['output_tokens']} output tokens; batch end-to-end {item['inference_batch_seconds']:.1f}s gồm cold start/load.")
    lines+=['','COST vẫn dựng từ bảng 2^N trên CPU, resource target generic rz/sx/x/cx, không phải topology/QPU cụ thể. Mọi kết quả quantum là mô phỏng.','',
            'Kế hoạch và nguồn: [quyết định nghiên cứu](../../../docs/SYNTHESIS_RESEARCH_DECISION.md); [ngưỡng](../../../docs/SYNTHESIS_THRESHOLDS.md).',
            'Tái tính báo cáo: `.venv/bin/python -m agqo.synthesis.evidence_report` (không gọi GPU).']
    (path/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    return summary


if __name__=='__main__':
    write_report()
