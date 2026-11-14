"""Own-A104 job validation over retained controls; no producer is executed.

The v2 jobs are untouched original049 plan/intent payloads. The v1 controls
are explicit test-only selections of their raw-input declarations, not saved
v1 actions or new scientific evidence. Software pins are validated as data.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tarfile

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode.episodic_workflow.root.a104.library import native_fluorescence_contracts as contracts

OPERATIONS = ('perform_facs_cell_sorting', 'analyze_cytokine_production_in_cd4_tcells')
FIXTURES = Path(__file__).parent / 'fixtures/fluorescence_original049'


def archived_job(operation, kind):
    manifest = json.loads((FIXTURES / 'manifest.json').read_bytes())
    case, = [row for row in manifest['cases'] if row['operation'] == operation]
    archive = FIXTURES / case['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == case['archive_sha256']
    intents = sorted(name for name in case['files'] if '/native-fluorescence-actions/' in name
        and name.endswith('/intent.json') and '/worker/' not in name)
    assert len(intents) == 3
    name = 'original-native-plan.json' if kind == 'plan' else intents[int(kind[-1])]
    with tarfile.open(archive, 'r:gz') as stream:
        member = stream.getmember(name)
        assert member.isfile() and not member.issym() and not member.islnk()
        raw = stream.extractfile(member).read()
    pin = case['files'][name]
    assert len(raw) == pin['size_bytes'] and hashlib.sha256(raw).hexdigest() == pin['sha256']
    record = json.loads(raw)
    requested = record['requested_job'] if kind == 'plan' else record['target']['assignment']['requested_job']
    value = requested['native_fluorescence']
    assert value['operation'] == operation and value['version'] == 'native_fluorescence_job_v2'
    return value, {'archive_sha256': case['archive_sha256'], 'member': name, 'member_sha256': pin['sha256']}


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('kind', ('plan', 'intent0', 'intent1', 'intent2'))
def test_original_v2_job_and_unknown_field_boundary(operation, kind, record_property):
    value, custody = archived_job(operation, kind)
    before = deepcopy(value)
    record_property('original_control', json.dumps(custody, sort_keys=True))
    result = contracts.validate_fluorescence_job(value)
    assert result == before == value and result is not value
    Draft202012Validator(contracts.JOB_V2_SCHEMA).validate(value)
    for name in ('preparations', 'report_inputs'):
        missing = deepcopy(value)
        del missing[name]
        with pytest.raises(ValueError, match='^invalid_fluorescence_contract$'):
            contracts.validate_fluorescence_job(missing)
    extra = deepcopy(value)
    extra['undeclared_operation'] = True
    with pytest.raises(ValueError, match='^invalid_fluorescence_contract$'):
        contracts.validate_fluorescence_job(extra)
    assert value == before


@pytest.mark.parametrize('operation', OPERATIONS)
def test_v1_raw_selection_still_valid_and_closed(operation):
    original, _ = archived_job(operation, 'plan')
    value = deepcopy(original)
    value['version'] = 'native_fluorescence_job_v1'
    del value['preparations'], value['report_inputs']
    raw_input, = value['inputs']
    assert raw_input['sample']['associations'] == []
    assert all(channel['analyte'] is None for channel in raw_input['channels'])
    assert all(raw_input['domain'][name]['parameters_file'] is None
        for name in ('compensation', 'transformation'))
    basis = raw_input['domain']['comparison_basis']['evidence_file']
    value['support_inputs'] = [row for row in value['support_inputs'] if row['file'] == basis]
    assert len(value['support_inputs']) == 1
    value['parameters']['intensity_requests'] = [row for row in value['parameters']['intensity_requests']
        if row['domain_key'] == raw_input['domain']['key']]
    value['parameters']['native_comparison_requests'] = []
    before = deepcopy(value)
    assert contracts.validate_fluorescence_job(value) == value == before
    Draft202012Validator(contracts.JOB_SCHEMA).validate(value)
    for name in ('preparations', 'report_inputs', 'undeclared_operation'):
        changed = deepcopy(value)
        changed[name] = []
        with pytest.raises(ValueError, match='^invalid_fluorescence_contract$'):
            contracts.validate_fluorescence_job(changed)
    assert value == before


@pytest.mark.parametrize('operation', OPERATIONS)
@pytest.mark.parametrize('fault', ('preparation_index', 'report_profile'))
def test_selected_v2_scientific_declarations_remain_validated(operation, fault):
    value, _ = archived_job(operation, 'plan')
    # First prove that this complete retained operand reaches the scientific
    # declaration checks. A generic closed-key rejection is not this test.
    assert contracts.validate_fluorescence_job(value) == value
    changed = deepcopy(value)
    if fault == 'preparation_index':
        changed['preparations'][0]['input']['index'] = len(value['inputs'])
    else:
        changed['report_inputs'][0]['profile'] = 'undeclared_report_profile'
    with pytest.raises(ValueError) as caught:
        contracts.validate_fluorescence_job(changed)
    assert str(caught.value) != 'invalid_fluorescence_contract'
    assert changed != value


def test_nested_v2_schema_edit_cannot_change_v1():
    before = deepcopy(contracts.JOB_SCHEMA)
    selected = contracts.JOB_V2_SCHEMA['properties']['parameters']['properties']['native_comparison_requests']
    assert '__test_isolation__' not in selected
    try:
        selected['__test_isolation__'] = True
        assert contracts.JOB_SCHEMA == before
    finally:
        del selected['__test_isolation__']
    assert contracts.JOB_SCHEMA == before
