"""Prepared resource/input boundaries inside the coordinator's bounded runner.

Capability cases use declared software and synthetic input shapes without a
native execution. Custody cases use actual Store records and the existing
episode receipt fixture; they do not claim full Workflow or installed science.
"""
from copy import deepcopy
from pathlib import Path

import pytest

from fluorescence_flowio_test_support import require_bounded_runtime

require_bounded_runtime()

from gene_annotation_episode.fluorescence_execution_common import canonical, identity
from gene_annotation_episode.native_fluorescence_contracts import (
    OPERATIONS, PREPARATION_METHODS, REPORT_PROFILES, fluorescence_environment,
    requested_job_from_fluorescence,
)
from gene_annotation_episode.practical_execution_operations import LocalPracticalOperations
from native_fluorescence_prepared_test_support import (
    SCALE, declared_software, file_input, selected_preparation,
)
from test_fluorescence_episode_routing import _request, selected
from test_fluorescence_local_routing import assignment_and_configuration


CAPABILITY_ERROR = 'native_fluorescence_prepared_capabilities_not_bound'
PARSER_ERROR = 'native_fluorescence_parser_not_bound'
SELECTION_ERROR = 'native_fluorescence_operation_mode_software_not_bound'


def _request_for(assignment, chosen):
    return requested_job_from_fluorescence(chosen, environment=fluorescence_environment(
        chosen['software'], attempt_directory=str(Path(assignment['workspace']) / 'caller-temporaries')))


def _binding(chosen, *, parsers=None, methods=PREPARATION_METHODS, profiles=REPORT_PROFILES):
    return dict(version='native_fluorescence_binding_v2',
        **{key: deepcopy(chosen[key]) for key in ('operation', 'mode', 'software')},
        parsers=sorted({row['parser'] for row in chosen['inputs']}) if parsers is None else list(parsers),
        preparation_methods=list(methods), report_profiles=list(profiles))


def _capability_case(directory, operation, *, methods=PREPARATION_METHODS, profiles=REPORT_PROFILES):
    assignment, configuration = assignment_and_configuration(directory, operation=operation,
        parsers=('fcs_encoded', 'csv'))
    chosen = deepcopy(assignment['requested_job']['native_fluorescence'])
    chosen.update(version='native_fluorescence_job_v2', preparations=[], report_inputs=[],
        software=declared_software(fcs=True))
    # These are declaration-only bytes. No decoder or preparation is called.
    chosen['inputs'][0]['channels'][0]['native_name'] = 'A'
    basis = file_input(directory, 'declared-basis.txt', b'declared synthetic basis', 'text')
    chosen['support_inputs'].append(basis)
    chosen['inputs'][0]['domain']['comparison_basis'] = dict(key='declared-basis', evidence_file=basis['file'])
    for index, method in enumerate(methods):
        selected_preparation(chosen, directory, method=method, key=f'prepared-{index}',
            parent_kind='preparation' if index else 'event_input', parent_index=max(0, index - 1))
    for index, profile in enumerate(profiles):
        supplied = file_input(directory, f'declared-report-{index}.txt',
            ('declaration-only ' + profile).encode(), 'text')
        chosen['report_inputs'].append(dict(**supplied, source_key=f'report-{index}',
            profile=profile, fields=[], association_file=None))
    assignment['requested_job'] = _request_for(assignment, chosen)
    configuration['native_fluorescence'] = [_binding(chosen)]
    return assignment, configuration


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('methods,profiles', [
    ((), ()), ((SCALE,), ()), ((), (REPORT_PROFILES[0],)),
    ((SCALE,), (REPORT_PROFILES[0],)), (PREPARATION_METHODS, REPORT_PROFILES),
])
@pytest.mark.parametrize('declared', ['exact', 'superset'])
def test_v2_accepts_complete_single_binding_subsets(tmp_path, operation, methods, profiles, declared):
    assignment, configuration = _capability_case(tmp_path, operation, methods=methods, profiles=profiles)
    chosen = assignment['requested_job']['native_fluorescence']
    if declared == 'exact':
        configuration['native_fluorescence'] = [_binding(chosen, methods=methods, profiles=profiles)]
    original = canonical(assignment)
    assert LocalPracticalOperations(configuration).validate_assignment(assignment) is None
    assert canonical(assignment) == original


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('missing', ['preparation', 'report'])
def test_v2_rejects_unbound_selected_capability(tmp_path, operation, missing):
    assignment, configuration = _capability_case(tmp_path, operation)
    row = configuration['native_fluorescence'][0]
    row['preparation_methods' if missing == 'preparation' else 'report_profiles'].pop()
    with pytest.raises(ValueError, match='^' + CAPABILITY_ERROR + '$'):
        LocalPracticalOperations(configuration).validate_assignment(assignment)


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('with_additions', [False, True])
def test_v1_binding_cannot_authorize_v2_job(tmp_path, operation, with_additions):
    assignment, configuration = _capability_case(tmp_path, operation,
        methods=PREPARATION_METHODS if with_additions else (),
        profiles=REPORT_PROFILES if with_additions else ())
    row = configuration['native_fluorescence'][0]
    for key in ('version', 'preparation_methods', 'report_profiles'):
        row.pop(key)
    with pytest.raises(ValueError, match='^' + CAPABILITY_ERROR + '$'):
        LocalPracticalOperations(configuration).validate_assignment(assignment)


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('split', ['methods', 'profiles', 'methods_profiles', 'parsers',
                                  'parser_capabilities', 'legacy_parsers'])
