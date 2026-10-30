"""Record this contract task's read evidence and observed local import closure."""
raise SystemExit('Historical direction/provenance generator retired; it does not define or validate runtime work.')
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
GOAL = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
def describe(path, extent):
    p = Path(path) if str(path).startswith('/') else ROOT / path
    raw = p.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'byte_count': len(raw), 'inspection': extent}
def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')

full = ['AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md',
    'docs/TASK_AND_STEERING.md','docs/TOOL_GRADER_GOAL_AND_PRINCIPLES_2026-10-24_001.md']
modules = ['mauve_v4_formats','mauve_v4_format_contracts','mauve_v4_calculators','mauve_v4_calculation_contracts',
    'mauve_backbone_formats','mauve_backbone_contracts','mauve_backbone_calculators',
    'bvbrc_genome_alignment_input_contracts','xmfa_formats','xmfa_format_contracts','xmfa_sources',
    'xmfa_source_contracts','xmfa_coordinates','xmfa_calculators','xmfa_calculation_contracts',
    'bvbrc_alignment_values','bvbrc_appservice_contracts','phylogeny_format_contracts','phylogeny_calculation_contracts',
    'bvbrc_msa_bundle_adapter','bvbrc_appservice_adapters','bvbrc_appservice_publication',
    'bvbrc_alignment_returns','episode_return_records','blast_pairwise_grader']
full += ['gene_annotation_episode/' + m + '.py' for m in modules]
old = 'verification/tool_graders_bvbrc_genome_alignment_boundaries_2026-10-25/'
full += [old + n for n in ['BOUNDARY_PROPOSAL_001.md','INTERFACES_002.md','IMPLEMENTATION_OWNERSHIP_003.md',
    'INPUT_RELATIONSHIPS_004.md','HASH_CORRECTION_005.md']]
rows = [describe(GOAL, 'full immutable user goal read; PURPOSE and all16 principles reread verbatim after substantive examinations')]
rows += [describe(p, 'complete source/record read') for p in full]
partial = {
    'research/tool_grader_inventory_2026-10-24/WORK_STATUS.json': 'fixed GenomeAlignment row and its unchanged pending/resource status',
    'gene_annotation_episode/bvbrc_appservice_schemas.json': 'complete referenced ArtifactBundle, ArtifactMember, OriginalTask, TaskAssociation, Transfer, ContentBinding, SourceEvidence, AcquisitionRequirement, Diagnostic, OutputRequirement, ResultSelector definitions',
    'gene_annotation_episode/bvbrc_alignment_bundle_resolution.py': 'lines1-699 and789-911; excluded unrelated cross-family calculation implementation',
    'gene_annotation_episode/bvbrc_alignment_bundle_contracts.py': 'parameter/selection sections1-320 and actual requested-form/fact schema sections1010-1178',
    'gene_annotation_episode/bvbrc_alignment_bundle_projection.py': 'lines1-160, saved projection identity/copy pattern; not full unrelated MSA/MetaCATS arithmetic family implementation',
    'gene_annotation_episode/blast_database_grader.py': 'build_database_sheet and calculate_database_probabilities, lines732-1007; separation design only, formula not reused',
    'gene_annotation_episode/api_service_execution.py': 'constructor and own/received reference dispatch integration paths',
    'gene_annotation_episode/bvbrc_appservice_host.py': 'facts and results/completion consumer paths',
    'gene_annotation_episode/execution_episodes.py': 'tool/fact source discovery and received_report_facts/resolve_received_reference/validate_received_report/_appservice_sources/received_form_references/resolve consumers',
    'verification/tool_graders_bvbrc_genome_alignment_extraction_boundaries_2026-10-25/EXTRACTION_CONTRACT_001.md': 'retained-record extension section3 fully; native extraction/output maps/missing cases sections4-7 and displayed provenance/scope conclusions',
    'verification/tool_graders_mauve_v4_2026-10-25/README_001.md': 'A handoff read; exact implementation additionally read in full',
    'verification/tool_graders_mauve_v4_2026-10-25/VERIFICATION_001.json': 'native examples/source hashes and stated verification evidence; not rerun as own test suite',
    'verification/tool_graders_mauve_sidecars_2026-10-25/HANDOFF_001.md': 'B handoff read; exact implementation additionally read in full',
    'verification/tool_graders_mauve_sidecars_2026-10-25/OWNED_SOURCE_HASHES_001.json': 'complete hash records checked against current owned production files',
    'verification/tool_graders_mauve_sidecars_2026-10-25/FILLED_EXAMPLES_001.json': 'loaded complete JSON; exact native selections/fields and synthetic witness distinctions inspected; replayed chosen values',
    'verification/tool_graders_mauve_v4_2026-10-25/official_small.document.json': 'loaded complete native saved document; exercised existing public calculator',
    'verification/tool_graders_mauve_v4_2026-10-25/official_small.components.json': 'loaded complete saved components; exact replay equality and inspected numeric rows',
    'verification/tool_graders_bvbrc_xmfa_sources_2026-10-25/saved_examples/separate_native-inputs.json': 'loaded complete existing neutral source fixture; explicit synthetic invocation/source wrappers, not a C-produced same-run witness',
    'verification/tool_graders_bvbrc_xmfa_calculators_2026-10-25/filled_examples/separate.xmfa.operands.json': 'top-level shape/identity inspection only; final probe uses source fixture above',
}
rows += [describe(p, extent) for p, extent in partial.items()]
native = [old+'retained_sources/mauve/testdata/small.mauve']
native += ['verification/tool_graders_mauve_sidecars_2026-10-25/native_examples/'+n
    for n in ['separate.xmfa','separate.xmfa.backbone','separate.xmfa.bbcols']]
