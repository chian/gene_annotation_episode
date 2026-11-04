"""Retained SR value/custody joins and closed replay; never run native science."""
import asyncio
import base64
from bisect import bisect_right
from copy import deepcopy
import gzip
import hashlib
import json
import os
from pathlib import Path
import stat
import struct

import pytest

from gene_annotation_episode import native_lifecycle
from gene_annotation_episode import native_lumpy_execution as native
from gene_annotation_episode import vcf_result_measurements as core
from gene_annotation_episode import vcf_result_tools as host
from gene_annotation_episode.communication import plain, validate_form
from gene_annotation_episode.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_lumpy_resource_workflow import _assemble, QUESTION, FIXTURES, INFO
from test_vcf_result_workflow import _tables, _closed_child, _forbidden


EXPECTED_NATIVE_SHA256 = 'd5e915220930c1a9a85534c46d37902e621254d86ccc33866533e9c1ef807678'


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()


def _pin(path):
    mode = path.lstat().st_mode
    assert stat.S_ISREG(mode), 'retained evidence must be an actual regular file'
    raw = path.read_bytes()
    return dict(path=str(path), sha256=_sha(raw), size_bytes=len(raw), mode=stat.S_IMODE(mode))


def _tree(directory):
    return {str(path.relative_to(directory)): _pin(path) for path in sorted(directory.rglob('*'))
        if not stat.S_ISDIR(path.lstat().st_mode)}


def _document(store, reference):
    raw = store.get_artifact(reference)
    assert reference == 'artifact_' + _sha(raw)
    return json.loads(raw)


def _tokens(node, raw, descriptor, line_starts):
    """Compare retained literal addresses with bytes; do not decode a new VCF."""
    count = 0
    if type(node) is list:
        for child in node:
            count += _tokens(child, raw, descriptor, line_starts)
    elif type(node) is dict:
        if set(node) == {'raw_token', 'raw_base64', 'locator'}:
            loc = node['locator']
            assert loc['input_id'] == descriptor['input_id']
            assert loc['artifact_ref'] == descriptor['retained_file']['artifact_ref']
            assert loc['sha256'] == descriptor['retained_file']['sha256']
            start, end = loc['byte_start_0based'], loc['byte_end_0based_exclusive']
            assert type(start) is type(end) is int and 0 <= start <= end <= len(raw)
            literal = raw[start:end]
            assert base64.b64decode(node['raw_base64'], validate=True) == literal
            assert node['raw_token'] == literal.decode('utf-8')
            assert loc['line_start_1based'] == loc['line_end_1based_inclusive'] == bisect_right(line_starts, start)
            count = 1
        else:
            for child in node.values():
                count += _tokens(child, raw, descriptor, line_starts)
    return count


def _native_record_literals(record, raw):
    loc = record['locator']
    columns = raw[loc['byte_start_0based']:loc['byte_end_0based_exclusive']].split(b'\t')
    assert len(columns) >= 10
    for name, literal in zip(('chrom', 'pos', 'id', 'ref', 'alt', 'qual', 'filter', 'info'), columns[:8], strict=True):
        assert record['fixed'][name]['raw_token'] == literal.decode('utf-8')
    assert record['pos_1based'] == int(columns[1])
    assert [row['token']['raw_token'] for row in record['alts']] == columns[4].decode().split(',')
    for field in [*record['info'], *(field for sample in record['samples'] for field in sample['fields'])]:
        for value in field['values']:
            token, decoded = value['token']['raw_token'], value['decoded']
            if decoded['kind'] == 'Integer':
                assert type(decoded['value']) is int and decoded['value'] == int(token)
            elif decoded['kind'] in ('String', 'Character'):
                assert decoded['value'] == token
            elif token == '.':
                assert decoded == dict(kind='missing', value=None)
    for index, sample in enumerate(record['samples']):
        assert sample['token']['raw_token'] == columns[index + 9].decode()
    # These are literal native qualifications, not inferred quality or calls.
    if columns[5] == b'.':
        assert record['qual']['decoded'] == dict(kind='missing', value=None)
    if columns[6] == b'.':
        assert record['filter']['state'] == 'not_applied' and record['filter']['codes'] == []


