"""Actual own-A104 saved-descriptor refusals; no substituted constructors.

The callback runs only after the ordinary constructor and original caller
projectors exist. Only the selected saved operand is altered in each case.
All original returned/raised records remain observable on the pending baseline.
"""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from .saved_binding_boundaries import diagnose, forbidden, module
from .api_cases import error_record

REPRESENTATIVES = {
    'execution_job_submission/api_job_execution': 'execution',
    'execution_progress_assessment': 'monitor',
    'hpc_work_planning': 'hpc',
    'published_evidence_assessment': 'literature',
    'scientific_process': 'scientific',
}
COMMON = ('changed_version', 'foreign_binding_id', 'extra_configuration',
          'duplicate_path', 'wrong_journal_store', 'empty_run_id')
SPECIFIC = {
    'execution': ('missing_directory', 'missing_projector', 'invalid_projector'),
    'monitor': ('missing_backend', 'missing_projector', 'invalid_projector'),
    'hpc': ('missing_directory', 'missing_projector', 'invalid_projector'),
    'literature': ('changed_fingerprint',),
    'scientific': ('missing_directory', 'changed_fingerprint', 'changed_library',
                   'changed_tool_library'),
}
CASES = tuple((home, kind, case) for home, kind in REPRESENTATIVES.items()
              for case in (*COMMON, *SPECIFIC[kind]))


def expected_failure(home, kind, case, role):
    code, reference = 'unavailable_binding', home
    if case in {'changed_version', 'changed_fingerprint', 'duplicate_path'}:
        code = 'identity_conflict'
        reference = 'episode_bindings' if case == 'duplicate_path' else home
    if case == 'changed_version' and kind == 'scientific':
        code = 'unavailable_binding'
    if case in {'changed_library', 'changed_tool_library'}:
        code = 'identity_conflict'
    if case == 'foreign_binding_id': reference = 'foreign_axis/not_an_owner'
    if case == 'wrong_journal_store': code, reference = 'identity_conflict', 'journal.store'
    if case == 'empty_run_id': reference = 'journal.run_id'
    if case == 'missing_backend': reference = 'execution_backend'
    if case in {'missing_projector', 'invalid_projector'}: reference = role
    return {'code': code, 'affected_refs': [reference],
            'diagnostic_ref': None, 'partial_record_refs': []}


def diagnose_with_controls(directory, retain):
    def inspect_constructed(home, kind, before, services, original):
        if home not in REPRESENTATIVES: return
        assert REPRESENTATIVES[home] == kind
        for case in (*COMMON, *SPECIFIC[kind]):
            kwargs = dict(original)
            kwargs['descriptors'] = deepcopy(original['descriptors'])
            descriptor, = kwargs['descriptors']
            role = before.roles[0]
            if case == 'changed_version': descriptor['version'] = 'unrecognized_saved_version'
            elif case == 'foreign_binding_id': descriptor['binding_id'] = 'foreign_axis/not_an_owner'
            elif case == 'extra_configuration': descriptor['configuration']['unknown_parameter'] = True
            elif case == 'duplicate_path': kwargs['descriptors'].append(deepcopy(descriptor))
            elif case == 'wrong_journal_store':
                kwargs['journal'] = SimpleNamespace(store=object(), run_id=original['journal'].run_id)
            elif case == 'empty_run_id':
                kwargs['journal'] = SimpleNamespace(store=original['store'], run_id='')
            elif case == 'missing_directory': kwargs['directory'] = None
            elif case == 'missing_backend': kwargs['execution_backend'] = None
            elif case == 'missing_projector': kwargs['role_credit_bindings'] = {}
            elif case == 'invalid_projector':
                kwargs['role_credit_bindings'] = {role: {
                    'definition': original['role_credit_bindings'][role]['definition'],
                    'project': None}}
            elif case == 'changed_fingerprint':
                assert 'implementation_sha256' in descriptor
                descriptor['implementation_sha256'] = (
                    '0' if descriptor['implementation_sha256'][0] != '0' else '1') + descriptor['implementation_sha256'][1:]
            elif case in {'changed_library', 'changed_tool_library'}:
                key = 'library' if case == 'changed_library' else 'tool_library'
                # A changed recorded library, never changed owned files.
                descriptor['configuration'][key] = {'unexpected_saved_library': True}
            else: raise AssertionError('undeclared_restoration_control')
            row = {'boundary': 'control:' + home + ':' + case,
                'original_descriptor': deepcopy(original['descriptors'][0]),
                'supplied_descriptors': deepcopy(kwargs['descriptors']),
                'expected_failure': expected_failure(home, kind, case, role),
                'capability_reads_forbidden': kind == 'execution'}
            try:
                # A rejected descriptor must never reach capability reads.
                if kind == 'execution':
                    with patch.object(type(before), 'capabilities', forbidden):
                        module('episode_composition').compose_episode_bindings(services, **kwargs)
                else:
                    module('episode_composition').compose_episode_bindings(services, **kwargs)
                row['status'] = 'returned'
            except Exception as error:
                row.update(status='raised', error=error_record(error))
            retain(row)
    diagnose(directory, retain, inspect_constructed=inspect_constructed)
