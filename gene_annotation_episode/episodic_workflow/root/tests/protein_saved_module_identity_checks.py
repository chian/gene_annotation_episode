"""Contract checks using an actual retained protein producer record.

These checks validate producer/command identities, not scientific calculations,
source availability at an old execution location, or native execution.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

HISTORICAL = ('gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_driver',
              'gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_worker')
CURRENT = ('gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_driver',
           'gene_annotation_episode.episodic_workflow.root.library.native_protein_structure_worker')
ORIGINAL_CASES = ('historical_roundtrip', 'historical_pin_required',
                  'historical_command', 'unknown_modules_rejected')
CASES = (*ORIGINAL_CASES, 'current_roundtrip', 'current_pin_required',
         'current_command', 'mixed_old_driver_rejected', 'mixed_old_worker_rejected')


def saved():
    return json.loads((Path(__file__).parent / 'fixtures/protein_module_identity/retained_software.json').read_bytes())


def current():
    value = saved()
    value['driver_module'], value['worker_module'] = CURRENT
    library = Path(__file__).parent.parent / 'library'
    value['implementation_files'] = [
        {'module': name, 'sha256': hashlib.sha256(
            (library / (name.rsplit('.', 1)[1] + '.py')).read_bytes()).hexdigest()}
        for name in CURRENT]
    return value


def rejected(function, value, expected):
    original = deepcopy(value)
    try:
        function(value)
    except ValueError as error:
        assert str(error) == expected, (str(error), expected)
    else:
        raise AssertionError('invalid module identity was accepted')
    assert value == original


def check(name, contracts):
    assert name in CASES
    historical = name.startswith('historical')
    value = saved() if historical or name == 'unknown_modules_rejected' else current()
    original = deepcopy(value)
    if name.endswith('roundtrip'):
        result = contracts.validate_protein_structure_software(value)
        assert result == original == value and result is not value
        assert result['implementation_files'] == original['implementation_files']
    elif name.endswith('pin_required'):
        value['implementation_files'] = [row for row in value['implementation_files']
                                         if row['module'] != value['driver_module']]
        rejected(contracts.validate_protein_structure_software, value, 'software_identity_mismatch')
    elif name.endswith('command'):
        qualified = contracts.validate_protein_structure_software(value)
        plan = {'requested_job': {'native_protein_structure': {'software': qualified}},
                'identity': {'execution_id': '/retained-protein-operation/native.json'}}
        frozen = deepcopy(plan)
        assert contracts.driver_argv(plan) == [value['python_executable'], '-B', '-m',
            value['driver_module'], '/retained-protein-operation/protein-structure-plan.json']
        assert plan == frozen and value == original
    elif name == 'unknown_modules_rejected':
        value['driver_module'] = 'gene_annotation_episode.unassigned_driver'
        value['worker_module'] = 'gene_annotation_episode.unassigned_worker'
        value['implementation_files'] += [
            {'module': value[key], 'sha256': '0' * 64} for key in ('driver_module', 'worker_module')]
        rejected(contracts.validate_protein_structure_software, value, 'invalid_schema')
    else:
        key, module = (('driver_module', HISTORICAL[0]) if name == 'mixed_old_driver_rejected'
                       else ('worker_module', HISTORICAL[1]))
        value[key] = module
        value['implementation_files'].append({'module': module, 'sha256': '0' * 64})
        rejected(contracts.validate_protein_structure_software, value, 'invalid_schema')
