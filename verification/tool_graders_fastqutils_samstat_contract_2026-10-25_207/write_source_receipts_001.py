"""Record retained source/build/native evidence; no grader implementation."""
from pathlib import Path
import subprocess,json,hashlib,datetime
W=Path(__file__).resolve().parent;R=W.parents[1];D=W/'native_examples_001'
def cmd(args,cwd=None):return subprocess.check_output(args,cwd=cwd,text=True).strip()
def blob(p,base=W):
 b=p.read_bytes();return dict(path=str(p.relative_to(base)) if p.is_relative_to(base) else str(p),byte_count=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
repos=[];files=[]
for name,version in [('samstat','2.5.0'),('samstat_2_2_3','2.2.3')]:
 p=W/'sources'/name
 repo=dict(path=str(p.relative_to(W)),official_url='https://github.com/TimoLassmann/samstat',acquisition='git clone --recursive; legacy detached worktree from retained official history',commit=cmd(['git','rev-parse','HEAD'],p),commit_time=cmd(['git','show','-s','--format=%cI','HEAD'],p),source_version=version,tracked_status=cmd(['git','status','--short'],p),submodules=cmd(['git','submodule','status','--recursive'],p),deployment_version_inference=False)
 for rel in cmd(['git','ls-files','--recurse-submodules'],p).splitlines():
  q=p/rel
  if q.is_file():files.append(blob(q))
 exe=W/f'sources/build_{version.replace(".","_")}/src/samstat'
 repo['executable']=blob(exe);repo['version_stdout']=blob(D/f'{version.replace(".","_")}_version.stdout');repo['version_text']=(D/f'{version.replace(".","_")}_version.stdout').read_text().strip()
 repos.append(repo)
write(W/'sources/SOURCE_FILE_HASHES_001.json',files)
native=[]
for p in sorted(D.rglob('*')):
 if p.is_file() and not p.name.startswith('FILE_HASHES_'):native.append(blob(p))
write(D/'FILE_HASHES_002.json',native)
callerroot=R/'verification/tool_graders_bvbrc_fastqutils_contract_2026-10-25_193'
caller_files=[callerroot/'sources/p3_fqutils'/p for p in ['lib/fastq_utils.py','Makefile','requirements.txt','README.md']]
candidate=R/'verification/tool_graders_bvbrc_fastqutils_remaining_formats_2026-10-25_204/candidate/gene_annotation_episode'
consumer_names=['bvbrc_fastqutils_native.py','bvbrc_fastqutils_contracts.py','bvbrc_fastqutils_mapping.py','bvbrc_fastqutils_calculators.py','bvbrc_fastqutils_sheet.py','bvbrc_fastqutils_bundle_adapter.py','bvbrc_fastqutils_resolution.py','bvbrc_fastqutils_projection.py','bvbrc_fastqutils_returns.py','bvbrc_fastqutils_metadata.py','bvbrc_fastqutils_saved_codec.py','bvbrc_fastqutils_identity.py','bvbrc_fastqutils_schemas.json']
builds=[]
for p in sorted((W/'sources').glob('*.json')):
 if p.name=='SOURCE_FILE_HASHES_001.json':continue
 builds.append(dict(receipt=blob(p),observed=json.loads(p.read_text())))
runsets=[json.loads(p.read_text()) for p in sorted(D.glob('RUN_RECEIPTS_*.json'))]
flat=[r for seq in runsets for r in seq];processes=[r for r in flat if 'exit_code' in r]
package_rows=[]
for p in sorted((W/'sources/deps/debs').glob('*.deb')):
 package_rows.append(dict(**blob(p),package_fields=cmd(['dpkg-deb','--field',str(p),'Package','Version','Architecture'])))
cmake_meta=next((W/'sources/build_tools').glob('cmake-*.dist-info/METADATA'))
receipt=dict(receipt_version='samstat_source_receipts_001',recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='SAMstat format contract for existing FastqUtils grader; no production/candidate edits',sources=repos,source_file_manifest=blob(W/'sources/SOURCE_FILE_HASHES_001.json'),caller=dict(source_commit_or_tree_from_193_receipt='efb17b5c23448eb6e2c81b90fbefcd5a2898ac86',upstream='https://github.com/BV-BRC/p3_fqutils',inherited_source_receipt=blob(callerroot/'SOURCE_RECEIPTS_001.json'),read_files=[blob(p) for p in caller_files],read_scope='Complete run_alignment; complete Makefile, requirements, README; searched retained caller tree for samstat constraints',invocation=['samstat','<prefix>.all.bam'],all_bam_deleted_after_report=True,retained_aligned_bam_filter='samtools view -b -F4',version_pin_found=False,external_deployment_make_rules_not_available=True,deployed_version=None),consumer_inspection=dict(candidate='204',files=[blob(candidate/n) for n in consumer_names],schema_scope='Complete relevant NativeDocument/Cell/Population/section/label/raw-block/context/artifact/calculation/component/selector definitions; schema file is hashed in full',scope_limit='No candidate parser/calculator executed; metric-spec catalog not claimed read in full',later_208_status='Parent reported closed requested-form generation, 27 dependencies and 359 unit cases; not rerun by this workload; root owns shared compatibility changes'),builds=builds,dependencies=dict(global_installation=False,cmake_local_target='sources/build_tools',cmake_distribution_metadata=blob(cmake_meta),cmake_version=cmd([str(W/'sources/build_tools/cmake/data/bin/cmake'),'--version']).splitlines()[0],local_apt_debs=package_rows,apt_acquisition='apt-get download to workload, dpkg-deb -x to sources/deps/root; no installation',apt_download_urls_recorded=False,autoconf_relocation='Separate local autom4te config and environment overrides in build attempt receipts; pinned SAMstat/tld tracked scientific sources remain unchanged',samstat_build_parallelism=2,converter=blob(W/'sources/build_2_5_0/htslib/src/htslib/test/test_view')),native_execution=dict(identity='source_executed_synthetic',biological_samples=False,run_receipts=[blob(p) for p in sorted(D.glob('RUN_RECEIPTS_*.json'))],run_receipt_process_count=len(processes),samstat_input_invocation_count=sum('samstat' in Path(r['command'][0]).name and any(str(a).endswith(('.sam','.bam','.fastq')) for a in r['command'][1:]) for r in processes),native_html_count=len(list(D.rglob('*.samstat.html')))-1,caller_failure_injection='Extracted exact caller except block via AST; /bin/false causes code1; not a native segfault or live-service run',native_file_manifest=blob(D/'FILE_HASHES_002.json'),audit=blob(D/'NATIVE_EVIDENCE_CHECKS_003.json'),native_JS_executed=False,optional_json='One explicit local --json comparison run; not caller artifact and not substituted for HTML values'),resource_observations=dict(address_space_limit_bytes=20*1024**3,core_limit_bytes=0,limit_scope='Native harness and build process limits where invoked; no aggregate profiler claimed',build_max_reported_rss_kib=max([v['observed'].get('max_rss_kib',0) for v in builds]),native_harness_max_child_rss_kib=max(r.get('max_child_rss_kib',0) for r in processes),rss_qualification='resource.getrusage(RUSAGE_CHILDREN).ru_maxrss is cumulative maximum in each harness, not independent per-invocation RSS',retained_scratch_apparent_bytes=int(cmd(['du','-sb',str(W)]).split()[0]),scratch_limit_bytes=4*1024**3,no_wall_time_cap=True,aurora_used=False),status=dict(source_present=True,prerequisites_local=True,native_versions_executed=['2.2.3','2.5.0'],native_format_observed=True,parser_implemented=False,parser_tested=False,calculator_implemented=False,calculator_tested=False,live_bvbrc_execution=False,integrated_episode_path_verified=False,deployed_bvbrc_version='unknown'),corrections=['CONTRACT_CORRECTIONS_002.md','NATIVE_FIELDS_002.json','PARSER_CALCULATOR_PORTS_002.md'])
write(W/'SOURCE_RECEIPTS_001.json',receipt)
print(json.dumps({'sources':len(repos),'source_files':len(files),'native_files':len(native),'process_receipts':len(processes),'samstat_input_invocations':receipt['native_execution']['samstat_input_invocation_count'],'native_html':receipt['native_execution']['native_html_count'],'scratch_bytes':receipt['resource_observations']['retained_scratch_apparent_bytes']}))
