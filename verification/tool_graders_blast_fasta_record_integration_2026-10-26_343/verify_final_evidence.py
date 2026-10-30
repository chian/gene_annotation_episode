"""Audit retained343 outputs; no scientific calculator, parser or execution."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
PACKET = Path(__file__).resolve().parent
RUN = PACKET/'check015'
PRODUCTION = ['native_blast_standard_database_contracts.py', 'native_blast_standard_database_result_views.py',
    'native_blast_standard_database_result_worker.py', 'native_blast_standard_database_calculators.py',
    'native_blast_database_result_worker.py', 'native_blast_database_result_views.py', 'native_blast_database_result_publication.py']
TESTS = ['test_native_blast_standard_database_contracts.py', 'test_native_blast_standard_database_result_views.py',
    'test_native_blast_standard_database_result_worker.py', 'test_native_blast_standard_database_calculators.py',
    'test_native_blast_database_result_worker.py', 'test_native_blast_database_result_views.py', 'test_blast_fasta_record_identity_integration.py']


def read(path): return json.loads(path.read_bytes())
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def json_rows(path): return [json.loads(line) for line in path.read_bytes().splitlines()]
def cells(row): return {v['name']:v['value'] for v in row['measurements']}
def ident(path): return dict(path=str(path.relative_to(ROOT)), sha256=sha(path), size_bytes=path.stat().st_size)


def test_final_evidence():
    out = Path.cwd()
    for name, count in (('check012', 314), ('check013', 56), ('check015', 32)):
        assert read(PACKET/name/'receipt.json')['returncode'] == 0
        assert str(count) + ' passed' in (PACKET/name/'stdout.txt').read_text()
    before, after = read(RUN/'source_hashes_before.json'), read(RUN/'source_hashes_after.json')
    closure = {}
    for request_path in [*RUN.joinpath('temporary/pytest').rglob('fresh-reuse-request.json'),
            *RUN.joinpath('temporary/pytest').glob('test_retained339_exact_wire_re[0-9]/generation-1.request.json')]:
        for row in read(request_path)['implementation']['files']:
            if not row['module'].startswith('gene_annotation_episode'):
                continue
            key = str(Path(row['path']).relative_to(ROOT))
            assert key not in closure or closure[key] == row['sha256']
            closure[key] = row['sha256']
    assert closure
    changed_during_run = {k:dict(before=v, after=after[k]) for k,v in before.items() if v != after[k]}
    assert not set(closure) & set(changed_during_run)
    assert all(sha(ROOT/key) == digest for key,digest in closure.items())
    original_before, original_after = (read(PACKET/'check012'/name) for name in ('source_hashes_before.json','source_hashes_after.json'))
    original_changed = {k:dict(before=v, after=original_after[k]) for k,v in original_before.items() if v != original_after[k]}
    assert not set(closure) & set(original_changed)
    paths = [ROOT/'gene_annotation_episode'/name for name in PRODUCTION] + [ROOT/'tests'/name for name in TESTS]
    for path in paths:
        key = str(path.relative_to(ROOT))
        assert sha(path) == before[key] == after[key] == original_before[key] == original_after[key]
        target = PACKET/'final_sources'/key
        target.parent.mkdir(exist_ok=True, parents=True)
        shutil.copyfile(path, target)
    sources = {str(p.relative_to(ROOT)):sha(p) for p in paths}
    (PACKET/'AFTER_SHA256_001.json').write_text(json.dumps(sources, indent=2)+'\n')
    pub = ROOT/'gene_annotation_episode/native_blast_database_result_publication.py'
    original_pub = PACKET/'before/native_blast_database_result_publication.py'
    assert sha(original_pub) == '24343190ba76a4926a689fe236a7d8e4fe551d89dd3fe630b17f2c60932449a5'
    assert pub.read_text().replace(" 'blast_fasta_record_identity',", '', 1) == original_pub.read_text()
    immutable = Path('/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt')
    assert sha(immutable) == '11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7'
    dependencies = {k:v for k,v in closure.items() if k not in sources}
    installed_dependency_differences = {k:dict(tested=v, installed=sha(ROOT/k)) for k,v in dependencies.items() if sha(ROOT/k) != v}
    case_roots = sorted((RUN/'temporary/pytest').glob('test_actual_child_worker_origi[0-9]'))
    assert len(case_roots) == 4
    hosts = []
    evidence_paths = [RUN/'receipt.json', RUN/'stdout.txt', RUN/'stderr.txt', RUN/'source_hashes_before.json', RUN/'source_hashes_after.json']
    for directory in case_roots:
        body = read(directory/'actual-result.json')
        request = read(directory/'fresh-reuse-request.json')
        first = Path(request['reuse']['manifest_path']).parent
        second = Path(request['output_directory'])
        first_manifest, second_manifest = read(first/'worker-manifest.json'), read(second/'worker-manifest.json')
        assert first_manifest['calculation_id'] != second_manifest['calculation_id']
        assert first_manifest['input_identity'] == second_manifest['input_identity']
        old_rows, new_rows = json_rows(first/'rows.ndjson'), json_rows(second/'rows.ndjson')
        assert [r['record_key'] for r in old_rows] == [r['record_key'] for r in new_rows]
        for root, manifest in ((first, first_manifest), (second, second_manifest)):
            for artifact in manifest['artifacts']:
                path = root/artifact['relative_path']
                assert sha(path) == artifact['sha256'] and path.stat().st_size == artifact['size_bytes']
                evidence_paths.append(path)
            evidence_paths.append(root/'worker-manifest.json')
        published = body['publication']['rows_by_family']['sequence_record_quality']
        assert len(published) == len({r['record_key'] for r in published}) == 4
        assert len({r['identity']['assembly_source']['source_ref'] for r in published}) == 1
        assert all(set(cells(r)) == {'completeness_fraction'} and r['booleans'] == [] and r['observation_ref'] is None for r in published)
        supplied = sorted({(r['identity']['assembly_source']['record_locator']['record_ordinal'], cells(r)['completeness_fraction']) for r in published})
        assert supplied == [(0,.9),(1,.6)]
        assert body['complete'] and not body['failures']
        program = old_rows[0]['program']
        hosts.append(dict(program=program, original_metadata_schema_ids=[d['schema_id'] for d in request['metadata_descriptors'] if d['origin']=='original_job_input'],
            selected_metadata_schema_ids=[d['schema_id'] for d in request['metadata_descriptors'] if d['origin']=='selected_results_input'],
            original_calculation_id=first_manifest['calculation_id'], reused_calculation_id=second_manifest['calculation_id'],
            quality=supplied, quality_row_count=len(published), requested_metrics=['completeness_fraction'],
            functions_T1={r['identity']['function']:cells(r) for r in body['publication']['rows_by_family']['sequence_function']},
            function_probabilities_T2={r['identity']['function']:cells(r)['unadjusted_probability'] for r in new_rows if r['family']=='sequence_function'},
            original_parent_form=ident(directory/'original-parent-form.json'), original_parent_schema=ident(directory/'original-parent-schema.json'),
            received_facts=ident(directory/'received-parent-facts.json'), actual_result=ident(directory/'actual-result.json')))
        evidence_paths.extend(directory/name for name in ('original-parent-form.json','original-parent-schema.json','received-parent-facts.json',
            'selected-v2-wire.json','selected-selector.json','actual-result.json','fresh-reuse-request.json','fresh-reuse.py','fresh-reuse.stdout','fresh-reuse.stderr','received-T2-manifest.json'))
    retained = next((RUN/'temporary/pytest').glob('test_retained339_exact_wire_re[0-9]'))
    first, second = retained/'generation-1', retained/'generation-2'
    old, warmer = json_rows(first/'rows.ndjson'), json_rows(second/'rows.ndjson')
    assert [cells(r)['native_score_bits'] for r in old if r['family']=='hsp'] == [20,18]
    fg = lambda rows, metric: {r['identity']['function']:cells(r)[metric] for r in rows if r['family']=='sequence_function'}
    assert fg(old,'function_mass') == {'F':1,'G':.25}
    assert fg(old,'unadjusted_probability') == {'F':.8,'G':.2}
    assert fg(warmer,'unadjusted_probability') == {'F':2/3,'G':1/3}
    public = ROOT/'verification/tool_graders_blast_fasta_record_public_associations_2026-10-26_339/check008'
    evidence_paths.extend([public/'new_wire_payload_v2.json', public/'new_descriptor_v2.json'])
    for directory in (RUN/'temporary/pytest').iterdir():
        if not directory.is_dir() or directory.is_symlink(): continue
        if not directory.name.startswith(('test_standard_quality_', 'test_native_actual_worker_', 'test_repeated_exact_', 'test_actual_standard_worker_', 'test_v2_real_worker_', 'test_retained339_')): continue
        for path in directory.rglob('*'):
            if path.is_file() and path.name in {'worker-manifest.json','rows.ndjson','sheets.json','calculations.json','inputs.json','generation-1.request.json','request.json','reuse.json','quality-oracle.json'}:
                evidence_paths.append(path)
    receipts = []
    for directory in sorted(PACKET.glob('check[0-9][0-9][0-9]')):
        if (directory/'receipt.json').exists():
            receipts.append(dict(directory=directory.name, **{k:read(directory/'receipt.json').get(k) for k in ('returncode','policy')}, receipt=ident(directory/'receipt.json')))
    summary = dict(schema='blast_fasta_record_integration_343_evidence_v1', immutable_goal_sha256=sha(immutable),
        source_hashes=sources, tested_dependency_hashes=dependencies, installed_dependency_differences=installed_dependency_differences,
        unrelated_changes_during_check012=original_changed, unrelated_changes_during_recheck=changed_during_run,
        native_host_only_helper_inventory_changed=True, final_regression=dict(check='check012', passed=314, integration_cases=32, owned_and_worker_closure_source_stable=True,
            native_metadata_sha256=original_before['gene_annotation_episode/native_blast_database_metadata.py']),
        current_dependency_recheck=dict(check='check015', passed=32, worker_closure_source_stable=True,
            native_metadata_sha256=closure['gene_annotation_episode/native_blast_database_metadata.py']),
        hosts=hosts, retained339_worker_oracles=dict(native_bits=[20,18], masses=fg(old,'function_mass'), T1=fg(old,'unadjusted_probability'), T2=fg(warmer,'unadjusted_probability')),
        receipts=receipts, evidence=[ident(p) for p in sorted(set(evidence_paths))],
        limits=dict(synthetic_supplied_measurements=True, synthetic_native_format_emitters=True, local_fake_pbs_transport=True,
            actual_producer_capture_worker_and_typed_return=True, actual_api_or_hpc_submission=False,
            native_database_blast=False, actual_resource_exhaustion=False, installed_or_downloaded_software=False,
            annotation_credit_or_episode_changes=False, original_frozen_results_rewritten=False))
    (out/'EVIDENCE_INDEX_001.json').write_text(json.dumps(summary, indent=2)+'\n')
    (PACKET/'EVIDENCE_INDEX_001.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(dict(source_count=len(sources), host_cases=len(hosts), evidence_files=len(summary['evidence']), installed_dependency_differences=installed_dependency_differences), indent=2))
