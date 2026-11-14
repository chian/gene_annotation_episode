"""Saved fluorescence identity and current-layout controls without native execution.

The requested job is an untouched authenticated original049 record. Worker
module controls use its original intent with an explicitly selected two-field
policy declaration; that derivative is not claimed to be a saved execution.
The original three-field historical policy is tested separately as rejected by
the original selected producer. No decoder, provider, or worker is dispatched.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

OLD_DRIVER = 'gene_annotation_episode.episodic_workflow.root.library.native_fluorescence_driver'
NEW_DRIVER = 'gene_annotation_episode.episodic_workflow.root.library.native_fluorescence_driver'
OLD_WORKER = 'gene_annotation_episode.episodic_workflow.root.library.fluorescence_result_worker'
NEW_WORKER = 'gene_annotation_episode.episodic_workflow.root.library.fluorescence_result_worker'
ORIGINAL_CASES = ('historical_software', 'historical_request',
                  'historical_driver_pin_required', 'historical_worker_control',
                  'historical_worker_pin_required', 'historical_unsupported_policy',
                  'unknown_driver_rejected', 'unknown_worker_rejected')
CASES = (*ORIGINAL_CASES, 'current_software', 'current_request',
         'current_driver_pin_required', 'current_worker_control',
         'current_worker_pin_required', 'mixed_old_driver_rejected',
         'mixed_old_worker_rejected', 'direct_extra_validator_scope')
FIXTURES = Path(__file__).parent / 'fixtures/fluorescence_module_identity'


def retained(name):
    provenance = json.loads((FIXTURES / 'provenance.json').read_bytes())
    raw = (FIXTURES / name).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == provenance['files'][name]['sha256']
    return json.loads(raw)


def rejected(function, value, code):
    before = deepcopy(value)
    try:
        function(value)
    except ValueError as error:
        assert str(error) == code, (str(error), code)
    else:
        raise AssertionError('invalid module/source identity was accepted')
    assert value == before


def request(contracts, *, current):
    value = retained('original-native-plan.json')['requested_job']
    assert value['argv'][4] == OLD_DRIVER
    if not current:
        return value
    value = deepcopy(value)
    software = value['native_fluorescence']['software']
    prefix = Path(software['module_root']) / 'gene_annotation_episode'
    library = Path(contracts.__file__).parent
    for pin in software['implementation_files']:
        relative = Path(pin['path']).relative_to(prefix)
        if relative.as_posix() == '__init__.py':
            continue
        source = library / relative
        raw = source.read_bytes()
        pin.update(path=str(prefix / 'episodic_workflow/root/library' / relative),
                   sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
    # This is a declared current-layout control, not a newly executed producer.
    return contracts.requested_job_from_fluorescence(
        value['native_fluorescence'], environment=value['environment'])


def worker(contracts, preparation, *, current):
    value = deepcopy(retained('original-worker-execution.json')['intent'])
    assert value['command'][4] == OLD_WORKER
    assert value['policy'] == dict(memory_bytes=21474836480,
                                  scratch_bytes=4294967296, wall_seconds=None)
    # Preserve the actual inherited unsupported policy separately; the module
    # boundary control uses the already-supported original two-field profile.
    value['policy'] = deepcopy(contracts.HISTORICAL_POLICY)
    if current:
        from gene_annotation_episode.episodic_workflow.root.library.native_source_snapshot import _source_closure
        repository = Path(contracts.__file__).resolve().parents[4]
        sources = _source_closure(repository, [NEW_WORKER])
        assert sources and 'gene_annotation_episode.episodic_workflow.root.library.fluorescence_result_worker' in sources
        frozen_root = Path(value['plan']['directory']) / 'source_snapshot'
        value['source_pins'] = []
        for name, source in sorted(sources.items()):
            raw = source.read_bytes()
            value['source_pins'].append(dict(
                path=str(frozen_root / (name.replace('.', '/') + '.py')),
                sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw)))
        value['command'][4] = NEW_WORKER
        value['policy'] = deepcopy(contracts.POLICY)
    return value


def check(name, contracts, preparation):
    assert name in CASES
    if name == 'direct_extra_validator_scope':
        from gene_annotation_episode.episodic_workflow.root.library.native_fluorescence_prepared_contracts import validate_selected_software
        original = retained('original-native-plan.json')['requested_job']['native_fluorescence']['software']
        value = deepcopy(original)
        value['implementation_files'] = [row for row in value['implementation_files']
                                        if row['path'].endswith('/native_fluorescence_prepared_contracts.py')]
        before = deepcopy(value)
        assert len(value['implementation_files']) == 1
        assert validate_selected_software(value, methods=[], profiles=[]) is None
        assert value == before
        return
    if 'worker' in name or name == 'historical_unsupported_policy':
        current = name.startswith('current') or name.startswith('mixed')
        value = worker(contracts, preparation, current=current)
        if name == 'historical_unsupported_policy':
            value = retained('original-worker-execution.json')['intent']
        elif name.endswith('pin_required'):
            relative = value['command'][4].replace('.', '/') + '.py'
            value['source_pins'] = [row for row in value['source_pins']
                                    if not row['path'].endswith('/' + relative)]
        elif name == 'unknown_worker_rejected':
            value['command'][4] = 'gene_annotation_episode.unassigned_worker'
        elif name == 'mixed_old_worker_rejected':
            value['command'][4] = OLD_WORKER
        before = deepcopy(value)
        validate = lambda item: preparation._validate_intent(item, item['plan'])
        if name.endswith('control'):
            result = validate(value)
            assert result == before == value and result is not value
            assert result['source_pins'] == before['source_pins']
        else:
            code = ('fluorescence_original_allocation_mismatch'
                    if name == 'historical_unsupported_policy' else 'worker_execution_mismatch')
            rejected(validate, value, code)
        return
    current = name.startswith('current') or name.startswith('mixed')
    value = request(contracts, current=current)
    if name.endswith('software'):
        software = value['native_fluorescence']['software']
        before = deepcopy(software)
        result = contracts.validate_fluorescence_software(software)
        assert result == before == software and result is not software
    elif name.endswith('request'):
        before = deepcopy(value)
        result = contracts.validate_fluorescence_requested_job(value)
        assert result == before == value and result is not value
        assert result['argv'][4] == (NEW_DRIVER if current else OLD_DRIVER)
    elif name.endswith('pin_required'):
        software = value['native_fluorescence']['software']
        software['implementation_files'] = [row for row in software['implementation_files']
                                           if not row['path'].endswith('/native_fluorescence_driver.py')]
        rejected(contracts.validate_fluorescence_software, software,
                 'fluorescence_implementation_closure_missing')
    else:
        value['argv'][4] = OLD_DRIVER if name.startswith('mixed') else 'gene_annotation_episode.unassigned_driver'
        rejected(contracts.validate_fluorescence_requested_job, value,
                 'fluorescence_requested_job_mismatch')