rows += [describe(p, 'complete retained actual native text bytes inspected; original BV-BRC task custody not established') for p in native]
for p in sorted((ROOT / old).glob('ACQUISITION_RECEIPTS_*.json')):
    rows.append(describe(str(p.relative_to(ROOT)), 'historical retained acquisition evidence referenced; no new acquisition in this task'))
for name in ['SOURCE_AND_CONSUMER_HASHES_001.json']:
    p=ROOT/old/name
    if p.exists(): rows.append(describe(str(p.relative_to(ROOT)), 'historical upstream source/consumer hash evidence; not a claim every upstream source was reread here'))
assert rows[0]['sha256']=='11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
by_path={r['path']:r for r in rows}
assert by_path[old+'INTERFACES_002.md']['sha256']=='53bd448f23b42c4c661fb0d15d5aca14deede3dd7e544265dc3fe5d0d0d0c3ca'
prior_a=json.loads((ROOT/'verification/tool_graders_mauve_v4_2026-10-25/VERIFICATION_001.json').read_text())['owned_source_hashes']
prior_b=json.loads((ROOT/'verification/tool_graders_mauve_sidecars_2026-10-25/OWNED_SOURCE_HASHES_001.json').read_text())
matches=[]
for row in prior_a+prior_b:
    if row['path'].startswith('gene_annotation_episode/'):
        actual=by_path[row['path']]['sha256']; assert actual==row['sha256']
        matches.append({'path':row['path'],'sha256':actual,'matches_prior_handoff':True})
stamp=datetime.now(timezone.utc).isoformat()
write('SOURCE_HASHES_001.json',{'recorded_utc':stamp,'scope':'read evidence, not implementation completion',
    'authority_and_frozen002_direct_hash_checks':'passed','A_B_current_production_vs_handoff':matches,'files':rows})

seeds=modules[:19]
seen=set();pending=seeds[:];edges={}
while pending:
    name=pending.pop()
    if name in seen:continue
    path=ROOT/'gene_annotation_episode'/(name+'.py')
    if not path.exists():continue
    seen.add(name); children=[]
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node,ast.ImportFrom) and node.level==1:
            children.extend([node.module.split('.')[0]] if node.module else [a.name for a in node.names])
    children=sorted(set(c for c in children if (ROOT/'gene_annotation_episode'/(c+'.py')).exists()))
    edges[name+'.py']=[c+'.py' for c in children];pending.extend(children)
