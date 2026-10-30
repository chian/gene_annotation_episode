"""Build proposed ordinary caller inputs using sealed public data only."""
from pathlib import Path
import hashlib,json,uuid,tomllib
P=Path(__file__).resolve().parent
ROOT=Path('/home/chia/repos/gene_annotation_episode');CODE=Path('/tmp/gene-annotation-configured-caller-20261022-007')
CAP=ROOT/'verification/progress_checkpoint_2026-10-22_015'; RUN=Path('/home/chia/gene_annotation_episode_runs/configured_literature_localization_001')
def save(n,b):
 if not isinstance(b,bytes):b=(json.dumps(b,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
 with (P/n).open('xb') as f:f.write(b)
def desc(p):
 b=p.read_bytes();return {'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
selection=json.loads((CAP/'actual-caller-inputs/C_SELECTION001.json').read_text())['arguments']
selection['destination_workspace']=str(RUN/'workspace');assert len(selection['initial_known_record_refs'])==198
save('C_REQUEST001.json',selection)
config=(CAP/'actual-caller-inputs/config.toml').read_text();config='\n'.join(config.splitlines()[1:])+'\n'
config=config.replace('/home/chia/gene_annotation_episode_runs/configured_api_prechoice_001',str(RUN))
save('config.toml',config.encode()); normalized=tomllib.loads(config)
original=tomllib.loads((CAP/'actual-caller-inputs/config.toml').read_text())
assert config and normalized['models']==original['models'] and normalized['local_jobs']==original['local_jobs']
focus='''This new isolated investigation concerns the fixed E. coli K-12 MG1655 YbhP/b0790 gene and its 253-aa P0AAW1 protein. Investigate what the original published evidence and its methods establish about the retained localization discrepancy: the workbook's STEPdb Cytoplasm assertion versus its sucrose-gradient IM classification. The retained row source source_8dbf6a14205689c8554e30c9 and its original workbook provenance identify the question; the labels are source assertions, not a supplied target-localization conclusion. Distinguish the actual subject, organism, experimental conditions, methods and source limitations. Preserve competing explanations and uncertainty when the sources do not discriminate; do not infer activity or physiological role from localization alone.

Carry out substantive iterative literature delegation through the existing literature episode interface, and use its admitted typed return in a later parent scientific decision when continuation permits. Define the actual child goal, contained scope, requested typed return and field meanings for the scientific distinction you need to integrate. The child owns its iterative choices, source work and any narrower literature investigations. Choose ordinary tools and further investigations from actual outcomes. This caller job requests episodic delegation and later integration for the demonstration; it installs no runtime action selector. No particular source, query, tool, nested sequence, child order, number of turns or scientific conclusion is prescribed. If the configured controller closes the parent before a usable return or later integration, preserve partial work and describe that limitation rather than forcing continuation.

All committed records and original native measurements supplied through the stopped-source custody receipt are inherited prior information, not new local actions or new credit. Reuse unchanged acquired evidence and measurements. The sealed later science001/002 proofs identify this demonstration question for the operator; their later new records are not silently added to this caller's inherited input list. Reference proteins, neighboring genes and studies remain evidence about this one fixed target.

The unchanged frozen scientific process publication is A0/P19: scientific_process is declared but lacks an adopted support entry for valid scoped scientific construction. Do not invent or adopt a support entry, scoring route or tool bundle. Literature remains its separate existing hierarchy. Preserve the configured scientific, annotation-support, monitoring and duration channels and all units. The existing scalar continuation estimator does not numerically use supplied pending-work context; this caller selects no new numerical model. Its unchanged configured controller owns continuation. Actual waits and child returns retain their own original observations; passing time alone earns zero. A yielded parent does not cancel descendants and is not scientific completion.
'''
save('focus.txt',focus.encode())
parameters=json.loads((CAP/'actual-caller-inputs/parameters.json').read_text())
del parameters['policy']['scientific_progress']['initial_known_record_refs'];del parameters['policy']['operational']['registry_ref']
services=parameters['services'];services['source_directory']=str(CODE/'research/slotted_process_library/publications/2026-10-21-001')
services['api_timing']['history_path']=str(RUN/'statistics/run_statistics.sqlite');services['api_timing']['ledger_path']=str(RUN/'statistics/api-timing.sqlite')
services['public_search_registry']['registry_ref']='execution_registry_9d451c293fb649cea87d48ab2f5ea4d2'
save('PARAMETER_TEMPLATE001.json',parameters)
receipt=json.loads((CAP/'actual-custody-receipt.json').read_text())
expected={k:receipt[k] for k in ['fixed_identity','preserved_counts']}
expected.update({'source_counts':receipt['source']['counts'],'checkpoint_descriptors':receipt['checkpoint'],
 'source_implementation_manifest':receipt['source']['implementation_file_manifest'],
 'source_authorities':receipt['source']['authority_files'],
 'source_database':receipt['source']['preservation']['database_before'],
 'source_native_database':receipt['source']['execution_inventory']['native_registry_database'],
 'original_native_receipts':json.loads((CAP/'actual-caller-inputs/INITIAL_BASELINE_SNAPSHOT001.json').read_text())['inherited_native_receipts'],
 'static_policy_remainder_sha256':'dc23b2c87d7d4466f217c2752d1ad1f1bedf86e50fe02ea0a416b60c0d345ac1',
 'retained_active_native_registry_ref':json.loads((CAP/'actual-caller-inputs/parameters.json').read_text())['policy']['operational']['registry_ref'],
 'retained_active_public_registry_ref':json.loads((CAP/'actual-caller-inputs/parameters.json').read_text())['services']['public_search_registry']['registry_ref'],
 'deferred_parameter_paths':['policy.scientific_progress.initial_known_record_refs','policy.operational.registry_ref']})
save('EXPECTED_HANDOFF001.json',expected)
schema=ROOT/'verification/scientific_checkpoint_custody_plan_2026-10-22_001/SCHEMAS004.json';assert desc(schema)['sha256']=='b000697eb19d68140f14f2e8f7d30c13b60653a6e443c0508c6ec1519b7d6112';save('SCHEMAS004.json',schema.read_bytes())
pub=Path(services['source_directory']);save('PUBLICATION_INPUTS001.json',{'root':str(pub),'members':{p.relative_to(pub).as_posix():desc(p) for p in sorted(pub.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}})
inputs=['C_REQUEST001.json','config.toml','focus.txt','PARAMETER_TEMPLATE001.json','EXPECTED_HANDOFF001.json','SCHEMAS004.json','PUBLICATION_INPUTS001.json']
save('INPUTS001.json',{'version':'configured_literature_caller_preparation_inputs_v1','status':'unadopted_not_executed',
 'implementation_root':str(CODE),'implementation_sha256':'3805ed95de6e84ac90e31fe89ee076218acbe53d5e111d4332f6d0d108d65842','runtime_file_count':137,
 'destination_run_directory':str(RUN),'case_directory':str(ROOT/'cases/gene_001'),
 'public_search_registry_ref':services['public_search_registry']['registry_ref'],
 'members':{n:desc(P/n) for n in inputs},
 'source_provenance':{n:desc(CAP/n) for n in ['actual-caller-inputs/C_SELECTION001.json','actual-caller-inputs/parameters.json','actual-caller-inputs/config.toml','actual-custody-receipt.json','actual-caller-inputs/INITIAL_BASELINE_SNAPSHOT001.json']}})
print(json.dumps({'directory':str(P),'input_manifest':desc(P/'INPUTS001.json'),'fresh_public_registry':services['public_search_registry']['registry_ref']},sort_keys=True))
