"""Descriptive data-quality assessment only; no trading or model selection.

Price diagnostics use development observations (2014--2018). Held-out years are
inspected for coverage only. Missing securities are reported, never replaced.
"""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
from sklearn.covariance import LedoitWolf


def main():
    root=Path('data/us_equities');out=Path('results/data_assessment');out.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((root/'dataset_manifest.json').read_text());rows=[];prices={}
    for security in manifest['securities']+[{'ticker_at_inception':'DIA','asset_id':'DIA'}]:
        ticker=security['ticker_at_inception'];path=root/'raw'/f'{ticker}.json'
        row={'ticker':ticker,'asset_id':security['asset_id'],'available':path.exists()}
        if path.exists():
            payload=json.loads(path.read_text())['chart']['result'][0];meta=payload['meta'];indicators=payload['indicators']
            dates=pd.to_datetime(payload['timestamp'],unit='s',utc=True).tz_convert('America/New_York').normalize().tz_localize(None)
            adjusted=np.array(indicators.get('adjclose',[{}])[0].get('adjclose',[]),dtype=float)
            close=np.array(indicators['quote'][0]['close'],dtype=float)
            series=pd.Series(adjusted,index=dates);prices[ticker]=series
            valid=series[np.isfinite(series)&(series>0)]
            daily=valid.loc['2014-01-01':'2018-12-31'].pct_change(fill_method=None)
            dev_mask=(dates >= pd.Timestamp('2014-01-01')) & (dates <= pd.Timestamp('2018-12-31'))
            row.update(provider_name=meta.get('longName'),provider_symbol=meta.get('symbol'),
                first_date=str(dates.min().date()),last_date=str(dates.max().date()),observations=len(series),
                missing_adjusted=int((~np.isfinite(adjusted)).sum()),nonpositive_adjusted=int((adjusted<=0).sum()),
                duplicate_dates=int(dates.duplicated().sum()),splits=len(payload.get('events',{}).get('splits',{})),
                dividends=len(payload.get('events',{}).get('dividends',{})),
                absolute_daily_moves_above_20pct=int((daily.abs()>.2).sum()),
                adjustment_factor_min=float(np.nanmin((adjusted/close)[dev_mask])),adjustment_factor_max=float(np.nanmax((adjusted/close)[dev_mask])),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        rows.append(row)
    frame=pd.DataFrame(prices).sort_index();development=frame.loc['2014-01-01':'2018-12-31']
    # No forward/back fill or ticker substitution. Available-series subset is
    # a diagnostic panel, not an approved investment universe.
    returns=development.pct_change(fill_method=None).iloc[1:]
    complete=returns.dropna();asset_names=[t for t in complete if t!='DIA']
    r=complete[asset_names].to_numpy();benchmark=complete['DIA'].to_numpy()
    cov=np.cov(r,rowvar=False);corr=np.corrcoef(r,rowvar=False);eigen=np.linalg.eigvalsh(cov)
    off=corr[np.triu_indices(len(asset_names),1)];shrink=LedoitWolf().fit(r)
    gram=r.T@r/len(r);interactions=2*gram[np.triu_indices(len(asset_names),1)]
    stability=[]
    for end in range(252,len(complete)+1,63):
        window=r[end-252:end];c=np.corrcoef(window,rowvar=False);ev=np.linalg.eigvalsh(np.cov(window,rowvar=False))
        stability.append({'last_date':str(complete.index[end-1].date()),'mean_pair_correlation':float(c[np.triu_indices(len(asset_names),1)].mean()),
                          'effective_rank':float(ev.sum()**2/(ev@ev))})
    result={'version':'development-descriptive-assessment-v1','dataset_status':'unverified_candidate',
        'analysis_purpose':'Data suitability and technical hypotheses only; no investment performance or financial optimizer evaluation.',
        'development_period':['2014-01-01','2018-12-31'],'heldout_policy':'2022--2025 coverage audit only; no return-shape fitting or strategy evaluation.',
        'requested_asset_count':len(manifest['securities']),'downloaded_assets':sum(x['available'] for x in rows if x['ticker']!='DIA'),
        'missing_tickers':[x['ticker'] for x in rows if not x['available']],
        'diagnostic_panel_assets':asset_names,'development_complete_observations':len(complete),
        'development_rows_removed_for_missing':len(returns)-len(complete),
        'asset_identity_verified_count':sum(bool(s.get('identity_verified')) for s in manifest['securities']),
        'historical_context_records':len(manifest.get('context',[])),
        'pairwise_correlation_quantiles':np.quantile(off,[0,.25,.5,.75,1]).tolist(),
        'covariance_eigenvalues':eigen.tolist(),'effective_rank_trace_squared':float(eigen.sum()**2/(eigen@eigen)),
        'sample_covariance_condition_number':float(np.linalg.cond(cov)),
        'ledoit_wolf_condition_number':float(np.linalg.cond(shrink.covariance_)),
        'ledoit_wolf_shrinkage':float(shrink.shrinkage_),
        'nonzero_pair_interaction_fraction_at_1e_minus_12':float(np.mean(abs(interactions)>1e-12)),
        'coefficient_absolute_quantiles':np.quantile(abs(interactions),[0,.25,.5,.75,1]).tolist(),
        'rolling_252_session_stride_63':stability,'coverage':rows,
        'formulas':{'effective_rank':'trace(Sigma)^2 / trace(Sigma^2), participation ratio; not entropy rank',
                    'tracking_pair_coefficient_before_K_scaling':'2*(R.T@R/T)_ij',
                    'condition':'largest singular value / smallest singular value',
                    'returns':'adjusted_price_t/adjusted_price_previous_session - 1, no filling'},
        'prohibited_inferences':['29 downloaded tickers do not define the final universe.',
            'Provider continuity does not certify continuity of the historical security.',
            'Dense interactions do not prove classical hardness.',
            'Covariance conditioning is not a theorem about QAOA trainability.']}
    (out/'assessment.json').write_text(json.dumps(result,indent=2,allow_nan=False))
    lines=['# US Equity Dataset: Measured Development Diagnostics','','Status: **candidate; financial evaluation blocked**.','',
        'This report describes raw provider series. Security lineage and total-return treatment remain unverified.',
        'The statistics below use 2014–2018 only. Later years are checked for coverage, not used for strategy design.','',
        f"Requested stocks: {result['requested_asset_count']}. Downloaded stocks: {result['downloaded_assets']}. Benchmark: DIA.",
        f"Missing requested ticker: {', '.join(result['missing_tickers'])}. Verified security identities: {result['asset_identity_verified_count']}.",
        f"Development complete observations: {len(complete)}. Context evidence records: {result['historical_context_records']}.",'',
        '| Diagnostic | Value |','|---|---:|',
        f"| Pair correlation quartiles [min,Q1,median,Q3,max] | {result['pairwise_correlation_quantiles']} |",
        f"| Covariance participation ratio | {result['effective_rank_trace_squared']:.3f} |",
        f"| Sample covariance condition | {result['sample_covariance_condition_number']:.3f} |",
        f"| Ledoit–Wolf covariance condition | {result['ledoit_wolf_condition_number']:.3f} |",
        f"| Ledoit–Wolf shrinkage | {result['ledoit_wolf_shrinkage']:.6f} |",
        f"| Nonzero pair fraction at 1e-12 | {result['nonzero_pair_interaction_fraction_at_1e_minus_12']:.3f} |",'',
        '## Coverage and identity warnings','','| Inception ticker | Downloaded | Provider name now | Dates | Rows | >20% moves (development only) |','|---|---|---|---|---:|---:|']
    for row in rows:
        lines.append(f"| {row['ticker']} | {row['available']} | {row.get('provider_name','missing')} | {row.get('first_date','')} / {row.get('last_date','')} | {row.get('observations',0)} | {row.get('absolute_daily_moves_above_20pct','')} |")
    lines+=['','## Interpretation and actions','',
        '- UTX is missing. Replacing it with a current ticker or deleting it would change the historical universe.',
        '- DD and GE resolve to present-day provider names. Their historical entity/action lineage needs source-level reconstruction.',
        '- Shared return structure motivates testing covariance shrinkage and correlation descriptors; it does not select a mixer.',
        '- Dense quadratic interactions motivate direct RZ/RZZ resource accounting. No cost coefficient may be deleted by the LLM.',
        '- Compare profile-informed designs against rules and adaptive classical designs on identical problems.',
        '- Add point-in-time positions, mandates and evidence records to study decisions; OHLCV alone is not rich financial context.',
        '- No final universe, sector labels, corporate-action correctness, or investment claims are approved by this report.','',
        'Machine-readable evidence and formulas: [assessment.json](assessment.json).',
        'Reproduce: `.venv/bin/python scripts/assess_us_dataset.py`. Raw provider files stay local; publish checksums only.']
    (out/'ASSESSMENT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:result[k] for k in ('downloaded_assets','missing_tickers','development_complete_observations','effective_rank_trace_squared','pairwise_correlation_quantiles','nonzero_pair_interaction_fraction_at_1e_minus_12')},indent=2))

if __name__=='__main__':main()
