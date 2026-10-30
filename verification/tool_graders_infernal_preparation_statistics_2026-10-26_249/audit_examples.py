"""Independent Decimal arithmetic over retained sheets; no production calculator."""
from decimal import Decimal, localcontext
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(directory):
    source = BASE / 'examples003'
    checks = []
    def load(name):
        return json.loads((source/(name+'.json')).read_text())
    def matching(document, native):
        return next(r['components'] for r in document['calculations']['rows'] if r['record_key'] == native['record_key'])
    def known(name, expected, actual, native=None):
        expected = Decimal(expected)
        delta = abs(expected-Decimal(str(actual)))
        assert delta < Decimal('1e-10'), (name, str(expected), actual)
        checks.append(dict(name=name, independent_decimal=str(expected), actual=actual,
                           absolute_difference=str(delta), native=native))
    with localcontext() as ctx:
        ctx.prec = 60
        doc = load('cmbuild_default')
        build=next(r for r in doc['sheet']['native_rows'] if r['kind']=='build')
        known('paired_consensus_fraction', Decimal(8)/12, matching(doc,build)['paired_consensus_fraction']['value'])
        doc = load('cmcalibrate_all_sidecars')
        row = next(r for r in doc['sheet']['native_rows'] if r['kind']=='calibration' and r['identity']['source']=='model_header' and r['identity']['algorithm']=='cm_local_cyk')
        mu = Decimal('-2.53576')+Decimal('.1').ln()/Decimal('.44855')
        known('LC_mu_extrap', mu, matching(doc,row)['mu_extrap_calculated']['value'], '-7.66916')
        known('LC_mu_extrap_residual', mu-Decimal('-7.66916'), matching(doc,row)['mu_extrap_residual']['value'])
        assert sum(len(r.get('series',[])) for r in doc['sheet']['native_rows']) == 12325
        fit_rows = [r for r in doc['sheet']['native_rows'] if r['kind']=='calibration_series' and r['identity']['series_kind']=='fit_grid']
        assert len(fit_rows) == 164
        checks.append(dict(name='sidecar_full_population', series_points=12325, tail_fit_rows=164))
        for case in ('cmstat_E','cmstat_P','cmstat_T'):
            doc=load(case)
            model=doc['sheet']['input_records'][0]
            for row in doc['sheet']['native_rows']:
                fit=next(f for f in model['calibration'].values() if f and f['algorithm']==row['identity']['algorithm'])
                lam=Decimal(fit['lambda']['native_token'])
                loc=Decimal(fit['mu_extrap']['native_token'])
                count=Decimal(10000000)/Decimal(fit['calibration_dbsize_nt']['native_token'])*Decimal(fit['random_hit_count']['native_token'])
                if case=='cmstat_E':
                    expected=loc-(Decimal('.01')/count).ln()/lam
                    component='score_at_evalue'
                    native=row['values']['threshold_bits']['value']
                elif case=='cmstat_P':
                    expected=loc-Decimal('.01').ln()/lam
                    component='score_at_pvalue'
                    native=row['values']['threshold_bits']['value']
                else:
                    expected=count*(-lam*(Decimal(10)-loc)).exp()
                    component='evalue_at_score'
                    native=row['values']['evalue']['value']
                known(case+'_'+row['identity']['algorithm'], expected, matching(doc,row)[component]['value'], native)
        doc=load('cmstat_hmm_P')
        model=doc['sheet']['input_records'][0]
        for row in doc['sheet']['native_rows']:
            algorithm=row['identity']['algorithm']
            if algorithm=='hmm_glocal_viterbi':
                assert matching(doc,row)['score_at_pvalue']['state']=='incompatible'
                continue
            if algorithm=='hmm_glocal_forward':
                fit=model['efp7gf']
            else:
                tag='FORWARD' if algorithm=='hmm_local_forward' else 'VITERBI'
                fit=next(s for s in model['filter_hmm']['stats'] if s['mode']=='LOCAL' and s['algorithm']==tag)
            expected=Decimal(fit['location']['native_token'])-Decimal('.01').ln()/Decimal(fit['scale']['native_token'])
            known('cmstat_P_'+algorithm, expected, matching(doc,row)['score_at_pvalue']['value'], row['values']['threshold_bits']['value'])
        doc=load('cmcalibrate_memreq_without_cpu_env')
        for row in doc['sheet']['native_rows']:
            expected=Decimal(row['values']['predicted_mb']['native_token'])*1000000
            known('predicted_bytes_'+str(row['values']['cpu_count']['value']), expected, matching(doc,row)['predicted_bytes']['value'])
        doc=load('cmcalibrate_merge')
        totals={}
        for row in doc['sheet']['native_rows']:
            if row['kind']=='partition':
                count=len(row['series'])
                assert count==row['values']['score_count']['value']
                totals[row['identity']['algorithm']]=totals.get(row['identity']['algorithm'],0)+count
                components=matching(doc,row)
                assert components['total_calibration_chunk_count']['value']==2
                assert components['partition_chunk_count']['value']==1
                assert components['actual_calibration_nt']['value']==10000
        assert totals==dict(cm_glocal_cyk=6330,cm_glocal_inside=6207,cm_local_cyk=8366,cm_local_inside=7127)
        for row in doc['sheet']['native_rows']:
            if row['kind']=='calibration' and row['identity']['source']=='model_header':
                assert row['values']['random_hit_count']['value']==totals[row['identity']['algorithm']]
        checks.append(dict(name='merged_complete_score_population', totals=totals, count=sum(totals.values())))
        for tag in ('NC','TC'):
            doc=load('cmstat_'+tag+'_present')
            assert doc['sheet']['input_records'][0]['fields'][tag]['value']==10
            assert all(r['values']['threshold_bits']['value']==0 for r in doc['sheet']['native_rows'])
            assert any(i['code']=='infernal_statistics_calculation_native_mismatch' for i in doc['calculations']['issues'])
            checks.append(dict(name=tag+'_native_edge_preserved', header_threshold=10, native_threshold=0, mismatch_retained=True))
    (directory/'answers.json').write_text(json.dumps(dict(decimal_precision=60, checks=checks),indent=2)+'\n')
    print(str(len(checks))+' independent numerical/population checks passed')


if __name__=='__main__':
    if sys.argv[1]=='--worker':
        worker(Path(sys.argv[2]))
    else:
        directory=BASE/sys.argv[1]
        directory.mkdir(exist_ok=False)
        command=[str(ROOT/'.venv/bin/python'),str(Path(__file__).resolve()),'--worker',str(directory)]
        inputs={str(p.relative_to(BASE)):digest(p) for p in sorted((BASE/'examples003').glob('*.json'))}
        result=run_local_job(command,cwd=directory,policy=LocalJobPolicy(20*1024**3,4*1024**3,None),
            stdout_path=directory/'stdout.txt',stderr_path=directory/'stderr.txt',
            env={'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(directory)})
        (directory/'receipt.json').write_text(json.dumps(dict(command=command,returncode=result.returncode,metadata=result.metadata,
            audit_source_sha256=digest(Path(__file__)),input_sha256=inputs),indent=2)+'\n')
        print((directory/'stdout.txt').read_text())
        print((directory/'stderr.txt').read_text())
        sys.exit(result.returncode)
