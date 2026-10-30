"""Exact retained envelope and live-source pin compatibility; no native jobs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import alignment_correspondence as common
from gene_annotation_episode import biopython_pairwise_grader as pairwise
from gene_annotation_episode import native_protein_structure_worker as worker
from gene_annotation_episode import protein_structure_contracts as science
from gene_annotation_episode import protein_structure_operands as operands
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_contracts import canonical
from gene_annotation_episode.native_protein_structure_contracts import validate_protein_structure_software
from gene_annotation_episode.protein_structure_authority import ProteinStructureOperandError
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import SequenceWork, ToolRegistry


def envelope(version):
    # Explicit engineering traceback fixture, not a claimed native execution.
    native = {"native_format": "biopython_pairwise_native_v2", "aligned": True, "mode": "global",
        "query_length": 4, "reference_length": 4, "native_score": 19., "matrix": "BLOSUM62",
        "gap_open": -10., "gap_extend": -.5, "aligned_query": "AGST", "aligned_reference": "AGST",
        "query_interval": [0, 4], "reference_interval": [0, 4], "coordinates": [[0, 4], [0, 4]]}
    grading = pairwise.grade_biopython_pairwise(native, molecule="protein", _retain_correspondence=version == 2)
    companion = grading.pop("correspondence", None)
    result = {"schema": "tool_grading_artifact_v" + str(version), "provider": "biopython.alignment",
        "native_artifact_ref": "constructed-native-artifact", "grading": grading}
    if companion is not None:
        result["correspondence"] = companion
    return result


@pytest.mark.parametrize("version", [1, 2])
def test_explicit_legacy_and_common_envelopes_preserve_the_legacy_sheet(version, monkeypatch):
    value = envelope(version)
    original = deepcopy(value)
    def no_calculation(*args, **kwargs):
        raise AssertionError("frozen envelope validation recalculated scientific values")
    monkeypatch.setattr(common, "calculate_correspondence_components", no_calculation)
    monkeypatch.setattr(pairwise, "calculate_biopython_pairwise_scores", no_calculation)
    monkeypatch.setattr(pairwise, "build_biopython_pairwise_sheet", no_calculation)
    result = worker._alignment_grading(value, native_artifact_ref="constructed-native-artifact",
        grading_format="tool_grading_artifact_v" + str(version))
    assert set(result) == {"sheet", "scores"}
    assert result["scores"]["paired_positions"] == 4
    assert value == original


@pytest.mark.parametrize("mutation", ["native_identity", "unknown_outer_field", "inner_companion", "missing_companion",
    "extra_instance", "axis_basis", "legacy_pointer", "common_counts", "common_input", "legacy_scores"])
def test_v2_conflicts_are_rejected_without_rewriting_the_stored_artifact(mutation):
    value = envelope(2)
    if mutation == "native_identity": value["native_artifact_ref"] = "different"
    elif mutation == "unknown_outer_field": value["unexpected"] = 1
    elif mutation == "inner_companion": value["grading"]["correspondence"] = deepcopy(value["correspondence"])
    elif mutation == "missing_companion": del value["correspondence"]
    elif mutation == "extra_instance": value["correspondence"]["instances"].append(deepcopy(value["correspondence"]["instances"][0]))
    elif mutation == "axis_basis": value["correspondence"]["instances"][0]["axis_basis"] = "reported"
    elif mutation == "legacy_pointer": value["correspondence"]["instances"][0]["legacy_pointer"] = "/different"
    elif mutation == "common_counts": value["correspondence"]["instances"][0]["components"]["rows"][0]["counts"]["paired_positions"] = 3
    elif mutation == "common_input": value["correspondence"]["instances"][0]["sheet"]["operands"]["query"]["length"] = 5
    else: value["grading"]["scores"]["paired_positions"] = 3
    original = deepcopy(value)
    with pytest.raises(ValueError, match="invalid_traceback|alignment_operand_mismatch"):
        worker._alignment_grading(value, native_artifact_ref="constructed-native-artifact", grading_format="tool_grading_artifact_v2")
    assert value == original


def descriptor(value):
    def identity(raw, format_name):
        digest = hashlib.sha256(raw).hexdigest()
        return dict(artifact_ref="artifact_" + digest, sha256=digest, byte_length=len(raw), format=format_name)
    native_file = identity(canonical(value["grading"]["sheet"]["native_result"]).encode(), "biopython_pairwise_json")
    value["native_artifact_ref"] = native_file["artifact_ref"]
    grading_file = identity(canonical(value).encode(), value["schema"])
    return dict(version="structure_alignment_descriptor_v1", observation_ref="observation_" + "a"*24,
        source_ref="source_" + "b"*24, original_operation_key="constructed-alignment",
        query_reference_ref="reference_" + "c"*24, reference_reference_ref="reference_" + "d"*24,
        native_file=native_file, grading_file=grading_file, molecule="protein", mode="global",
        traceback_selection="explicit_retained", producer_traceback_selection="first_native_optimal_returned",
        optimal_alternative_count=None)


@pytest.mark.parametrize("version", [1, 2])
def test_truthful_descriptor_schema_and_validator_admit_exact_outer_version(version):
    value = envelope(version)
    claimed = descriptor(value)
    schema = {"$defs": science.protein_structure_schema_definitions(), "$ref": "#/$defs/AlignmentDescriptor"}
    Draft202012Validator(schema).validate(claimed)
    assert science.validate_alignment_descriptor(claimed) == claimed
    result = worker._alignment_grading(value, native_artifact_ref=claimed["native_file"]["artifact_ref"],
        grading_format=claimed["grading_file"]["format"])
    assert result == value["grading"]
    with pytest.raises(ValueError, match="alignment_operand_mismatch"):
        worker._alignment_grading(value, native_artifact_ref=claimed["native_file"]["artifact_ref"],
            grading_format="tool_grading_artifact_v" + str(3-version))


def test_unknown_descriptor_and_outer_version_are_rejected():
    value = envelope(2)
    claimed = descriptor(value)
    claimed["grading_file"]["format"] = "tool_grading_artifact_v3"
    schema = {"$defs": science.protein_structure_schema_definitions(), "$ref": "#/$defs/AlignmentDescriptor"}
    assert not Draft202012Validator(schema).is_valid(claimed)
    with pytest.raises(ValueError, match="invalid_schema|unsupported_format"):
        science.validate_alignment_descriptor(claimed)
    value["schema"] = "tool_grading_artifact_v3"
    with pytest.raises(ValueError, match="invalid_traceback"):
        worker._alignment_grading(value, native_artifact_ref=claimed["native_file"]["artifact_ref"],
            grading_format=claimed["grading_file"]["format"])


def historical_software_shape():
    # Structurally valid frozen selection, deliberately not executable pins.
    return {"python_executable": sys.executable, "python_sha256": "0"*64, "python_version": "constructed",
        "driver_module": "gene_annotation_episode.native_protein_structure_driver",
        "worker_module": "gene_annotation_episode.native_protein_structure_worker",
        "implementation_files": [{"module": "gene_annotation_episode.native_protein_structure_driver", "sha256": "0"*64},
            {"module": "gene_annotation_episode.native_protein_structure_worker", "sha256": "0"*64}],
        "numpy_version": "constructed", "biopython_version": "constructed",
        "implementation": "gene_annotation_episode_corrected_protein_structure_v1", "algorithm": "unweighted_proper_rigid_ca_svd_v1"}


def test_historical_software_shape_stays_valid_but_current_execution_requires_transitive_pins(monkeypatch):
    selected = historical_software_shape()
    assert validate_protein_structure_software(selected) == selected
    monkeypatch.setattr(worker, "_checksum", lambda *args: pytest.fail("missing closure reached byte verification"))
    with pytest.raises(ValueError, match="software_identity_mismatch"):
        worker.check_selected_software(selected)


_RETAINED398 = Path(__file__).resolve().parents[1] / (
    'verification/tool_graders_protein_structure_operands_2026-10-27_398/'
    'check005/temporary/pytest/398-original-native-fixtures0')
_RETAINED_FILES = {
    'fixture.json': ('ce2ce51127e309f3dc89e36ee7cf071ed4815835666a91d1ed9d2cfb53c280eb', 633184),
    'original-alignment-0.json': ('e8994cd4a2e30f784ae9b2ad2107e9871fded9149d7125d224b4f0cf5bb1a700', 547),
    'original-alignment-1.json': ('e8994cd4a2e30f784ae9b2ad2107e9871fded9149d7125d224b4f0cf5bb1a700', 547),
    'original-alignment-2.json': ('133b26226c81b1a18bc672a77792459f8546b0b3925fbbd3406facab25e208a4', 561),
    'original-alignment-3.json': ('da6d4253c6ee33bc5e83d3b81c167e9e2d1a37fd7df2156fbd923c2c101a1821', 117),
}
_ALIGNMENTS = (
    ('global', 'fixed', 'moving', 'fixed_is_query', 0),
    ('reverse', 'fixed', 'moving', 'fixed_is_reference', 1),
    ('local', 'local', 'fixed', 'fixed_is_query', 2),
    ('zero', 'zero_q', 'zero_r', 'fixed_is_query', 3),
)


def _forbidden(*args, **kwargs):
    raise AssertionError('retained operand read attempted native work, scoring, fitting, acquisition or publication')


class _RetainedPorts:
    """Engineered authority ports; no claim of a new typed Workflow delivery."""
    def __init__(self, case):
        self.store, self.context = case.store, case.context
        self.run_id, self.data, self.alignment = self.context.run_id, case.data, None

    def authenticate(self, context, *, allow_unsaved=False):
        assert context is self.context
        return context

    def authenticate_received_sequence(self, context, descriptor, *, required_use):
        assert context is self.context
        rows = [row for row in self.data['rows'].values() if row['descriptor'] == descriptor]
        assert len(rows) == 1 and required_use in descriptor['allowed_uses']
        return deepcopy(rows[0]['view'])

    def authenticate_received_alignment(self, context, descriptor):
        assert context is self.context and descriptor == self.alignment

    def resolve_received(self, context, reference, namespace):
        assert context is self.context
        return None

    retained_reference_access = resolve_received


@pytest.fixture
def retained_operand_case(tmp_path):
    """Copy the authentic398 retained Store; never run its original_assets fixture."""
    for name, expected in _RETAINED_FILES.items():
        raw = (_RETAINED398 / name).read_bytes()
        assert (hashlib.sha256(raw).hexdigest(), len(raw)) == expected
    inputs = [path for path in (_RETAINED398 / 'store').rglob('*') if path.is_file()]
    assert len(inputs) == 58 and sum(path.stat().st_size for path in inputs) == 1033452
    assert not any(path.is_symlink() for path in inputs)
    assert (_RETAINED398 / 'store/state.sqlite3-wal').stat().st_size == 0
    clone = tmp_path / 'store'
    shutil.copytree(_RETAINED398 / 'store', clone)
    # The runner freezes its input snapshot. Only the fresh test copy is writable.
    for path in clone.rglob('*'):
        path.chmod(0o700 if path.is_dir() else 0o600)
    clone.chmod(0o700)
    control = sqlite3.connect('file:' + str(clone / 'state.sqlite3') + '?mode=ro&immutable=1', uri=True)
    control.row_factory = sqlite3.Row
    archived = {table: [dict(row) for row in control.execute('SELECT * FROM ' + table)]
        for table in ('records', 'artifacts', 'tool_operations', 'runtime_record_receipts')}
    control.close()
    with Store(clone) as store:
        data = json.loads((_RETAINED398 / 'fixture.json').read_bytes())
        context = SimpleNamespace(run_id='synthetic-run', episode_id='operand-reader', role='scientific',
            scope=data['scope'], assignment={})
        case = SimpleNamespace(store=store, context=context, data=data, root=tmp_path)
        case.ports = _RetainedPorts(case)
        # Fresh engineering associations may be added; recorded398 facts are
        # immutable inputs and must survive every setup and operand read.
        case.archived = archived
        yield case
        for table, before in case.archived.items():
            after = [dict(row) for row in store.db.execute('SELECT * FROM ' + table)]
            assert all(row in after for row in before)


def _retained_alignment(case, label, version):
    selected, = [row for row in _ALIGNMENTS if row[0] == label]
    ordinal = selected[-1]
    original = deepcopy(case.data['alignments'][label]['descriptor'])
    raw = (_RETAINED398 / ('original-alignment-' + str(ordinal) + '.json')).read_bytes()
    assert case.store.get_artifact(original['native_file']['artifact_ref']) == raw
    legacy = json.loads(case.store.get_artifact(original['grading_file']['artifact_ref']))
    assert legacy['schema'] == 'tool_grading_artifact_v1'
    descriptor = original
    if version == 2:
        registry, requests = ToolRegistry(case.store), []
        path = case.root / ('retained-alignment-' + str(ordinal) + '.json')
        path.write_bytes(raw)

        async def retained_work(*args, **kwargs):
            requests.append((args, kwargs))
            return SequenceWork(path, {'fixture': 'authentic398 retained native bytes; no new alignment'})

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(registry, '_prepare_sequence_work_async', retained_work)
            patch.setattr('gene_annotation_episode.sequence_ops.align_pair', _forbidden)
            patch.setattr('gene_annotation_episode.native_lifecycle.prepare_job', _forbidden)
            patch.setattr(worker, 'execute_protein_structure_request', _forbidden)
            arguments = deepcopy(case.data['alignments'][label]['arguments'])
            key = 'synthetic-run:operand-reader:' + str(4 + ordinal)
            outcome = registry.execute('sequence.align', arguments, operation_key=key)
        assert outcome['status'] == 'completed' and len(requests) == 1
        source = case.store.get(outcome['result']['source_ref'])
        grade_ref, = source['auxiliary_artifact_refs']
        body = json.loads(case.store.get_artifact(grade_ref))
        assert body['schema'] == 'tool_grading_artifact_v2'
        assert canonical(body['grading']) == canonical(legacy['grading'])
        assert source['artifact_ref'] == original['native_file']['artifact_ref']
        assert source['version'] == json.loads(raw)['biopython_version']
        metadata = case.store.get(grade_ref)
        descriptor.update(source_ref=source['id'], observation_ref=outcome['result']['observation_ref'],
            original_operation_key=key, grading_file={'artifact_ref': grade_ref, 'sha256': metadata['sha256'],
                'byte_length': metadata['size'], 'format': body['schema']})
        EpisodeReceipts(case.store, case.context.run_id).receive(case.context.episode_id,
            [descriptor['source_ref'], descriptor['observation_ref'], grade_ref], kind='initial')
    else:
        body = legacy
    case.ports.alignment = deepcopy(descriptor)
    fixed, moving = [deepcopy(case.data['rows'][name]['descriptor']) for name in selected[1:3]]
    return descriptor, body, fixed, moving, selected[3]


def _read_only(case, monkeypatch):
    for target in (
        'gene_annotation_episode.sequence_ops.align_pair',
        'gene_annotation_episode.native_protein_structure_worker.execute_protein_structure_request',
        'gene_annotation_episode.protein_structure_formats.parse_pdb_structure',
        'gene_annotation_episode.protein_structure_formats.parse_mmcif_structure',
        'gene_annotation_episode.protein_structure_sequences.extract_structure_sequence',
        'gene_annotation_episode.protein_structure_calculations.calculate_protein_structure_components',
        'gene_annotation_episode.protein_structure_calculations.fit_ca_transform',
        'numpy.linalg.svd',
        'gene_annotation_episode.biopython_pairwise_grader.grade_biopython_pairwise',
        'gene_annotation_episode.biopython_pairwise_grader.calculate_biopython_pairwise_scores',
        'gene_annotation_episode.tool_grading_artifacts.retain_tool_grading',
        'gene_annotation_episode.protein_structure_publication.publish_protein_structure_source',
        'gene_annotation_episode.native_protein_structure_acquisition.capture_local_protein_structure_bundle',
        'gene_annotation_episode.native_lifecycle.prepare_job',
        'gene_annotation_episode.native_lifecycle.start_prepared',
        'gene_annotation_episode.native_lifecycle.resume_start',
        'subprocess.Popen', 'subprocess.run', 'socket.create_connection', 'socket.socket.connect'):
        monkeypatch.setattr(target, _forbidden)
    monkeypatch.setattr(case.store, 'put', _forbidden)
    monkeypatch.setattr(case.store, 'artifact', _forbidden)
    case.store.db.execute('PRAGMA query_only=ON')
    # The existing _check_snapshot may rebuild its consistency sheet through
    # the shared counter/calculator. It never publishes or replaces saved cells.
    case.before_read = tuple(case.store.db.iterdump()), case.store.db.total_changes


def _unchanged(case):
    assert (tuple(case.store.db.iterdump()), case.store.db.total_changes) == case.before_read


@pytest.mark.parametrize('version', [1, 2])
@pytest.mark.parametrize('label', ['global', 'reverse', 'local', 'zero'])
def test_retained_operand_versions_preserve_saved_alignment(retained_operand_case, monkeypatch, version, label):
    case = retained_operand_case
    descriptor, body, fixed, moving, orientation = _retained_alignment(case, label, version)
    original, calls = deepcopy(descriptor), []
    actual = operands.validate_tool_correspondence

    def shared(grading, companion, *, admission):
        assert admission is False
        calls.append((deepcopy(grading), deepcopy(companion)))
        return actual(grading, companion, admission=admission)

    monkeypatch.setattr(operands, 'validate_tool_correspondence', shared)
    _read_only(case, monkeypatch)
    snapshot = operands.authenticate_selected_alignment(case.store, case.context, descriptor,
        fixed=fixed, moving=moving, orientation=orientation, returns=case.ports)
    assert snapshot['descriptor'] == descriptor == original
    assert snapshot['pairwise_sheet'] == body['grading']['sheet']
    assert snapshot['native_result'] == body['grading']['sheet']['native_result']
    assert calls == ([(body['grading'], body['correspondence'])] if version == 2 else [])
    _unchanged(case)


@pytest.mark.parametrize('version', [1, 2])
def test_retained_operand_versions_resolve_selected_comparison_inputs(retained_operand_case, monkeypatch, version):
    case = retained_operand_case
    descriptor, _, fixed, moving, orientation = _retained_alignment(case, 'global', version)
    request = deepcopy(case.data['saved']['view']['request'])
    for side, sequence in (('fixed', fixed), ('moving', moving)):
        request[side + '_selection'] = deepcopy(sequence['selection'])
        request[side + '_selection']['structure_role'] = side
    for key in ('fit_selection', 'evaluation_selection'):
        request['parameters'][key] = {'kind': 'all_mapped_pairs'}
    request['correspondence'] = {'kind': 'retained_alignment', 'alignment': descriptor,
        'fixed_sequence_descriptor': fixed, 'moving_sequence_descriptor': moving, 'orientation': orientation}
    original = deepcopy(request)
    _read_only(case, monkeypatch)
    resolved = operands.resolve_comparison_operands(case.store, case.context, request, returns=case.ports)
    assert resolved['request'] == request == original
    assert len(resolved['input_files']) == 8
    grading, = [row for row in resolved['input_files'] if row['role'] == 'alignment_grading']
    assert grading['file_identity'] == descriptor['grading_file']
    assert grading['file_identity']['format'] == 'tool_grading_artifact_v' + str(version)
    assert all(row['path'] == str(case.store.path / 'artifacts' / row['file_identity']['sha256'][:2]
        / row['file_identity']['sha256']) for row in resolved['input_files'])
    _unchanged(case)


def _forged_grading(case, descriptor, body):
    """Adversarial fresh associations; never rewrite a recorded398 source/observation."""
    raw = canonical(body).encode()
    artifact = case.store.artifact(raw, 'application/vnd.gene-annotation.tool-grading+json')
    metadata = case.store.get(artifact)
    descriptor['grading_file'] = {'artifact_ref': artifact, 'sha256': metadata['sha256'],
        'byte_length': metadata['size'], 'format': 'tool_grading_artifact_v2'}
    source = case.store.get(descriptor['source_ref'])
    payload = {key: value for key, value in source.items() if key not in {'id', 'record_type', 'origin'}}
    payload['auxiliary_artifact_refs'] = [artifact]
    source = case.store.put('source', payload, origin='tool')
    observation = case.store.get(descriptor['observation_ref'])
    payload = {key: value for key, value in observation.items() if key not in {'id', 'record_type', 'origin'}}
    payload['source_ref'] = source['id']
    observation = case.store.put('observation', payload, origin='tool')
    row = case.store.db.execute('SELECT * FROM tool_operations WHERE operation_key=?',
        (descriptor['original_operation_key'],)).fetchone()
    # Only the new, deliberately engineered4+ row can be changed here.
    assert int(descriptor['original_operation_key'].rsplit(':', 1)[1]) >= 4
    result = json.loads(row['result'])
    result['record_refs'] = [source['id'], observation['id']]
    result['result'].update(source_ref=source['id'], observation_ref=observation['id'])
    case.store.db.execute('UPDATE tool_operations SET result=? WHERE operation_key=?',
        (canonical(result), descriptor['original_operation_key']))
    descriptor.update(source_ref=source['id'], observation_ref=observation['id'])


@pytest.mark.parametrize('mutation,code', [
    ('missing_companion', 'invalid_traceback'), ('common_counts', 'invalid_traceback'),
    ('common_input', 'invalid_traceback'), ('legacy_scores', 'invalid_traceback'),
    ('inner_companion', 'invalid_traceback'), ('outer_extra', 'invalid_traceback'),
    ('extra_instance', 'invalid_traceback'), ('axis_basis', 'invalid_traceback'),
    ('outer_version', 'invalid_traceback'), ('provider', 'alignment_operand_mismatch'),
    ('native_identity', 'alignment_operand_mismatch'), ('descriptor_format', 'alignment_operand_mismatch'),
    ('native_file_identity', 'alignment_operand_mismatch'), ('wrong_grading_aux', 'alignment_operand_mismatch'),
])
def test_retained_v2_operand_rejects_format_custody_and_companion_forgeries(retained_operand_case, monkeypatch, mutation, code):
    case = retained_operand_case
    descriptor, body, fixed, moving, orientation = _retained_alignment(case, 'global', 2)
    if mutation == 'descriptor_format':
        descriptor['grading_file']['format'] = 'tool_grading_artifact_v1'
    elif mutation == 'native_file_identity':
        raw = case.store.get_artifact(descriptor['native_file']['artifact_ref']) + b'\n'
        artifact = case.store.artifact(raw, 'application/json')
        metadata = case.store.get(artifact)
        descriptor['native_file'] = {'artifact_ref': artifact, 'sha256': metadata['sha256'],
            'byte_length': metadata['size'], 'format': 'biopython_pairwise_json'}
    elif mutation == 'wrong_grading_aux':
        descriptor['grading_file'] = deepcopy(case.data['alignments']['global']['descriptor']['grading_file'])
    else:
        if mutation == 'missing_companion': del body['correspondence']
        elif mutation == 'common_counts': body['correspondence']['instances'][0]['components']['rows'][0]['counts']['paired_positions'] = 3
        elif mutation == 'common_input': body['correspondence']['instances'][0]['sheet']['operands']['query']['length'] = 5
        elif mutation == 'legacy_scores': body['grading']['scores']['paired_positions'] = 3
        elif mutation == 'inner_companion': body['grading']['correspondence'] = deepcopy(body['correspondence'])
        elif mutation == 'outer_extra': body['unexpected'] = 1
        elif mutation == 'extra_instance': body['correspondence']['instances'].append(deepcopy(body['correspondence']['instances'][0]))
        elif mutation == 'axis_basis': body['correspondence']['instances'][0]['axis_basis'] = 'reported'
        elif mutation == 'outer_version': body['schema'] = 'tool_grading_artifact_v3'
        elif mutation == 'provider': body['provider'] = 'different-provider'
        elif mutation == 'native_identity': body['native_artifact_ref'] = 'artifact_' + '0' * 64
        _forged_grading(case, descriptor, body)
    case.ports.alignment = deepcopy(descriptor)
    _read_only(case, monkeypatch)
    with pytest.raises(ProteinStructureOperandError) as caught:
        operands.authenticate_selected_alignment(case.store, case.context, descriptor,
            fixed=fixed, moving=moving, orientation=orientation, returns=case.ports)
    assert str(caught.value) == code
    assert caught.value.issue['stage'] == 'correspondence'
    assert caught.value.issue['field'] == ('traceback' if code == 'invalid_traceback' else 'alignment')
    _unchanged(case)


@pytest.mark.parametrize('field', ['native_file', 'grading_file'])
@pytest.mark.parametrize('changed', [False, True])
def test_retained_operand_files_preserve_missing_and_digest_failures(retained_operand_case, monkeypatch, field, changed):
    case = retained_operand_case
    descriptor, _, fixed, moving, orientation = _retained_alignment(case, 'global', 2)
    file = descriptor[field]
    path = case.store.path / 'artifacts' / file['sha256'][:2] / file['sha256']
    if changed: path.write_bytes(path.read_bytes() + b'\n')
    else: path.unlink()
    _read_only(case, monkeypatch)
    with pytest.raises(ProteinStructureOperandError) as caught:
        operands.authenticate_selected_alignment(case.store, case.context, descriptor,
            fixed=fixed, moving=moving, orientation=orientation, returns=case.ports)
    assert str(caught.value) == ('input_digest_mismatch' if changed else 'retained_artifact_missing')
    assert caught.value.issue['stage'] == 'input' and caught.value.issue['field'] == 'file_identity'
    _unchanged(case)