def _row_join(row, original, selection):
    for key in ('record_ordinal_0based', 'line_ordinal_0based', 'locator', 'state', 'chrom', 'pos_1based',
            'identifiers', 'ref', 'alts', 'qual', 'filter'):
        assert row[key] == original[key]
    assert row['fixed'] == {**original['fixed'], 'info': None}
    assert row['info'] == [field for key in selection['info_keys'] for field in original['info'] if field['key'] == key]
    assert row['format'] == [field for key in selection['format_keys'] for field in original['format'] if field['key'] == key]
    assert row['extra_columns'] == []
    assert [sample['sample_ordinal_0based'] for sample in row['samples']] == [sample['sample_ordinal_0based'] for sample in original['samples']]
    for sample, native_sample in zip(row['samples'], original['samples'], strict=True):
        assert all(sample[key] == native_sample[key] for key in ('sample_ordinal_0based', 'sample_name', 'column_present', 'genotype'))
        assert sample['fields'] == [field for key in selection['format_keys'] for field in native_sample['fields'] if field['key'] == key]
        assert sample['token'] is None and sample['extra_fields'] == []


def _publication(store, returned, native_bytes):
    source = store.get(returned['source_ref'])
    assert (source['record_type'], source['origin'], source['provider'], source['version']) == (
        'source', 'tool', host.TOOL, host.SOURCE_VERSION)
    packet = _document(store, source['artifact_ref'])
    sheet_ref, components_ref, grading_ref = source['auxiliary_artifact_refs']
    sheet, components = _document(store, sheet_ref), _document(store, components_ref)
    control, grading = _document(store, source['request_ref']), _document(store, grading_ref)
    assert set(control) == set(host._CONTROL_KEYS.split())
    assert control['version'] == host.CONTROL_VERSION and control['native_call_state'] == 'not_requested'
    assert control['calculator_id'] == host.CALCULATOR_ID
    assert (control['sheet_ref'], control['components_ref'], control['grading_ref'], control['public_packet_ref']) == (
        sheet_ref, components_ref, grading_ref, source['artifact_ref'])
    assert components['version'] == core.COMPONENTS_VERSION and sheet['version'] == core.SHEET_VERSION
    assert components['sheet_sha256'] == _sha(_canonical(sheet))
    assert components['value'] == returned['value'] == packet['value']
    assert packet == dict(version=host.PACKET_VERSION, value=returned['value'])
    assert grading == dict(schema='tool_grading_artifact_v1', provider=host.TOOL,
        native_artifact_ref=source['artifact_ref'], grading=dict(sheet=sheet, scores=components))
    assert control['arguments']['selection'] == returned['value']['selection']
    descriptor = sheet['input']
    assert descriptor == components['value']['input']
    assert descriptor['capture'] == dict(state='complete', byte_start_0based=0,
        byte_end_0based_exclusive=len(native_bytes), original_size_bytes=len(native_bytes))
    assert descriptor['original_file'] == descriptor['retained_file']
    assert descriptor['retained_file'] == dict(artifact_ref='artifact_' + _sha(native_bytes),
        sha256=_sha(native_bytes), size_bytes=len(native_bytes), format='vcf')
    assert sheet['raw_content'] == dict(encoding='base64', data=base64.b64encode(native_bytes).decode(),
        sha256=_sha(native_bytes), size_bytes=len(native_bytes))
    assert sheet['header']['state'] == 'available' and sheet['header']['fileformat'] == 'VCFv4.2'
    assert all(row['state'] == 'decoded' for row in sheet['records'])
    return dict(source=source, sheet=sheet, components=components, control=control,
        packet=packet, references=[source['artifact_ref'], source['request_ref'], sheet_ref, components_ref, grading_ref])