def test_v2_never_unions_alternative_bindings(tmp_path, operation, split):
    assignment, configuration = _capability_case(tmp_path, operation)
    complete = configuration['native_fluorescence'][0]
    first, second = deepcopy(complete), deepcopy(complete)
    expected = CAPABILITY_ERROR
    if split == 'methods':
        first['preparation_methods'] = list(PREPARATION_METHODS[:1])
        second['preparation_methods'] = list(PREPARATION_METHODS[1:])
    elif split == 'profiles':
        first['report_profiles'] = list(REPORT_PROFILES[:1])
        second['report_profiles'] = list(REPORT_PROFILES[1:])
    elif split == 'methods_profiles':
        first['report_profiles'], second['preparation_methods'] = [], []
    elif split == 'parsers':
        first['parsers'], second['parsers'] = ['csv'], ['fcs_encoded']
        expected = PARSER_ERROR
    elif split == 'parser_capabilities':
        first['preparation_methods'], first['report_profiles'] = [], []
        second['parsers'] = ['fcs_encoded']
    else:
        for key in ('version', 'preparation_methods', 'report_profiles'):
            first.pop(key)
        second['parsers'] = ['fcs_encoded']
    configuration['native_fluorescence'] = [first, second]
    with pytest.raises(ValueError, match='^' + expected + '$'):
        LocalPracticalOperations(configuration).validate_assignment(assignment)
    configuration['native_fluorescence'].append(complete)
    assert LocalPracticalOperations(configuration).validate_assignment(assignment) is None


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('mismatch', ['operation', 'software', 'parser'])
def test_v2_preserves_existing_selection_and_parser_failures(tmp_path, operation, mismatch):
    assignment, configuration = _capability_case(tmp_path, operation)
    row = configuration['native_fluorescence'][0]
    if mismatch == 'operation':
        row['operation'] = next(value for value in OPERATIONS if value != operation)
    elif mismatch == 'software':
        row['software']['python_version'] = 'different declared interpreter'
    else:
        row['parsers'] = ['csv']
    expected = PARSER_ERROR if mismatch == 'parser' else SELECTION_ERROR
    with pytest.raises(ValueError, match='^' + expected + '$'):
        LocalPracticalOperations(configuration).validate_assignment(assignment)


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('parsers', [('csv',), ('fcs_encoded',), ('csv', 'table_snapshot')])
@pytest.mark.parametrize('binding_version', ['legacy', 'v2'])
def test_legacy_v1_selection_behavior_is_preserved(tmp_path, operation, parsers, binding_version):
    assignment, configuration = assignment_and_configuration(tmp_path, operation=operation, parsers=parsers)
    if binding_version == 'v2':
        chosen = assignment['requested_job']['native_fluorescence']
        chosen['software'] = declared_software(fcs='fcs_encoded' in parsers)
        assignment['requested_job'] = _request_for(assignment, chosen)
        configuration['native_fluorescence'] = [_binding(chosen, methods=(), profiles=())]
    original = canonical(assignment)
    assert LocalPracticalOperations(configuration).validate_assignment(assignment) is None
    assert canonical(assignment) == original


def _received_reports(fixture, operation, *, receive=True):
    chosen = deepcopy(fixture.selected)
    chosen.update(version='native_fluorescence_job_v2', operation=operation,
        preparations=[], report_inputs=[], software=declared_software(fcs=False))
    for index, profile in enumerate(REPORT_PROFILES):
        raw = ('synthetic report custody fixture ' + profile).encode()
        reference = fixture.store.artifact(raw, 'text/plain')
        file = identity(raw, format='text')
        assert reference == file['artifact_ref']
        path = str(fixture.store.path / 'artifacts' / file['sha256'][:2] / file['sha256'])
        chosen['report_inputs'].append(dict(file=file, path=path, source_key=f'raw-report-{index}',
            profile=profile, fields=[], association_file=None))
        if receive:
            fixture.ledger.receive(fixture.root.episode_id, [reference], kind='own_action')
    assignment = {**fixture.assignment, 'requested_job': _request(fixture, chosen)}
    versions = [*deepcopy(fixture.versions), *[dict(reference=row['file']['artifact_ref'],
        version=None, content_sha256=row['file']['sha256']) for row in chosen['report_inputs']]]
    return assignment, versions


