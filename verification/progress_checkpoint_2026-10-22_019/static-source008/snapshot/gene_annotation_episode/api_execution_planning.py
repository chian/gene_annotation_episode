"""Explicit API duration proposals using the caller's actual HMMER owners.

Preparation/capture belongs to a selected information action. Saved validation
projects only its original closed capture and never reopens current work/history.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
import hashlib
from pathlib import Path

from .communication import plain
from .domain import ContractError, canonical, validate_schema
from .resource_estimation import API_REPORT_ESTIMATE_SCHEMA, ResourceToolEstimator
from .resource_records import INPUT_VERSION_SCHEMA


VERSION = 'hmmer_api_execution_planner_v1'
RESULT_VERSION = 'api_execution_proposal_estimate_v1'
TARGET = 'public.hmmer.search'
CALLABLE = 'execution.estimate'

# Exact scope027 schemas. References are expanded for the actual tool contracts.
_DEFINITIONS = {'api_capture': {'additionalProperties': False,
                 'properties': {'code': {'enum': [None,
                                                  'unsupported_statistics_configuration',
                                                  'history_schema_unavailable',
                                                  'history_unavailable',
                                                  'invalid_statistics']},
                                'execution_classes': {'items': {'$ref': '#/$defs/api_execution_class'},
                                                      'maxItems': 1,
                                                      'type': 'array'},
                                'snapshots': {'items': {'additionalProperties': False,
                                                        'properties': {'data': {'$ref': '#/$defs/api_snapshot_data'},
                                                                       'ref': {'format': 'reference',
                                                                               'type': 'string',
                                                                               'x-reference-namespace': 'execution_expectation'}},
                                                        'required': ['ref', 'data'],
                                                        'type': 'object'},
                                              'maxItems': 1,
                                              'type': 'array'},
                                'status': {'enum': ['available', 'unavailable', 'invalid_statistics']},
                                'version': {'const': 'episode_execution_expectation_binding_v3'}},
                 'required': ['version', 'execution_classes', 'status', 'code', 'snapshots'],
                 'type': 'object'},
 'api_constraints': {'additionalProperties': False,
                     'properties': {'allowed_kinds': {'items': {'minLength': 1, 'type': 'string'},
                                                      'minItems': 1,
                                                      'type': 'array'},
                                    'allowed_resource_ids': {'items': {'minLength': 1, 'type': 'string'},
                                                             'minItems': 1,
                                                             'type': 'array'},
                                    'cpu': {'type': 'null'},
                                    'kind': {'const': 'api'},
                                    'memory_bytes': {'type': 'null'},
                                    'resource_id': {'format': 'reference',
                                                    'type': 'string',
                                                    'x-reference-namespace': 'resource_binding'},
                                    'scratch_bytes': {'type': 'null'},
                                    'wall_seconds': {'type': 'null'}},
                     'required': [],
                     'type': 'object'},
 'api_estimate_input_template': {'additionalProperties': False,
                                 'properties': {'arguments': {'$ref': '#/$defs/hmmer_arguments'},
                                                'constraints': {'$ref': '#/$defs/api_constraints'},
                                                'immutable_input_versions': {'items': {'$ref': '#/$defs/input_version'},
                                                                             'type': 'array'},
                                                'resource_selection': {'$ref': '#/$defs/api_selection',
                                                                       'x-required-bound-const': 'Replace '
                                                                                                 'this '
                                                                                                 'schema '
                                                                                                 'with '
                                                                                                 'const(actual '
                                                                                                 'bound API '
                                                                                                 'selection) '
                                                                                                 'when '
                                                                                                 'constructing '
                                                                                                 'the real '
                                                                                                 'catalog '
                                                                                                 'branch.'},
                                                'tool': {'const': 'public.hmmer.search'}},
                                 'required': ['tool',
                                              'arguments',
                                              'resource_selection',
                                              'constraints',
                                              'immutable_input_versions'],
                                 'type': 'object'},
 'api_estimate_output': {'additionalProperties': False,
                         'properties': {'api_execution_options': {'items': {'$ref': '#/$defs/existing_api_option'},
                                                                  'type': 'array'},
                                        'api_reported_execution_expectations': {'items': {'$ref': '#/$defs/api_capture'},
                                                                                'maxItems': 1,
                                                                                'minItems': 1,
                                                                                'type': 'array'},
                                        'api_reported_execution_forecasts': {'items': {'$ref': '#/$defs/existing_api_report_estimate'},
                                                                             'type': 'array'},
                                        'api_timing_planning_disposition': {'$ref': '#/$defs/forecast_disposition'},
                                        'arguments': {'$ref': '#/$defs/hmmer_arguments'},
                                        'constraints': {'$ref': '#/$defs/api_constraints'},
                                        'immutable_input_versions': {'items': {'$ref': '#/$defs/input_version'},
                                                                     'type': 'array'},
                                        'normalized_arguments': {'$ref': '#/$defs/hmmer_normalized_arguments'},
                                        'request': {'$ref': '#/$defs/hmmer_request'},
                                        'request_sha256': {'pattern': '^[0-9a-f]{64}$', 'type': 'string'},
                                        'resource_selection': {'$ref': '#/$defs/api_selection'},
                                        'scope_sha256': {'pattern': '^[0-9a-f]{64}$', 'type': 'string'},
                                        'tool': {'const': 'public.hmmer.search'},
                                        'version': {'const': 'api_execution_proposal_estimate_v1'}},
                         'required': ['version',
                                      'tool',
                                      'arguments',
                                      'normalized_arguments',
                                      'scope_sha256',
                                      'resource_selection',
                                      'constraints',
                                      'immutable_input_versions',
                                      'request',
                                      'request_sha256',
                                      'api_reported_execution_expectations',
                                      'api_reported_execution_forecasts',
                                      'api_execution_options',
                                      'api_timing_planning_disposition'],
                         'type': 'object'},
 'api_execution_class': {'additionalProperties': False,
                         'properties': {'backend': {'const': 'https'},
                                        'cpu_threads': {'type': 'null'},
                                        'duration_measure': {'const': 'hmmer_reported_search_elapsed_seconds'},
                                        'implementation_sha256': {'type': 'null'},
                                        'memory_bytes': {'type': 'null'},
                                        'parameters_sha256': {'pattern': '^[0-9a-f]{64}$', 'type': 'string'},
                                        'phase': {'const': 'remote_protein_homology_search'},
                                        'query_residues': {'minimum': 1, 'type': 'integer'},
                                        'reference_records': {'type': 'null'},
                                        'reference_residues': {'type': 'null'},
                                        'reference_state': {'const': 'unknown'},
                                        'resource_id': {'minLength': 1, 'type': 'string'},
                                        'scratch_bytes': {'type': 'null'},
                                        'wall_seconds': {'type': 'null'}},
                         'required': ['phase',
                                      'backend',
                                      'resource_id',
                                      'implementation_sha256',
                                      'parameters_sha256',
                                      'memory_bytes',
                                      'scratch_bytes',
                                      'cpu_threads',
                                      'query_residues',
                                      'reference_residues',
                                      'reference_records',
                                      'reference_state',
                                      'duration_measure',
                                      'wall_seconds'],
                         'type': 'object'},
 'api_selection': {'additionalProperties': False,
                   'properties': {'allocation': {'additionalProperties': False,
                                                 'properties': {'cpu': {'type': 'null'},
                                                                'memory_bytes': {'type': 'null'},
                                                                'scratch_bytes': {'type': 'null'},
                                                                'wall_seconds': {'type': 'null'}},
                                                 'required': ['cpu',
                                                              'memory_bytes',
                                                              'scratch_bytes',
                                                              'wall_seconds'],
                                                 'type': 'object'},
                                  'capability_binding_ref': {'format': 'reference',
                                                             'type': 'string',
                                                             'x-reference-namespace': 'execution_registry'},
                                  'kind': {'const': 'api'},
                                  'resource_id': {'format': 'reference',
                                                  'type': 'string',
                                                  'x-reference-namespace': 'resource_binding'}},
                   'required': ['resource_id', 'kind', 'allocation', 'capability_binding_ref'],
                   'type': 'object'},
 'api_snapshot_data': {'additionalProperties': False,
                       'properties': {'class_ref': {'format': 'reference',
                                                    'type': 'string',
                                                    'x-reference-namespace': 'execution_class'},
                                      'current_condition': {'additionalProperties': False,
                                                            'properties': {'reason': {'enum': [None,
                                                                                               'operator_report',
                                                                                               'outage',
                                                                                               'maintenance',
                                                                                               'recovered']},
                                                                           'ref': {'format': 'reference',
                                                                                   'type': ['string', 'null'],
                                                                                   'x-reference-namespace': 'execution_condition'},
                                                                           'reported_at': {'type': ['string',
                                                                                                    'null']},
                                                                           'resource_id': {'minLength': 1,
                                                                                           'type': 'string'},
                                                                           'state': {'enum': ['unspecified',
                                                                                              'normal',
                                                                                              'degraded',
                                                                                              'unavailable']}},
                                                            'required': ['ref',
                                                                         'resource_id',
                                                                         'state',
                                                                         'reason',
                                                                         'reported_at'],
                                                            'type': 'object'},
                                      'execution_class': {'$ref': '#/$defs/api_execution_class'},
                                      'expectation_method': {'const': 'empirical_reported_result_duration_mean_by_condition_v1'},
                                      'history_through_sequence': {'minimum': 0, 'type': 'integer'},
                                      'observation_unit': {'const': 'logical_provider_job_reported_result'},
                                      'statistics': {'items': {'additionalProperties': False,
                                                               'properties': {'condition_state': {'enum': ['unspecified',
                                                                                                           'normal',
                                                                                                           'degraded',
                                                                                                           'unavailable']},
                                                                              'max_seconds': {'minimum': 0,
                                                                                              'type': ['number',
                                                                                                       'null']},
                                                                              'mean_seconds': {'minimum': 0,
                                                                                               'type': ['number',
                                                                                                        'null']},
                                                                              'min_seconds': {'minimum': 0,
                                                                                              'type': ['number',
                                                                                                       'null']},
                                                                              'reported_result_count': {'minimum': 0,
                                                                                                        'type': 'integer'}},
                                                               'required': ['condition_state',
                                                                            'reported_result_count',
                                                                            'mean_seconds',
                                                                            'min_seconds',
                                                                            'max_seconds'],
                                                               'type': 'object'},
                                                     'type': 'array'},
                                      'version': {'const': 'reported_result_statistics_v1'}},
                       'required': ['version',
                                    'class_ref',
                                    'execution_class',
                                    'history_through_sequence',
                                    'current_condition',
                                    'observation_unit',
                                    'statistics',
                                    'expectation_method'],
                       'type': 'object'},
 'existing_api_option': {'additionalProperties': False,
                         'properties': {'algorithm': {'enum': ['phmmer', 'hmmscan']},
                                        'database': {'minLength': 1, 'type': 'string'},
                                        'execution_class_ref': {'format': 'reference',
                                                                'type': 'string',
                                                                'x-reference-namespace': 'execution_class'},
                                        'parameters': {'additionalProperties': False,
                                                       'properties': {'E': {'type': 'number'},
                                                                      'T': {'type': 'number'},
                                                                      'domE': {'type': 'number'},
                                                                      'domT': {'type': 'number'},
                                                                      'exclude_taxonomy': {'items': {'minimum': 1,
                                                                                                     'type': 'integer'},
                                                                                           'type': 'array'},
                                                                      'incE': {'type': 'number'},
                                                                      'incT': {'type': 'number'},
                                                                      'incdomE': {'type': 'number'},
                                                                      'incdomT': {'type': 'number'},
                                                                      'include_taxonomy': {'items': {'minimum': 1,
                                                                                                     'type': 'integer'},
                                                                                           'type': 'array'},
                                                                      'mx': {'minLength': 1,
                                                                             'type': 'string'},
                                                                      'pextend': {'type': 'number'},
                                                                      'popen': {'type': 'number'},
                                                                      'threshold': {'enum': ['evalue',
                                                                                             'bitscore']}},
                                                       'required': [],
                                                       'type': 'object'},
                                        'proposal_ref': {'format': 'reference',
                                                         'type': 'string',
                                                         'x-reference-namespace': 'execution_proposal'},
                                        'provider': {'const': 'hmmer'},
                                        'subject_ref': {'format': 'reference',
                                                        'type': 'string',
                                                        'x-reference-namespace': None},
                                        'version': {'const': 'api_execution_option_v1'}},
                         'required': ['version',
                                      'provider',
                                      'subject_ref',
                                      'algorithm',
                                      'database',
                                      'parameters',
                                      'execution_class_ref',
                                      'proposal_ref'],
                         'type': 'object'},
 'forecast_disposition': {'additionalProperties': False,
                          'properties': {'code': {'enum': [None,
                                                           'history_schema_unavailable',
                                                           'history_unavailable',
                                                           'not_opted_in_order',
                                                           'reported_duration_conflict',
                                                           'reported_duration_identity_conflict',
                                                           'reported_duration_invalid',
                                                           'reported_duration_missing',
                                                           'start_binding_unavailable',
                                                           'start_condition_unknown',
                                                           'statistics_identity_conflict',
                                                           'submission_binding_ambiguous',
                                                           'submission_binding_conflict',
                                                           'submission_binding_unavailable',
                                                           'timing_binding_unavailable',
                                                           'timing_custody_unavailable',
                                                           'timing_source_publication_unavailable',
                                                           'unsupported_statistics_configuration']},
                                         'intent_ref': {'type': 'null'},
                                         'measurement_ref': {'type': 'null'},
                                         'order_binding_ref': {'type': 'null'},
                                         'source_ref': {'type': 'null'},
                                         'state': {'enum': ['available',
                                                            'unavailable',
                                                            'not_applicable',
                                                            'conflict']},
                                         'submission_binding_ref': {'type': 'null'},
                                         'version': {'const': 'api_timing_disposition_v1'}},
                          'required': ['version',
                                       'state',
                                       'code',
                                       'order_binding_ref',
                                       'intent_ref',
                                       'submission_binding_ref',
                                       'measurement_ref',
                                       'source_ref'],
                          'type': 'object'},
 'hmmer_arguments': {'additionalProperties': False,
                     'properties': {'algorithm': {'enum': ['phmmer', 'hmmscan']},
                                    'database': {'minLength': 1, 'type': 'string'},
                                    'page_size': {'minimum': 1, 'type': 'integer'},
                                    'parameters': {'additionalProperties': False,
                                                   'properties': {'E': {'type': 'number'},
                                                                  'T': {'type': 'number'},
                                                                  'domE': {'type': 'number'},
                                                                  'domT': {'type': 'number'},
                                                                  'exclude_taxonomy': {'items': {'minimum': 1,
                                                                                                 'type': 'integer'},
                                                                                       'type': 'array'},
                                                                  'incE': {'type': 'number'},
                                                                  'incT': {'type': 'number'},
                                                                  'incdomE': {'type': 'number'},
                                                                  'incdomT': {'type': 'number'},
                                                                  'include_taxonomy': {'items': {'minimum': 1,
                                                                                                 'type': 'integer'},
                                                                                       'type': 'array'},
                                                                  'mx': {'minLength': 1, 'type': 'string'},
                                                                  'pextend': {'type': 'number'},
                                                                  'popen': {'type': 'number'},
                                                                  'threshold': {'enum': ['evalue',
                                                                                         'bitscore']}},
                                                   'required': [],
                                                   'type': 'object'},
                                    'subject_ref': {'description': 'An existing persistent record ID. In a '
                                                                   'reasoning commit only, @name refers to '
                                                                   'an earlier successfully processed row '
                                                                   'declared with alias name in this same '
                                                                   'commit. Ordinary tool calls require '
                                                                   'existing persistent IDs.',
                                                    'pattern': '^(?:[a-z][a-z_]*_[a-f0-9]{24,64}|@[A-Za-z][A-Za-z0-9_]*)$',
                                                    'type': 'string'}},
                     'required': ['subject_ref', 'algorithm', 'database'],
                     'type': 'object'},
 'hmmer_normalized_arguments': {'additionalProperties': False,
                                'properties': {'algorithm': {'enum': ['phmmer', 'hmmscan']},
                                               'database': {'minLength': 1, 'type': 'string'},
                                               'page_size': {'minimum': 1, 'type': 'integer'},
                                               'parameters': {'additionalProperties': False,
                                                              'properties': {'E': {'type': 'number'},
                                                                             'T': {'type': 'number'},
                                                                             'domE': {'type': 'number'},
                                                                             'domT': {'type': 'number'},
                                                                             'exclude_taxonomy': {'items': {'minimum': 1,
                                                                                                            'type': 'integer'},
                                                                                                  'type': 'array'},
                                                                             'incE': {'type': 'number'},
                                                                             'incT': {'type': 'number'},
                                                                             'incdomE': {'type': 'number'},
                                                                             'incdomT': {'type': 'number'},
                                                                             'include_taxonomy': {'items': {'minimum': 1,
                                                                                                            'type': 'integer'},
                                                                                                  'type': 'array'},
                                                                             'mx': {'minLength': 1,
                                                                                    'type': 'string'},
                                                                             'pextend': {'type': 'number'},
                                                                             'popen': {'type': 'number'},
                                                                             'threshold': {'enum': ['evalue',
                                                                                                    'bitscore']}},
                                                              'required': [],
                                                              'type': 'object'},
                                               'subject_ref': {'description': 'An existing persistent record '
                                                                              'ID. In a reasoning commit '
                                                                              'only, @name refers to an '
                                                                              'earlier successfully '
                                                                              'processed row declared with '
                                                                              'alias name in this same '
                                                                              'commit. Ordinary tool calls '
                                                                              'require existing persistent '
                                                                              'IDs.',
                                                               'pattern': '^(?:[a-z][a-z_]*_[a-f0-9]{24,64}|@[A-Za-z][A-Za-z0-9_]*)$',
                                                               'type': 'string'}},
                                'required': ['subject_ref',
                                             'algorithm',
                                             'database',
                                             'parameters',
                                             'page_size'],
                                'type': 'object'},
 'hmmer_request': {'additionalProperties': False,
                   'properties': {'algorithm': {'enum': ['phmmer', 'hmmscan']},
                                  'database': {'minLength': 1, 'type': 'string'},
                                  'identity_version': {'const': 'hmmer_single_fasta_sequence_v2'},
                                  'page_size': {'minimum': 1, 'type': 'integer'},
                                  'parameters': {'additionalProperties': False,
                                                 'properties': {'E': {'type': 'number'},
                                                                'T': {'type': 'number'},
                                                                'domE': {'type': 'number'},
                                                                'domT': {'type': 'number'},
                                                                'exclude_taxonomy': {'items': {'minimum': 1,
                                                                                               'type': 'integer'},
                                                                                     'type': 'array'},
                                                                'incE': {'type': 'number'},
                                                                'incT': {'type': 'number'},
                                                                'incdomE': {'type': 'number'},
                                                                'incdomT': {'type': 'number'},
                                                                'include_taxonomy': {'items': {'minimum': 1,
                                                                                               'type': 'integer'},
                                                                                     'type': 'array'},
                                                                'mx': {'minLength': 1, 'type': 'string'},
                                                                'pextend': {'type': 'number'},
                                                                'popen': {'type': 'number'},
                                                                'threshold': {'enum': ['evalue',
                                                                                       'bitscore']}},
                                                 'required': [],
                                                 'type': 'object'},
                                  'query_length': {'minimum': 1, 'type': 'integer'},
                                  'query_sha256': {'pattern': '^[0-9a-f]{64}$', 'type': 'string'},
                                  'query_sha256_representation': {'const': 'submitted_fasta_utf8_bytes'},
                                  'sequence_sha256': {'pattern': '^[0-9a-f]{64}$', 'type': 'string'},
                                  'sequence_sha256_representation': {'const': 'single_fasta_sequence_uppercase_whitespace_removed_ascii'},
                                  'subject_ref': {'description': 'An existing persistent record ID. In a '
                                                                 'reasoning commit only, @name refers to an '
                                                                 'earlier successfully processed row '
                                                                 'declared with alias name in this same '
                                                                 'commit. Ordinary tool calls require '
                                                                 'existing persistent IDs.',
                                                  'pattern': '^(?:[a-z][a-z_]*_[a-f0-9]{24,64}|@[A-Za-z][A-Za-z0-9_]*)$',
                                                  'type': 'string'}},
                   'required': ['subject_ref',
                                'algorithm',
                                'database',
                                'parameters',
                                'page_size',
                                'query_sha256',
                                'identity_version',
                                'query_sha256_representation',
                                'sequence_sha256_representation',
                                'sequence_sha256',
                                'query_length'],
                   'type': 'object'}}

_DEFINITIONS['existing_api_report_estimate'] = deepcopy(API_REPORT_ESTIMATE_SCHEMA)
_DEFINITIONS['input_version'] = deepcopy(INPUT_VERSION_SCHEMA)


def _expand(value):
    if isinstance(value, dict):
        if '$ref' in value:
            return _expand(_DEFINITIONS[value['$ref'].removeprefix('#/$defs/')])
        return {key: _expand(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_expand(item) for item in value]
    return value


API_CAPTURE_SCHEMA = _expand(_DEFINITIONS['api_capture'])
API_ESTIMATE_RESULT_SCHEMA = _expand(_DEFINITIONS['api_estimate_output'])


def _sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _options(request, forecasts):
    return [{'version': 'api_execution_option_v1', 'provider': 'hmmer',
        **{key: deepcopy(request[key]) for key in ('subject_ref', 'algorithm', 'database', 'parameters')},
        'execution_class_ref': row['execution_class_ref'], 'proposal_ref': row['proposal_ref']}
        for row in forecasts if row['execution_class_ref'] is not None and row['proposal_ref'] is not None]


def _disposition(capture):
    from .api_timing_records import timing_disposition
    available = capture['status'] == 'available'
    code = None if available else capture['code']
    if code == 'invalid_statistics':
        code = 'timing_binding_unavailable'
    return timing_disposition('available' if available else 'unavailable', code)


class ApiExecutionPlanner:
    def __init__(self, store, *, run_id, ports, timing, resource_estimator):
        from .api_reported_statistics import ApiReportedStatistics
        from .api_timing_records import ApiTimingLedger
        from .public_search_operations import ProviderJobOperations, PublicSearchPorts
        from .public_search_publication import PublicSearchResultPublisher
        from .state import Store
        if (not isinstance(store, Store) or type(ports) is not PublicSearchPorts
                or type(ports.operations) is not ProviderJobOperations
                or type(ports.result_publisher) is not PublicSearchResultPublisher
                or type(timing) is not ApiTimingLedger
                or type(timing.statistics) is not ApiReportedStatistics
                or type(resource_estimator) is not ResourceToolEstimator):
            raise TypeError('typed_api_execution_planner_owners_required')
        if resource_estimator.as_record() != ResourceToolEstimator.with_reported_results().as_record():
            raise ValueError('reported_result_estimator_not_enabled')
        self.store, self.run_id, self.ports = store, run_id, ports
        self.timing, self.resource_estimator = timing, resource_estimator
        self._validate_owners()
        # The publisher's actual registry is the callable authority even before
        # attachment; no configuration-only stand-in can authorize this branch.
        self.validate_registry(ports.result_publisher.tools)

    def _validate_owners(self):
        operations, publisher = self.ports.operations, self.ports.result_publisher
        saved = self.timing.as_record()
        if (operations.store is not self.store or publisher.store is not self.store
                or publisher.operations is not operations or operations.timing is not self.timing
                or self.timing.store is not self.store or self.timing.run_id != self.run_id
                or saved['store_path'] != str(self.store.path.resolve())
                or saved['registry'] != self.ports.registry or operations.registry != self.ports.registry
                or self.timing.statistics.registry != self.ports.registry
                or self.timing.statistics.binding is not self.timing.binding):
            raise ContractError('api_execution_planner_identity_conflict')

    def validate_registry(self, tool_registry):
        from .public_search_operations import hmmer_client_binding_sha256
        from .tools import ToolRegistry
        self._validate_owners()
        if (type(tool_registry) is not ToolRegistry or tool_registry.store is not self.store
                or self.ports.result_publisher.tools is not tool_registry
                or self.ports.operations.remote_searches is not tool_registry.remote_searches
                or tool_registry.remote_searches.store is not self.store
                or hmmer_client_binding_sha256(tool_registry.remote_searches.clients)
                    != self.ports.registry['client_binding_sha256']):
            raise ContractError('api_execution_planner_identity_conflict')

    def as_record(self):
        from . import hmmer_request_preparation
        return {'version': VERSION, 'ledger': self.timing.as_record(),
            'resource_estimator': self.resource_estimator.as_record(),
            'callable': CALLABLE, 'target': TARGET,
            'preparation_version': hmmer_request_preparation.VERSION,
            'implementation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'preparation_sha256': hashlib.sha256(Path(hmmer_request_preparation.__file__).read_bytes()).hexdigest()}

    def _selection(self):
        from .hmmer_resource_information import api_selection
        return api_selection(self.ports.registry)

    def input_schema(self, hmmer_arguments_schema):
        value = _expand(_DEFINITIONS['api_estimate_input_template'])
        value['properties']['arguments'] = deepcopy(hmmer_arguments_schema)
        value['properties']['resource_selection'] = {'const': self._selection()}
        return value

    def estimate(self, arguments, *, scope):
        from .hmmer_request_preparation import prepare_hmmer_request, qualify_api_candidate
        selected = plain(arguments)
        validate_schema(selected, self.input_schema(_DEFINITIONS['hmmer_arguments']))
        try:
            qualify_api_candidate(self.store, scope=scope, selection=selected['resource_selection'],
                constraints=selected['constraints'], immutable_input_versions=selected['immutable_input_versions'])
            prepared = prepare_hmmer_request(selected['arguments'],
                sequence_symbols=self.ports.sequence_symbols, scope=scope)
        except ContractError:
            raise
        except ValueError as error:
            raise ContractError(str(error)) from error
        request = plain(prepared.request)
        capture = self.timing.statistics.capture(request)
        forecasts = self._validate_capture(capture, request)
        result = {'version': RESULT_VERSION, 'tool': TARGET, 'arguments': plain(prepared.arguments),
            'normalized_arguments': plain(prepared.normalized_arguments), 'scope_sha256': _sha(scope),
            **{key: deepcopy(selected[key]) for key in ('resource_selection', 'constraints', 'immutable_input_versions')},
            'request': request, 'request_sha256': _sha(request),
            'api_reported_execution_expectations': [deepcopy(capture)],
            'api_reported_execution_forecasts': forecasts,
            'api_execution_options': _options(request, forecasts),
            'api_timing_planning_disposition': _disposition(capture)}
        return self.validate_result(result, selected_arguments=selected, scope=scope)

    def _validate_capture(self, capture, request):
        """Validate original typed statistics using only pure class/projection APIs."""
        try:
            validate_schema(capture, API_CAPTURE_SCHEMA)
            try:
                expected = asdict(self.timing.statistics.execution_class(request))
            except ValueError:
                expected = None
            classes, snapshots = capture['execution_classes'], capture['snapshots']
            if expected is None:
                if (capture['status'] != 'unavailable' or capture['code'] != 'unsupported_statistics_configuration'
                        or classes or snapshots):
                    raise ValueError('unsupported_statistics_capture_conflict')
            elif classes != [expected]:
                raise ValueError('api_capture_class_conflict')
            elif capture['status'] == 'available':
                if capture['code'] is not None or len(snapshots) != 1:
                    raise ValueError('api_capture_snapshot_conflict')
            elif (snapshots or (capture['status'], capture['code']) not in {
                    ('unavailable', 'history_unavailable'), ('unavailable', 'history_schema_unavailable'),
                    ('invalid_statistics', 'invalid_statistics')}):
                raise ValueError('api_capture_status_conflict')
            for snapshot in snapshots:
                if snapshot['ref'] != 'execution_expectation_' + _sha(snapshot['data']):
                    raise ValueError('api_capture_expectation_conflict')
            forecasts = self.resource_estimator.estimate_reported_context(deepcopy(capture))
            if capture['status'] == 'available' and any(row['status'] == 'invalid_statistics' for row in forecasts):
                raise ValueError('api_capture_projection_conflict')
            return forecasts
        except (ValueError, TypeError, KeyError, OverflowError) as error:
            raise ContractError('invalid_api_execution_statistics') from error

    def validate_result(self, result, *, selected_arguments, scope):
        """Pure replay validation against the original normalized scope/input.

        No sequence, current scope/version, history, capture, custody recovery or
        transport is consulted. Hashes bind the original local request; the
        shared statistical identity remains only its exposed technical class.
        """
        try:
            value, selected = plain(result), plain(selected_arguments)
            validate_schema(selected, self.input_schema(_DEFINITIONS['hmmer_arguments']))
            # Give malformed original capture the specific statistical failure.
            captures = value.get('api_reported_execution_expectations') if isinstance(value, dict) else None
            if not isinstance(captures, list) or len(captures) != 1:
                raise ContractError('invalid_api_execution_statistics')
            forecasts = self._validate_capture(captures[0], value['request'])
            validate_schema(value, API_ESTIMATE_RESULT_SCHEMA)
            if (value['scope_sha256'] != _sha(scope) or value['request_sha256'] != _sha(value['request'])
                    or any(value[key] != selected[key] for key in
                        ('tool', 'arguments', 'resource_selection', 'constraints', 'immutable_input_versions'))):
                raise ValueError('api_original_input_conflict')
            normalized = deepcopy(value['arguments'])
            normalized.setdefault('parameters', {})
            normalized.setdefault('page_size', 50)
            if (value['normalized_arguments'] != normalized or any(value['request'][key] != item
                    for key, item in normalized.items())):
                raise ValueError('api_request_normalization_conflict')
            constraints, selection = value['constraints'], value['resource_selection']
            for key, actual in (('resource_id', selection['resource_id']), ('kind', 'api'),
                    *selection['allocation'].items()):
                if key in constraints and constraints[key] != actual:
                    raise ValueError('api_candidate_constraint_conflict')
            for key, actual in (('allowed_resource_ids', selection['resource_id']), ('allowed_kinds', 'api')):
                if key in constraints and actual not in constraints[key]:
                    raise ValueError('api_candidate_constraint_conflict')
            if (value['api_reported_execution_forecasts'] != forecasts
                    or value['api_execution_options'] != _options(value['request'], forecasts)
                    or value['api_timing_planning_disposition'] != _disposition(captures[0])):
                raise ValueError('api_original_projection_conflict')
            return deepcopy(value)
        except ContractError as error:
            if str(error) == 'invalid_api_execution_statistics':
                raise
            raise ContractError('api_execution_proposal_conflict') from error
        except (ValueError, TypeError, KeyError, OverflowError, AttributeError) as error:
            raise ContractError('api_execution_proposal_conflict') from error


__all__ = ['ApiExecutionPlanner', 'VERSION', 'RESULT_VERSION', 'TARGET', 'CALLABLE',
           'API_CAPTURE_SCHEMA', 'API_ESTIMATE_RESULT_SCHEMA']