def _header_evidence(plan, seal):
    signals = plan['requested_job']['native_lumpy']['request']['signals']
    assert len(signals) == 1 and signals[0]['kind'] == 'split_read'
    signal = signals[0]
    assert signal['read_group'] is signal['declared_sample_id'] is signal['reference_id'] is None
    assert signal['parameters'] == dict(back_distance=10, min_non_overlap=25, weight=1, min_mapping_threshold=20, min_clip=20)
    binding, = plan['requested_job']['native_lumpy']['input_bindings']
    assert binding['file'] == signal['bam']
    assert _pin(Path(binding['path']))['sha256'] == signal['bam']['sha256']
    with gzip.open(binding['path'], 'rb') as stream:
        def exact(size):
            value = stream.read(size)
            assert len(value) == size
            return value
        def integer():
            return struct.unpack('<i', exact(4))[0]
        assert exact(4) == b'BAM\x01'
        text = exact(integer())
        dictionary = []
        for _ in range(integer()):
            name = exact(integer())
            assert name.endswith(b'\0')
            dictionary.append((name[:-1].decode(), integer()))
    output, = [row for row in seal['outputs'] if row['specification']['role'] == 'bam_header']
    header = Path(plan['attempt_directory']) / output['specification']['relative_path']
    assert header.read_bytes() == text and output['declaration']['sha256'] == _sha(text)
    inspection, = seal['input_inspections']
    assert inspection['producer_outcome'] == 'succeeded' and inspection['supplied_extent'] == 'complete'
    assert inspection['header'] == output['declaration'] and inspection['input_file'] == signal['bam']
    lines = text.decode().splitlines()
    sq, labels = [], []
    for line in lines:
        fields = line.split('\t')
        if fields[0] == '@SQ':
            values = dict(field.split(':', 1) for field in fields[1:])
            sq.append((values['SN'], int(values['LN'])))
        elif fields[0] == '@RG':
            labels.append(dict(field.split(':', 1) for field in fields[1:]))
    assert sq == dictionary
    return dict(output_sample_label=signal['output_sample_label'], bam_read_groups=labels,
        header=_pin(header), reference_dictionary=dictionary, declared_sample_id=None, reference_build=None,
        qualification='Literal header labels and references only; no authenticated biological sample/build association.')