@pytest.mark.parametrize('operation', OPERATIONS)
def test_received_report_versions_use_metadata_without_byte_reads_or_new_records(selected, monkeypatch, operation):
    f = selected
    assignment, versions = _received_reports(f, operation)
    reports = assignment['requested_job']['native_fluorescence']['report_inputs']
    report_refs = [row['file']['artifact_ref'] for row in reports]
    assert f.owner._fluorescence_inputs(f.root, assignment) == [*f.input_refs, *report_refs]
    assert f.store.reference_subset(report_refs, f.scope) == []
    for path in [*f.input_paths, *[Path(row['path']) for row in reports]]:
        path.unlink()
    monkeypatch.setattr(f.store, 'get_artifact', lambda *_: pytest.fail('input versions read scientific bytes'))
    before = list(f.store.db.iterdump())
    assert f.owner._versions(versions, f.scope, context=f.root, fluorescence_assignments=[assignment]) is None
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize('operation', OPERATIONS)
def test_unreceived_reports_fail_before_input_version_admission(selected, operation):
    f = selected
    assignment, versions = _received_reports(f, operation, receive=False)
    before = list(f.store.db.iterdump())
    with pytest.raises(ValueError, match='^fluorescence_input_not_received$'):
        f.owner._versions(versions, f.scope, context=f.root, fluorescence_assignments=[assignment])
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('mismatch', ['version_hash', 'version_revision', 'selected_size',
                                    'stored_hash', 'stored_size', 'selected_path'])
def test_report_versions_reject_wrong_hash_size_version_or_path(selected, operation, mismatch):
    f = selected
    assignment, versions = _received_reports(f, operation)
    chosen = deepcopy(assignment['requested_job']['native_fluorescence'])
    report = chosen['report_inputs'][0]
    version = versions[len(f.versions)]
    expected = 'fluorescence_input_artifact_metadata_mismatch'
    if mismatch == 'version_hash':
        version['content_sha256'] = 'f' * 64
        expected = 'execution_input_version_conflict'
    elif mismatch == 'version_revision':
        version['version'] = 'unrecorded-revision'
        expected = 'execution_input_version_conflict'
    elif mismatch == 'selected_size':
        report['file']['size_bytes'] += 1
    elif mismatch == 'stored_hash':
        f.store.db.execute('UPDATE artifacts SET sha256=? WHERE id=?', ('0' * 64, report['file']['artifact_ref']))
    elif mismatch == 'stored_size':
        f.store.db.execute('UPDATE artifacts SET size=size+1 WHERE id=?', (report['file']['artifact_ref'],))
    else:
        report['path'] = str(f.directory / 'unselected-report.txt')
        expected = 'fluorescence_input_selected_path_mismatch'
    assignment['requested_job'] = _request(f, chosen)
    before = list(f.store.db.iterdump())
    with pytest.raises(ValueError, match='^' + expected + '$'):
        f.owner._versions(versions, f.scope, context=f.root, fluorescence_assignments=[assignment])
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('undeclared', ['report', 'other_artifact', 'assignment'])
def test_report_input_map_never_broadens_generic_artifact_scope(selected, operation, undeclared):
    f = selected
    assignment, versions = _received_reports(f, operation)
    if undeclared == 'report':
        chosen = deepcopy(assignment['requested_job']['native_fluorescence'])
        chosen['report_inputs'].pop()
        assignment['requested_job'] = _request(f, chosen)
    elif undeclared == 'other_artifact':
        reference = f.store.artifact(b'received but not selected by this fluorescence job', 'text/plain')
        f.ledger.receive(f.root.episode_id, [reference], kind='own_action')
        versions.append(dict(reference=reference, version=None, content_sha256=reference[9:]))
    before = list(f.store.db.iterdump())
    with pytest.raises(ValueError, match='^execution_input_outside_assigned_scope$'):
        f.owner._versions(versions, f.scope, context=f.root,
            fluorescence_assignments=[] if undeclared == 'assignment' else [assignment])
    assert list(f.store.db.iterdump()) == before


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('substitution', ['version_only', 'selected_report'])
def test_received_raw_report_does_not_authorize_unreceived_derived_result(selected, monkeypatch, operation, substitution):
    f = selected
    assignment, versions = _received_reports(f, operation)
    derived_ref = f.sheet['artifact_ref']
    # Declare ownership through the existing fixture port; the actual received
    # typed-return authority still decides access. No native result is claimed.
    monkeypatch.setattr(f.owner.native_fluorescence_results, 'owns_reference',
        lambda reference: reference == derived_ref)
    assert f.owner._fluorescence_reference_access(f.root, derived_ref, 'artifact') is False
    assert f.owner._fluorescence_inputs(f.root, assignment) == [row['reference'] for row in versions]
    if substitution == 'version_only':
        versions.append(dict(reference=derived_ref, version=None, content_sha256=f.sheet['sha256']))
    else:
        chosen = deepcopy(assignment['requested_job']['native_fluorescence'])
        chosen['report_inputs'][0]['file'] = deepcopy(f.sheet)
        chosen['report_inputs'][0]['path'] = str(f.store.path / 'artifacts' /
            f.sheet['sha256'][:2] / f.sheet['sha256'])
        assignment['requested_job'] = _request(f, chosen)
    before = list(f.store.db.iterdump())
    with pytest.raises(ValueError, match='^fluorescence_input_protected_reference_denied$'):
        f.owner._versions(versions, f.scope, context=f.root, fluorescence_assignments=[assignment])
    assert list(f.store.db.iterdump()) == before
