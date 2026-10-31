"""Verified gate synthesis: offline smoke, budgeted live pilot and bounded search."""
import argparse
from dataclasses import replace
from pathlib import Path
import json

from agqo.repair.data import synthetic_data,make_window
from .budget import BudgetLedger,billing_snapshot
from .client import SynthesisClient
from .pilot import evaluate_model, freeze, report_pilot
from .search import run_search,SearchConfig


def main():
    parser=argparse.ArgumentParser(description='Verified data-conditioned GateIR QAOA synthesis')
    parser.add_argument('command',choices=['search','pilot','benchmark','billing','report'])
    parser.add_argument('--mode',choices=['disabled','modal','replay','rules'],default='disabled')
    parser.add_argument('--model',choices=['next80','coder30','both'],default='next80')
    parser.add_argument('--output',default='results/synthesis/pilot')
    parser.add_argument('--n',type=int,default=4)
    parser.add_argument('--repair-rounds',type=int,choices=[0,1,2],default=2)
    parser.add_argument('--ablation',choices=['full','constraints_only','no_correlation','shuffled'],default='full')
    parser.add_argument('--feedback',choices=['none','verifier','full'],default='full')
    parser.add_argument('--angle-initialization',choices=['standard','proposed'],default='standard')
    args=parser.parse_args()
    if args.command=='billing':
        print(json.dumps(billing_snapshot(),indent=2));return 0
    if args.command=='report':
        report_pilot(args.output);print(str(Path(args.output)/'REPORT.md'));return 0
    if args.command=='pilot':
        freeze(args.output)
        for model in ['next80','coder30'] if args.model=='both' else [args.model]:
            evaluate_model(model,args.output,args.mode if args.mode!='rules' else 'disabled',args.repair_rounds)
            report_pilot(args.output)
        return 0
    if args.command=='benchmark':
        if args.model=='both':parser.error('benchmark accepts one frozen model')
        from .benchmark import run_suite
        records=run_suite(args.output,args.model,args.mode if args.mode!='rules' else 'disabled',
                          variants=(args.ablation,),feedback_levels=(args.feedback,),
                          config=SearchConfig(repair_rounds=args.repair_rounds,use_proposed_angles=args.angle_initialization=='proposed'))
        print(json.dumps({'records':len(records),'output':args.output}));return 0
    if args.model=='both':parser.error('search accepts one model')
    p,*_=make_window(synthetic_data(n=args.n),n=args.n,k=args.n//2,text=f'Hold {args.n//2} assets')
    client=None if args.mode=='rules' else SynthesisClient(args.model,args.mode,args.output,ledger=BudgetLedger('results/synthesis/budget.json'))
    donor=None
    if args.ablation=='shuffled':
        from .profile import data_profile
        donor_p,*_=make_window(synthetic_data(seed=989,n=args.n),n=args.n,k=args.n//2,text=f'Hold {args.n//2} assets')
        donor=data_profile(donor_p)
    result=run_search(p,args.output,client,config=SearchConfig(repair_rounds=args.repair_rounds,use_proposed_angles=args.angle_initialization=='proposed'),ablation=args.ablation,feedback_level=args.feedback,donor=donor)
    print(json.dumps({'status':result['status'],'total_shots':result['total_shots'],'output':args.output}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