existing=sorted(n+'.py' for n in seen)+['bvbrc_appservice_schemas.json']
new=['bvbrc_genome_alignment_calculation_contracts.py','bvbrc_genome_alignment_sheet.py',
    'bvbrc_genome_alignment_calculators.py','bvbrc_genome_alignment_bundle_contracts.py',
    'bvbrc_genome_alignment_bundle_resolution.py','bvbrc_genome_alignment_bundle_projection.py',
    'bvbrc_genome_alignment_bundle_adapter.py','bvbrc_genome_alignment_inputs.py','bvbrc_genome_alignment_associations.py']
write('PIN_DEPENDENCIES_001.json',{'recorded_utc':stamp,'implementation_pin':None,
    'status':'observed existing neutral/shared closure plus exact planned C/D/E roots; final closure awaits actual C/D/E imports',
    'required_existing_files':existing,'observed_local_import_edges':edges,'required_new_files':sorted(new),
    'non_module_resource_edges':{'bvbrc_appservice_contracts.py':['bvbrc_appservice_schemas.json']},
    'algorithm':"sha256 concatenation of sorted filename UTF8 + NUL + decimal byte_count ASCII + NUL + exact content bytes",
    'must_audit_when_implemented':'actual local transitive imports, lazy imports and file-loaded data; include every dependency actually reached by consume/validation/projection, and no unrelated whole-provider lists',
    'excluded_unless_actual_dependency':['bvbrc_alignment_bundle_*','bvbrc_msa_*','bvbrc_metacats_*','blast_*','phylogeny_calculators.py','phylogeny_formats.py','bvbrc_genome_alignment_returns.py','host/execution/tool-library modules'],
    'external_runtime':'Python stdlib and installed jsonschema; jsonschema bundled vocabularies initialized before no-I/O grading probe; no package installation performed'})

outputs=[describe(str(p.relative_to(ROOT)), 'produced in owned verification directory') for p in sorted(OUT.iterdir())
    if p.is_file() and p.name!='VERIFICATION_001.json']
write('VERIFICATION_001.json',{'recorded_utc':stamp,'task':'D/E/F exact contract planning only',
    'commands':[{'command':'PYTHONPATH=. python3 '+str((OUT/'offline_probe_001.py').relative_to(ROOT)), 'final_exit_code':0,
        'result_file':'OFFLINE_EXAMPLES_001.json','checks':['exact A/B saved reproduction','changed k2/k3 neutral calculations',
        'explicit XMFA alignment/coverage/coordinate/inverse calculations','no I/O or native parsers during recalculation',
        'no scientific functions/source comparison during saved neutral validation']}],
    'earlier_probe_setup_failures':['jsonschema lazily loaded bundled vocabularies under I/O barrier; fixed configuration warmup',
        'B synthetic C input xmfa_source_inputs is null; used existing neutral XMFA source fixture, did not invent C projection'],
    'pytest_executed_by_this_task':False,'parent_reported_existing_A_B_C_tests':289,
    'production_files_edited':[],'service_calls':0,'jobs_submitted':0,'installs':0,
    'D_E_F_implemented':False,'live_execution_verified':False,'episode_integration_verified':False,
    'native_bytes_vs_synthetic_evidence':'actual retained upstream native examples; synthetic source/task/interval witness wrappers explicitly labeled',
    'artifacts':outputs})
print(json.dumps({'authority_hash':rows[0]['sha256'],'frozen002_hash':by_path[old+'INTERFACES_002.md']['sha256'],
    'prior_A_B_hashes_match':len(matches),'observed_pin_existing_files':len(existing),'source_records':len(rows),
    'artifacts':len(outputs)},indent=2))
