"""Retain populated native examples and separate calculations under local limits."""
from pathlib import Path
import hashlib
import json
import sys

from gene_annotation_episode.local_jobs import LocalJobPolicy, run_local_job

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]


def worker(directory):
    sys.path.insert(0,str(ROOT/'tests'))
    from test_infernal_preparation_statistics import native_stat, operation, populate, retained
    from test_infernal_preparation_calculations import calibration_sheet, merge_sheet
    from gene_annotation_episode.infernal_preparation_calculations import calculate_infernal_statistics
    index = []
    def save(name,sheet,parameters=None):
        calculations = calculate_infernal_statistics(sheet,parameters=parameters or {})
        document = dict(sheet=sheet,calculations=calculations)
        path = directory/(name+'.json')
        path.write_text(json.dumps(document,indent=2,allow_nan=False)+'\n')
        index.append(dict(name=name,path=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),size_bytes=path.stat().st_size,
            native_rows=len(sheet['native_rows']),input_records=len(sheet['input_records']),output_records=len(sheet['output_records']),
            series_points=sum(len(r.get('series',[])) for r in sheet['native_rows']),
            sheet_issue_codes=sorted(set(i['code'] for i in sheet['issues'])),
            calculation_issue_codes=sorted(set(i['code'] for i in calculations['issues']))))
    for name in ['cmbuild_default','cmbuild_hand','cmbuild_noss','cmbuild_refine']:
        refine = name=='cmbuild_refine'
        settings = {'--hand':True} if name.endswith('hand') else {'--noss':True} if name.endswith('noss') else {}
        inputs = {'alignment':[retained(name,'seed.sto','alignment','stockholm',new=refine)]}
        outputs = {'built_models':[retained(name,'built.cm','built_models','infernal_cm_ascii',new=refine)],
                   'stdout':[retained(name,'stdout.txt','stdout','infernal_stdout',new=refine)]}
        if refine:
            outputs['refined_alignment']=[retained(name,'refined.sto','refined_alignment','stockholm',new=True)]
            outputs['processed_alignment']=[retained(name,'processed.sto','processed_alignment','stockholm',new=True)]
        save(name,populate(operation('cmbuild','refine' if refine else 'build',**settings),inputs,outputs))
    inputs = {'models':[retained('cmcalibrate_tiny','original.cm','models','infernal_cm_ascii')]}
    outputs = {'calibrated_models':[retained('cmcalibrate_tiny','model.cm','calibrated_models','infernal_cm_ascii')],
               'stdout':[retained('cmcalibrate_tiny','stdout.txt','stdout','infernal_stdout')]}
    for kind, filename in [('hfile','hist.dat'),('sfile','survival.dat'),('qqfile','qq.dat'),('ffile','fits.dat'),('xfile','tail.dat')]:
        outputs[kind]=[retained('cmcalibrate_tiny',filename,kind,'infernal_calibration_'+kind)]
    save('cmcalibrate_all_sidecars',populate(operation('cmcalibrate','calibrate',**{'-L':.01,'--seed':181,'--tailp':.1}),inputs,outputs))
    for case,mode in [('cmcalibrate_forecast','forecast'),('cmcalibrate_memreq_without_cpu_env','memory_estimate'),
                      ('cmcalibrate_split','split_commands'),('cmcalibrate_partition_1','partition_scores')]:
        settings={'-L':.01 if mode in {'forecast','memory_estimate'} else .02}
        if mode in {'split_commands','partition_scores'}:
            settings['--ptot']=2
        if mode=='partition_scores':
            settings['--part']=1
        outputs={'stdout':[retained(case,'stdout.txt','stdout','infernal_stdout')]}
        if mode=='partition_scores':
            outputs['partition_scores']=[retained(case,'scores.dat','partition_scores','infernal_partition_scores')]
        if mode=='split_commands':
            outputs['commands']=[retained(case,'commands.txt','commands','infernal_commands')]
        sheet=populate(operation('cmcalibrate',mode,**settings),{'models':[retained(case,'model.cm','models','infernal_cm_ascii')]},outputs)
        save(case,sheet)
    sheet,requests=merge_sheet()
    save('cmcalibrate_merge',sheet,{'partition_requests':requests})
    for case,mode,settings in [('cmstat_summary','summary',{}),('cmstat_E','scores_at_evalue',{'-E':.01,'-Z':10}),
        ('cmstat_P','scores_at_pvalue',{'-P':.01}),('cmstat_T','evalues_at_score',{'-T':10,'-Z':10}),
        ('cmstat_GA','evalues_at_ga',{'-Z':10}),('cmstat_NC','evalues_at_nc',{'-Z':10}),('cmstat_TC','evalues_at_tc',{'-Z':10}),
        ('cmstat_hmm_E','scores_at_evalue',{'-E':.01,'-Z':10,'--hmmonly':True}),
        ('cmstat_hmm_T','evalues_at_score',{'-T':10,'-Z':10,'--hmmonly':True}),('cmstat_noss_summary','summary',{})]:
        save(case,native_stat(case,mode,**settings))
    save('cmstat_hmm_P',native_stat('cmstat_hmm_P','scores_at_pvalue',new=True,**{'-P':.01,'--hmmonly':True}))
    save('cmstat_key',native_stat('cmstat_key','scores_at_evalue',new=True,**{'-E':.01,'-Z':10,'--key':'SECOND249'}))
    for tag in ('GA','NC','TC'):
        save('cmstat_'+tag+'_present',native_stat('cmstat_'+tag+'_present','evalues_at_'+tag.lower(),new=True,**{'-Z':10}))
    (directory/'INDEX.json').write_text(json.dumps(index,indent=2)+'\n')
    print(json.dumps([dict(name=i['name'],native_rows=i['native_rows'],series_points=i['series_points'],
                          calculation_issue_codes=i['calculation_issue_codes']) for i in index],indent=2))


if __name__=='__main__':
    if sys.argv[1]=='--worker':
        worker(Path(sys.argv[2]))
    else:
        directory=BASE/sys.argv[1]
        directory.mkdir(parents=True,exist_ok=False)
        command=[str(ROOT/'.venv/bin/python'),str(Path(__file__).resolve()),'--worker',str(directory)]
        source_paths=['gene_annotation_episode/infernal_preparation_statistics.py','gene_annotation_episode/infernal_preparation_calculations.py',
                      'gene_annotation_episode/infernal_preparation_models.py','gene_annotation_episode/infernal_preparation_schema.py']
        before={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths}
        result=run_local_job(command,cwd=directory,policy=LocalJobPolicy(20*1024**3,4*1024**3,None),
            stdout_path=directory/'stdout.txt',stderr_path=directory/'stderr.txt',
            env={'PYTHONPATH':str(ROOT),'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(directory)})
        after={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in source_paths}
        (directory/'receipt.json').write_text(json.dumps(dict(command=command,returncode=result.returncode,metadata=result.metadata,
            source_sha256_before=before,source_sha256_after=after,source_stable=before==after),indent=2)+'\n')
        print((directory/'stdout.txt').read_text())
        print((directory/'stderr.txt').read_text())
        sys.exit(result.returncode)
