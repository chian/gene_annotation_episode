"""Build future launch operands using sealed preparation metadata only."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent;CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007')
PREP=Path('/tmp/configured-literature-localization-invocation-20261022-001-nuzn9c6c')
RUN=Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001')
def d(p):
 b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(n,x):
 b=x if isinstance(x,bytes) else (json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 with (P/n).open('xb') as f:f.write(b)
prepared=json.loads((PREP/'outputs/PREPARATION_RESULT001.json').read_text())
assert d(PREP/'outputs/PREPARATION_RESULT001.json')['sha256']=='8551d082f9a28e4004d6d7b11237f57bddd5c9c43a7720aa9813f13f29a0b245'
assert prepared['parameters']['sha256']=='5ab22e01f87cec425adaa7dcde1ffbaa5df776a8a0070a77e6c746870af74d73'
members={}
for n in ['PREPARATION_RESULT001.json','C_RESULT001.json','parameters.json','config.toml','focus.txt','case-launch.json','scientific-checkpoint-fork.json']:
 source=PREP/'outputs'/n;save('prepared-'+n,source.read_bytes())
 target=(RUN/n if n=='case-launch.json' else RUN/'workspace'/n if n=='scientific-checkpoint-fork.json' else RUN/'caller-inputs'/n)
 desc=d(source);desc['path']=str(target);members[n]=desc
argv=['/home/chia/repos/gene_annotation_episode/.venv/bin/python','-m','gene_annotation_episode.case_execution','run','--run-dir',str(RUN),'--policy',str(CODE/'gene_annotation_episode/api_planning_case_policy.py'),'--parameters',str(RUN/'caller-inputs/parameters.json')]
command={'version':'configured_literature_localization_launch_command_v1','status':'unadopted_not_executed',
 'argv':argv,'cwd':str(CODE),'environment_overrides':{'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(CODE)},
 'runtime_pin':'3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842','runtime_files':137,
 'policy_source_sha256':'4474422fa09ac5247b1957e7d1bce4a57ac811f39f1cc9356666a7c4d4ea276f',
 'inputs':members,'working_database_before_launch':prepared['working_database_after_prepare'],
 'native_registry_ref':prepared['native_registry_ref'],'public_search_registry_ref':prepared['public_search_registry_ref'],
 'launch_evidence_directory':'/tmp/configured-literature-localization-launch-20261022-001',
 'resume':False,'timeout':None,'retry':False,'cancellation':False,
 'preparation_manifest':d(PREP/'MANIFEST_FINAL002.json'),'prepared_result_descriptor':d(PREP/'outputs/PREPARATION_RESULT001.json')}
save('LAUNCH_COMMAND_DRAFT001.json',command)
print(json.dumps({'directory':str(P),'launch_command':d(P/'LAUNCH_COMMAND_DRAFT001.json')},sort_keys=True))