def test_retained_SR_native_values_publication_parent_and_closed_reconstruction(tmp_path, monkeypatch):
    selected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RESOURCE_PROOF')
    expected = os.environ.get('HMMER_NATIVE_ORACLE_LUMPY_RESOURCE_PROOF_SHA256')
    if not selected or not expected:
        pytest.skip('requires the explicit completed original SR Workflow proof and digest')
    proof_path = Path(selected).resolve(strict=True)
    assert _sha(proof_path.read_bytes()) == expected
    proof = json.loads(proof_path.read_bytes())
    assert proof['version'] == 'lumpy_resource_workflow_proof_v1' and proof['question'] == QUESTION
    audit = dict(version='lumpy_resource_retained_audit_v1', original_proof=_pin(proof_path), passed=False,
        original_passed=proof['passed'], original_failure=proof.get('failure'),
        new_native_calls=0, new_parser_calls=0, new_calculator_calls=0, new_tool_calls=0,
        new_provider_decision_calls=0, provider_cleanup_callbacks=[])
    provider = None
    try:
        plan = native.validate_lumpy_run_plan(proof['native_plan'])
        seal = native.validate_lumpy_seal(proof['native_seal'], plan=plan)
        assert seal['outcome'] == 'succeeded' and seal['returncode'] == 0
        native_path = Path(plan['attempt_directory']) / 'native/result.vcf'
        raw = native_path.read_bytes()
        declaration, = [row['declaration'] for row in seal['outputs'] if row['specification']['role'] == 'vcf']
        assert declaration['state'] == 'present' and declaration['sha256'] == _sha(raw) == EXPECTED_NATIVE_SHA256
        assert declaration['size_bytes'] == len(raw) == 909083
        expected_file = FIXTURES / 'test_onlysplit.bam.vcf'
        assert raw == expected_file.read_bytes()
        associations = _header_evidence(plan, seal)
        protected_files = [native_path, Path(plan['attempt_directory']) / native.SEAL_FILENAME,
            *[Path(row['path']) for row in plan['requested_job']['native_lumpy']['input_bindings']]]
        originals = {str(path): _pin(path) for path in protected_files}
        with Store(proof['store_directory']) as store:
            before = _tables(store)
            artifacts = _tree(store.path / 'artifacts')
            libraries = _tree(Path(proof['directory']) / 'run/scientific-process-library')
            rows = list(store.db.execute('SELECT result FROM tool_operations WHERE name=? ORDER BY rowid', (host.TOOL,)))
            assert len(rows) == 3
            original, derived, read = [json.loads(row[0]) for row in rows]
            assert all(value['status'] in ('completed', 'partial') for value in (original, derived, read))
            assert original['result']['source_ref'] != derived['result']['source_ref']
            assert derived['result'] == read['result'] and read['changed_record_refs'] == []
            group = [original['result'], derived['result']]
            assert proof['returned'] == group
            publications = [_publication(store, returned, raw) for returned in group]
            first, saved = publications
            assert first['sheet'] == saved['sheet'] and first['control']['sheet_ref'] == saved['control']['sheet_ref']
            native_source = first['sheet']['input']['source_ref']
            assert store.get(native_source)['artifact_ref'] == 'artifact_' + _sha(raw)
            assert first['source']['parent_source_refs'] == [native_source]
            assert saved['source']['parent_source_refs'] == [group[0]['source_ref']]
            assert first['control']['arguments']['mode'] == 'analyze' and saved['control']['arguments']['mode'] == 'calculate_saved'
            assert first['control']['arguments']['reference'] == native_source
            assert first['control']['arguments']['namespace'] == 'source'
            assert saved['control']['original_source'] == dict(source_ref=group[0]['source_ref'],
                record_sha256=_sha(_canonical(first['source'])))
            assert all(saved['control'][key] == first['control'][key] for key in
                ('admission_invocation', 'received_input', 'file_admission', 'sheet_ref'))
            sheet = first['sheet']
            line_starts = [0, *[index + 1 for index, byte in enumerate(raw) if byte == 10]]
            verified_tokens = _tokens(sheet, raw, sheet['input'], line_starts)
            contigs = dict(associations['reference_dictionary'])
            for row in sheet['records']:
                _native_record_literals(row, raw)
                assert row['chrom'] in contigs and 1 <= row['pos_1based'] <= contigs[row['chrom']]
            n = len(sheet['records'])
            assert n >= 2
            examples = []
            for returned, expected_ordinals, requested_ordinals, selected_count in (
                    (group[0], [0, 1], None, n), (group[1], [1, 0], [1, 0], 2)):
                value, selection = returned['value'], returned['value']['selection']
                assert selection['record_ordinals'] == requested_ordinals
                assert selection['sample_ordinals'] is None and selection['offset'] == 0 and selection['limit'] == 2
                assert selection['info_keys'] == INFO and selection['format_keys'] == ['GT', 'SU', 'PE', 'SR']
                assert [row['record_ordinal_0based'] for row in value['records']] == expected_ordinals
                population = value['population']
                assert population['capture_state'] == 'complete' and population['header_state'] == 'available'
                assert population['record_population_complete'] is True
                assert [population[key] for key in ('total_original_record_slots', 'retained_record_slots', 'selected_record_slots',
                    'returned_record_slots', 'omitted_by_window_record_slots')] == [n, n, selected_count, 2, selected_count - 2]
                assert population['returned_record_fraction'] == dict(value=2 / selected_count, numerator=2,
                    denominator=selected_count, unit='fraction', missing_reason=None)
                assert population['has_more'] is (selected_count > 2)
                for row in value['records']:
                    _row_join(row, sheet['records'][row['record_ordinal_0based']], selection)
                assert [sample['name']['raw_token'] for sample in value['header']['samples']] == [associations['output_sample_label']]
                assert population['returned_alt_tokens'] == sum(len(row['alts']) for row in value['records'])
                assert population['returned_sample_cells'] == population['returned_observed_sample_cells'] == 2
                assert population['returned_genotype_slots'] == sum(len(sample['genotype']['alleles'])
                    for row in value['records'] for sample in row['samples'] if sample['genotype'] is not None)
                selected_rows = sheet['records'] if requested_ordinals is None else [sheet['records'][index] for index in requested_ordinals]
                assert population['selected_alt_tokens'] == sum(len(row['alts']) for row in selected_rows)
                assert population['selected_sample_cells'] == sum(len(row['samples']) for row in selected_rows)
                assert population['selected_observed_sample_cells'] == sum(sample['column_present']
                    for row in selected_rows for sample in row['samples'])
                assert population['selected_genotype_slots'] == sum(len(sample['genotype']['alleles'])
                    for row in selected_rows for sample in row['samples'] if sample['genotype'] is not None)
                examples.append(dict(source_ref=returned['source_ref'], population=deepcopy(population),
                    records=deepcopy(value['records'])))
            records = EpisodeReturnRecords(store, proof['run_id'], failure_prefix='lumpy_resource_retained_')
            contexts = [records.context(row[0]) for row in store.db.execute(
                'SELECT episode_id FROM runtime_episodes WHERE run_id=? ORDER BY rowid', (proof['run_id'],))]
            parent, = [context for context in contexts if context.role == 'annotation']
            science, = [context for context in contexts if context.role == 'scientific_process']
            form, = list(store.db.execute('SELECT facts,form FROM runtime_forms WHERE run_id=? '
                'AND json_extract(form,\'$.variants\') IS NOT NULL', (proof['run_id'],)))
            assert json.loads(form['form']) == dict(variants=group) and json.loads(form['facts'])[host.FACT_SOURCE] == group
            attempts = list(store.db.execute('SELECT failure,form FROM runtime_report_attempts WHERE run_id=? '
                'AND json_extract(form,\'$.variants\') IS NOT NULL', (proof['run_id'],)))
            assert any(row['failure'] is None and json.loads(row['form']) == dict(variants=group) for row in attempts)
            public_files = {publication['source']['artifact_ref'] for publication in publications}
            private = {ref for publication in publications for ref in publication['references']}
            private.add('artifact_' + _sha(raw))
            get, reads = Store.get_artifact, []
            def public_packet(current, reference, *args, **kwargs):
                assert reference in public_files, 'fact refresh attempted a private or native File read'
                reads.append(reference)
                return get(current, reference, *args, **kwargs)
            class NoNewSRDecisions:
                complete = _forbidden

                def __init__(self):
                    self.cleanup_callbacks = []

                async def release(self, episode_id):
                    self.cleanup_callbacks.append(episode_id)
            provider = NoNewSRDecisions()
            with monkeypatch.context() as patch:
                for name in ('parse_vcf_sheet', 'calculate_vcf_components'):
                    patch.setattr(core, name, _forbidden)
                for name in ('run_lumpy', 'prepare_local_lumpy', 'freeze_lumpy_software_binding'):
                    patch.setattr(native, name, _forbidden)
                for name in ('prepare_job', 'start_prepared', 'resume_start', 'wait_job', 'collect', 'status', 'cancel', 'release'):
                    patch.setattr(native_lifecycle, name, _forbidden)
                patch.setattr(ToolRegistry, 'execute_async', _forbidden)
                patch.setattr(Store, 'artifact', _forbidden)
                patch.setattr(Store, 'put', _forbidden)
                patch.setattr(Store, 'get_artifact', public_packet)
                patch.setattr('gene_annotation_episode.materials._verified_artifact_path', _forbidden)
                patch.setattr('gene_annotation_episode.native_file_capture._verified_artifact_path', _forbidden)
                patch.setattr('gene_annotation_episode.acquisition.PublicClients._http', _forbidden)
                patch.setattr('subprocess.run', _forbidden)
                patch.setattr('subprocess.Popen', _forbidden)
                patch.setattr('socket.create_connection', _forbidden)
                workflow, _ = _assemble(store, proof, provider)
                with patch.context() as closed:
                    closed.setattr(Store, 'get_artifact', _forbidden)
                    root = workflow.build('annotation', 'root', QUESTION, proof['scope'])
                    completed = asyncio.run(root.run_async(workflow.context))
                    assert plain(asyncio.run(root.build_result(completed)).as_record()) == dict(credit=0, pending_handles=[])
                    assert _closed_child(workflow, root, parent, science) == dict(form=dict(variants=group))
                assert workflow.services.molecular_own_facts(science, fact_source=host.FACT_SOURCE) == group
                assert workflow.services.molecular_frozen_facts(science, fact_source=host.FACT_SOURCE) == group
                assert workflow.services.molecular_received_facts(parent, fact_source=host.FACT_SOURCE) == group
                known = set(workflow.receipts.known(parent.episode_id))
                assert {item['source_ref'] for item in group} <= known
                assert private.isdisjoint(known) and native_source not in known
                assert set(proof['initial_refs']) <= known
                delivered = list(store.db.execute('SELECT record_ref FROM runtime_record_receipts '
                    'WHERE run_id=? AND episode_id=? AND receipt_kind=\'child_form\' ORDER BY receipt_index',
                    (proof['run_id'], parent.episode_id)))
                assert {row['record_ref'] for row in delivered} == {item['source_ref'] for item in group}
                resolver = workflow.resolver(plain(parent.scope), context=parent)
                assert all(resolver(item['source_ref'], 'source') for item in group)
                assert all(resolver(reference, 'artifact') for reference in proof['initial_refs'])
                assert not any(resolver(reference, 'artifact') for reference in private)
                assert resolver(native_source, 'source') is False
                resolved = []
                def resolve(reference, namespace):
                    resolved.append((reference, namespace))
                    return resolver(reference, namespace)
                assert validate_form(dict(variants=group), proof['parent_schema'], resolve) == dict(variants=group)
                assert set(resolved) == {(item['source_ref'], 'source') for item in group}
            assert set(reads) == public_files
            assert _tables(store) == before
            assert _tree(store.path / 'artifacts') == artifacts
            assert _tree(Path(proof['directory']) / 'run/scientific-process-library') == libraries
            assert {str(path): _pin(path) for path in protected_files} == originals
            assert _pin(proof_path) == audit['original_proof']
            audit.update(passed=True, native_file=_pin(native_path), upstream_expected=_pin(expected_file),
                byte_equal_upstream=True, associations=associations, verified_literal_tokens=verified_tokens,
                shared_sheet_sha256=_sha(_canonical(sheet)), source_groups=[item['source_ref'] for item in group],
                selected_value_examples=examples, public_packet_reads=reads,
                provider_cleanup_callbacks=list(provider.cleanup_callbacks),
                all_original_rows_unchanged=True, artifacts_and_library_unchanged=True,
                original_input_grants_preserved=True, private_or_native_File_grants=[],
                original_call_count_qualification='Three original ToolOperations retained; original parser/calculator call counts were not instrumented.')
    except BaseException as error:
        audit['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if provider is not None:
            audit['provider_cleanup_callbacks'] = list(provider.cleanup_callbacks)
        (tmp_path / 'lumpy_resource_retained_audit.json').write_text(json.dumps(audit, indent=2, allow_nan=False) + '\n')
