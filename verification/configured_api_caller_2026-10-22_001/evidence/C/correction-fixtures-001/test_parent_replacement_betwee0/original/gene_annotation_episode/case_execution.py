"""Fixed one-gene case preparation and delegation to the shared workflow.

No episode loop, scientific scorer, estimator, itinerary or default policy here.
A caller supplies the policy implementation and its explicit parameters.
"""
from __future__ import annotations

import argparse
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import sqlite3
import tomllib

from ._local_job_worker import atomic_json
from .domain import canonical
from .episode_application_services import service_binding
from .episode_bindings import native_job_event_configuration
from .execution_expectations import ExecutionExpectations
from .execution_recording import HomologyStatistics
from .homology_episodes import HomologyEpisodes
from .homology_jobs import FileAsset, HomologyJobs, digest
from .local_jobs import LocalJobPolicy
from .materials import artifact_path
from .run_statistics import RunHistory
from .native_timing_information import NativeTimingInformation
from .resource_estimation import ResourceToolEstimator
from .runtime import _effective_models, _effective_restoration_configuration, run_workflow
from .state import Store
from .tool_configuration import build_tools


VERSION = 'fixed_gene_case_execution_v1'


@dataclass(frozen=True)
class PolicyBindings:
    project_task_credit: object
    project_scientific_child_credit: object
    project_job_credit: object
    project_monitoring_credit: object
    controller_factory: object
    task_credit_definition: dict
    scientific_child_credit_definition: dict
    job_credit_definition: dict
    monitoring_credit_definition: dict
    controller_definition: dict
    project_annotation_score: object = None
    annotation_score_definition: dict | None = None
    initial_known_record_refs: list[str] | None = None
    native_timing_information: NativeTimingInformation | None = None
    episode_service_factory: object = None
    episode_service_binding: dict | None = None
    episode_record_receipts: bool = False
    execution_planning_roles: tuple[str, ...] | None = None
    native_job_events: dict | None = None
    episode_service_inputs: str | None = None
    annotation_child_roles: tuple[str, ...] | None = None
    resource_estimator: ResourceToolEstimator | None = None

    def __post_init__(self):
        native_job_event_configuration(self.native_job_events)
        if type(self.episode_record_receipts) is not bool:
            raise TypeError('episode_record_receipts_must_be_bool')
        if self.episode_record_receipts and self.initial_known_record_refs is None:
            raise ValueError('receipt_binding_requires_explicit_initial_known_record_refs')
        if self.execution_planning_roles is not None and (
                not isinstance(self.execution_planning_roles, tuple) or not self.execution_planning_roles
                or any(not isinstance(role, str) or not role.isidentifier()
                       for role in self.execution_planning_roles)
                or len(set(self.execution_planning_roles)) != len(self.execution_planning_roles)):
            raise ValueError('explicit_unique_execution_planning_roles_required')
        if self.annotation_child_roles is not None and (
                not isinstance(self.annotation_child_roles, tuple)
                or any(not isinstance(role, str) or not role.isidentifier()
                       for role in self.annotation_child_roles)
                or len(set(self.annotation_child_roles)) != len(self.annotation_child_roles)):
            raise ValueError('explicit_unique_annotation_child_roles_required')
        service_binding(self.episode_service_factory, self.episode_service_binding,
            inputs=self.episode_service_inputs)
        if self.native_timing_information is not None and type(self.native_timing_information) is not NativeTimingInformation:
            raise TypeError('typed_native_timing_information_required')
        if self.resource_estimator is not None and type(self.resource_estimator) is not ResourceToolEstimator:
            raise TypeError('typed_resource_tool_estimator_required')
        if not all(callable(value) for value in (self.project_task_credit, self.project_scientific_child_credit,
                                                self.project_job_credit, self.project_monitoring_credit, self.controller_factory)):
            raise ValueError('case_requires_explicit_credit_and_controller_functions')
        for value in (self.task_credit_definition, self.scientific_child_credit_definition,
                      self.job_credit_definition, self.monitoring_credit_definition, self.controller_definition):
            if not isinstance(value, dict) or not value:
                raise ValueError('case_requires_explicit_binding_definitions')
            canonical(value)
        if self.project_annotation_score is None:
            if self.annotation_score_definition is not None:
                raise ValueError('annotation_score_definition_requires_projector')
        elif (not callable(self.project_annotation_score)
                or not isinstance(self.annotation_score_definition, dict)
                or not self.annotation_score_definition):
            raise ValueError('annotation_score_requires_explicit_projector_and_definition')
        else:
            canonical(self.annotation_score_definition)
        if self.initial_known_record_refs is not None and (
                not isinstance(self.initial_known_record_refs, list)
                or not all(isinstance(ref, str) for ref in self.initial_known_record_refs)):
            raise ValueError('initial_known_record_refs_must_be_explicit_references')


def _json_copy(value):
    return json.loads(canonical(value))


def _path(base, value):
    value = Path(value).expanduser()
    return value.resolve() if value.is_absolute() else (base/value).resolve()


def _fixed_case(case_dir, workspace):
    case = json.loads((case_dir/'case.json').read_text())
    if case['target_kind'] != 'single_gene':
        raise ValueError('this_harness_requires_one_fixed_gene_case')
    for name, expected in case['target_files'].items():
        if digest(case_dir/name) != expected:
            raise ValueError('fixed_case_sequence_file_changed')
    _workspace_binding(workspace, case['target_ref'], case['problem_ref'])
    return case


def _workspace_binding(workspace, target_ref, problem_ref, expected_sequence_sha256=None):
    problem = workspace.problem()
    targets = workspace.targets()
    if (problem['subject_refs'] != [target_ref] or len(targets) != 1
            or targets[0]['id'] != target_ref or problem['id'] != problem_ref):
        raise ValueError('case_workspace_has_different_fixed_material')
    sequence_sha256 = digest(artifact_path(workspace, targets[0]['sequence_ref']))
    if expected_sequence_sha256 is not None and sequence_sha256 != expected_sequence_sha256:
        raise ValueError('prepared_case_sequence_changed')
    return sequence_sha256


def _evidence_index(store, case_dir, case):
    """An inventory of caller inputs; no generated scientific interpretation."""
    path = case_dir/'evidence-refs.json'
    evidence = json.loads(path.read_text()) if path.exists() else {}
    scope = {'subject_refs': [case['target_ref']]}
    valid, unavailable = {}, []
    def admit(value, kind, label):
        try:
            record = store.get(value)
            if record['record_type'] == kind and store.reference_subset([value], scope):
                return value
        except (KeyError, ValueError, TypeError):
            pass
        unavailable.append({'input_key': label, 'requested_ref': value})
        return None
    for alias, value in evidence.get('source_refs', {}).items():
        reference = admit(value, 'source', alias)
        if reference is not None:
            valid[alias] = reference
    comparisons = [ref for index, value in enumerate(evidence.get('comparison_refs', []))
        if (ref := admit(value, 'observation', 'comparison_'+str(index))) is not None]
    product = evidence.get('product_ref')
    product = admit(product, 'product', 'product_ref') if product is not None else None
    payload = {'case_ref': case['case_ref'], 'target_ref': case['target_ref'], 'product_ref': product,
        'baseline_source_refs': valid, 'baseline_comparison_refs': comparisons,
        'unavailable_input_references': unavailable,
        'source_assertions_are_investigation_conclusions': False,
        'inventory_is_episode_progress': False}
    if evidence.get('background_unavailable'):
        payload['preparation_feedback'] = evidence['background_unavailable']
    artifact = store.artifact(canonical(payload), 'application/json')
    return store.put('source', {'provider': 'caller.fixed_gene_evidence_index', 'accession': case['case_ref'],
        'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None,
        'version': VERSION, 'retrieved_at': None, 'parent_source_refs': list(dict.fromkeys(valid.values())),
        'operand_refs': [case['target_ref'], *([product] if product is not None else [])]}, origin='tool')['id']


def _configuration(case_dir, supplied):
    required = {'workspace', 'history', 'resource_id', 'max_cpu', 'executable', 'reference_database', 'local_jobs', 'models'}
    allowed = required | {'reference_records', 'reference_residues', 'restoration', 'public', 'local_tools', 'search_modes'}
    if not required <= set(supplied) <= allowed:
        raise ValueError('case_configuration_fields_incomplete_or_unknown')
    result = _json_copy(supplied)
    result['workspace'], result['history'] = str(_path(case_dir, supplied['workspace'])), str(_path(case_dir, supplied['history']))
    for key in ('executable', 'reference_database'):
        asset = supplied[key]
        if not isinstance(asset, dict) or set(asset) != {'path', 'sha256'}:
            raise ValueError('explicit_native_file_asset_required')
        result[key] = FileAsset(_path(case_dir, asset['path']), asset['sha256']).as_record()
    result['local_jobs'] = LocalJobPolicy(**supplied['local_jobs']).to_dict()
    result['models'] = _effective_models({'models': supplied['models']})
    result['restoration'] = _effective_restoration_configuration(supplied)
    return result


def prepare_case_run(case_dir, run_dir, configuration, *, focus=None):
    """Prepare resources/context; no policy execution, model or native launch."""
    if focus is not None and (not isinstance(focus, str) or not focus.strip()):
        raise ValueError('case_scientific_focus_requires_nonempty_text')
    case_dir, run_dir = Path(case_dir).resolve(), Path(run_dir).resolve()
    settings = _configuration(case_dir, configuration)
    marker = run_dir/'case-launch.json'
    if not (Path(settings['workspace'])/'state.sqlite3').is_file():
        raise ValueError('prepared_case_workspace_unavailable')
    if marker.is_file():
        previous = json.loads(marker.read_text())
        if previous['configuration'] != settings:
            raise ValueError('prepared_case_assignment_conflict')
        if focus is not None and previous.get('focus') != focus:
            raise ValueError('prepared_case_scientific_focus_conflict')
        with Store(settings['workspace']) as store:
            _workspace_binding(store, previous['target_ref'], previous['problem_ref'], previous['target_sequence_sha256'])
        jobs = HomologyJobs(run_dir/'native-jobs')
        try:
            if jobs.config != previous['registry_configuration']:
                raise ValueError('prepared_native_resources_conflict')
        finally:
            jobs.close()
        return previous
    with Store(settings['workspace']) as store:
        case = _fixed_case(case_dir, store)
        context_ref = _evidence_index(store, case_dir, case)
        target_sha256 = _workspace_binding(store, case['target_ref'], case['problem_ref'])
    run_dir.mkdir(parents=True, exist_ok=True)
    registry = run_dir/'native-jobs'
    if (registry/'configuration.json').is_file():
        jobs = HomologyJobs(registry)
    else:
        jobs = HomologyJobs.create(registry, executable=FileAsset(**settings['executable']),
            reference_database=FileAsset(**settings['reference_database']),
            policy=LocalJobPolicy(**settings['local_jobs']), max_cpu=settings['max_cpu'],
            **({'search_modes': settings['search_modes']} if 'search_modes' in settings else {}))
    try:
        expected = {key: settings[key] for key in ('executable', 'reference_database', 'max_cpu')}
        if 'search_modes' in settings:
            expected['search_modes'] = settings['search_modes']
        elif 'search_modes' in jobs.config:
            raise ValueError('prepared_native_resources_conflict')
        if any(jobs.config[key] != value for key, value in expected.items()) or jobs.config['job_limits'] != settings['local_jobs']:
            raise ValueError('prepared_native_resources_conflict')
        registered = jobs.config
    finally:
        jobs.close()
    # Explicit caller path: initialize a new shared history, never adopt an
    # unrelated existing database or silently invent a per-workspace fallback.
    try:
        history = RunHistory(settings['history'], create=not Path(settings['history']).exists())
        history.close()
    except (OSError, sqlite3.Error):
        # The later context/recorder surfaces unavailability. It does not make
        # statistics availability a prerequisite for scientific work.
        pass
    manifest = {'version': VERSION, 'case_dir': str(case_dir), 'run_dir': str(run_dir),
        'configuration': settings, 'problem_ref': case['problem_ref'], 'target_ref': case['target_ref'],
        'target_sequence_sha256': target_sha256,
        'context_source_ref': context_ref, 'registry_configuration': registered,
        'focus': focus,
        'goal': (case['scientific_question'] + ('\n'+focus if focus is not None else '') + '\n'
            'Investigate only the fixed original gene '+case['target_ref']+'. '
            'Read the caller evidence inventory source '+context_ref+' for already acquired sources and native measurements. '
            'Those are prior inputs, not new episode contributions or established target-function conclusions. '
            'Existing unchanged work is reusable; do not repeat acquisition or native searches merely to exercise tools. '
            'Reason from actual source methods, subjects and conditions; retain competing explanations and justified uncertainty. '
            'Choose useful iterative child investigations, ordinary tools and reasoning from outcomes. '
            'No child sequence, number of iterations or scientific completion is prescribed by this harness.')}
    if marker.exists():
        if json.loads(marker.read_text()) != manifest:
            raise ValueError('prepared_case_assignment_conflict')
    else:
        atomic_json(marker, manifest)
    return manifest


def _load_policy(run_dir, policy_file, parameters, *, resume):
    marker = run_dir/'policy-binding.json'
    previous = json.loads(marker.read_text()) if marker.is_file() else None
    if resume:
        if previous is None:
            raise ValueError('resume_requires_recorded_case_policy')
        if policy_file is not None and digest(policy_file) != previous['source_sha256']:
            raise ValueError('resume_cannot_replace_policy_source')
        if parameters is not None and parameters != previous['parameters']:
            raise ValueError('resume_cannot_replace_policy_parameters')
        source, parameters = run_dir/previous['snapshot_file'], previous['parameters']
        if digest(source) != previous['source_sha256']:
            raise ValueError('recorded_policy_source_changed')
    else:
        if policy_file is None or not isinstance(parameters, dict):
            raise ValueError('explicit_policy_source_and_parameters_required')
        body = Path(policy_file).read_bytes()
        source = run_dir/('policy-'+hashlib.sha256(body).hexdigest()+'.py')
        if not source.is_file() or source.read_bytes() != body:
            temporary = source.with_suffix('.writing')
            with temporary.open('wb') as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, source)
            directory = os.open(source.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    identity = digest(source)
    module_name = 'fixed_gene_policy_'+identity
    spec = importlib.util.spec_from_file_location(module_name, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        policy = module.create_policy(_json_copy(parameters))
        if type(policy) is not PolicyBindings:
            raise TypeError('policy_factory_must_return_PolicyBindings')
        recorded = {'source_sha256': identity, 'snapshot_file': source.name, 'parameters': _json_copy(parameters),
            'definitions': _json_copy({'credit': policy.task_credit_definition,
                'scientific_child_credit': policy.scientific_child_credit_definition,
                'job_credit': policy.job_credit_definition,
                'monitoring_credit': policy.monitoring_credit_definition, 'controller': policy.controller_definition})}
        if policy.project_annotation_score is not None:
            recorded['definitions']['annotation_score'] = _json_copy(policy.annotation_score_definition)
        if policy.native_timing_information is not None:
            recorded['definitions']['native_timing_information'] = policy.native_timing_information.as_record()
        if policy.resource_estimator is not None:
            recorded['definitions']['resource_estimator'] = policy.resource_estimator.as_record()
        if policy.initial_known_record_refs is not None:
            recorded['initial_known_record_refs'] = _json_copy(policy.initial_known_record_refs)
        services = service_binding(policy.episode_service_factory, policy.episode_service_binding,
            inputs=policy.episode_service_inputs)
        if services is not None:
            recorded['episode_application_services'] = services
        if policy.episode_record_receipts:
            recorded['episode_record_receipts'] = {
                'version': 'explicit_store_record_receipts_v1', 'enabled': True}
        if policy.execution_planning_roles is not None:
            recorded['execution_planning_roles'] = list(policy.execution_planning_roles)
        if policy.native_job_events is not None:
            recorded['native_job_events'] = native_job_event_configuration(policy.native_job_events)
        if policy.annotation_child_roles is not None:
            recorded['annotation_child_roles'] = list(policy.annotation_child_roles)
        if resume and recorded != previous:
            raise ValueError('restored_policy_definition_changed')
        atomic_json(marker, recorded)
        return policy, recorded
    finally:
        # Active callables retain their own globals. The import cache need not
        # retain closed policy state after those callables are released.
        if sys.modules.get(module_name) is module:
            del sys.modules[module_name]


@contextmanager
def prepared_case_bindings(store, run_dir, *, policy_file=None, parameters=None, resume=True):
    """Reopen caller-owned case resources without starting an investigation.

    The root entry point and independently placed children use this same policy
    and resource construction. Closing it releases its registry connection only;
    existing native executions and other episodes retain their identities.
    """
    run_dir = Path(run_dir).resolve()
    manifest = json.loads((run_dir/'case-launch.json').read_text())
    if manifest['version'] != VERSION or manifest['run_dir'] != str(run_dir):
        raise ValueError('case_launch_manifest_mismatch')
    settings = manifest['configuration']
    if store.path != Path(settings['workspace']).resolve():
        raise ValueError('prepared_case_workspace_mismatch')
    _workspace_binding(store, manifest['target_ref'], manifest['problem_ref'], manifest['target_sequence_sha256'])
    policy, recorded = _load_policy(run_dir, policy_file, parameters, resume=resume)
    jobs = HomologyJobs(run_dir/'native-jobs')
    try:
        if jobs.config != manifest['registry_configuration']:
            raise ValueError('case_native_registry_configuration_changed')
        statistics = HomologyStatistics(settings['history'], settings['resource_id'],
            settings.get('reference_records'), settings.get('reference_residues'))
        identity = {'policy_source_sha256': recorded['source_sha256'],
            'policy_parameters_sha256': hashlib.sha256(canonical(recorded['parameters']).encode()).hexdigest()}
        binding = HomologyEpisodes(jobs, parser_policy=LocalJobPolicy(**settings['local_jobs']),
            credit_projector=policy.project_job_credit,
            credit_binding={**identity, 'definition': policy.job_credit_definition},
            monitoring_projector=policy.project_monitoring_credit,
            monitoring_binding={**identity, 'definition': policy.monitoring_credit_definition}, statistics=statistics)
        expectations = ExecutionExpectations.for_homology(jobs, statistics, roles=binding.roles,
            planning_roles=(('annotation', 'improvement') if policy.execution_planning_roles is None
                            else policy.execution_planning_roles))
        options = {
            'project_credit': policy.project_task_credit, 'controller_factory': policy.controller_factory,
            'project_child_credit': policy.project_scientific_child_credit,
            'project_annotation_score': policy.project_annotation_score,
            'initial_known_record_refs': policy.initial_known_record_refs,
            'binding_definitions': {key: {**identity, 'definition': recorded['definitions'][key]}
                for key in ('credit', 'scientific_child_credit', 'controller', 'annotation_score')
                if key in recorded['definitions']},
            'job_episodes': binding, 'execution_expectations': expectations,
            'native_timing_information': policy.native_timing_information,
            'resource_estimator': (policy.resource_estimator if policy.resource_estimator is not None
                                   else ResourceToolEstimator())}
        if policy.episode_service_factory is not None:
            options['episode_service_factory'] = policy.episode_service_factory
            options['episode_service_binding'] = policy.episode_service_binding
            if policy.episode_service_inputs is not None:
                options['episode_service_inputs'] = policy.episode_service_inputs
        if policy.annotation_child_roles is not None:
            options['annotation_child_roles'] = policy.annotation_child_roles
        if policy.episode_record_receipts:
            options['episode_record_receipts'] = True
        if policy.native_job_events is not None:
            options['native_job_events'] = native_job_event_configuration(policy.native_job_events)
        yield manifest, options
    finally:
        jobs.close()


async def run_prepared_case(run_dir, *, policy_file=None, parameters=None, resume=False, provider=None):
    run_dir = Path(run_dir).resolve()
    manifest = json.loads((run_dir/'case-launch.json').read_text())
    if not resume and (run_dir/'run.json').exists():
        raise ValueError('case_runtime_already_exists_use_resume')
    settings = manifest['configuration']
    if not (Path(settings['workspace'])/'state.sqlite3').is_file():
        raise ValueError('prepared_case_workspace_unavailable')
    with Store(settings['workspace']) as store, prepared_case_bindings(store, run_dir,
            policy_file=policy_file, parameters=parameters, resume=resume) as (manifest, bindings):
        return await run_workflow(store, build_tools(store, settings), provider=provider,
            provider_config={'models': settings['models'], 'restoration': settings['restoration']},
            run_dir=run_dir, resume=resume, goal=manifest['goal'], **bindings)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prepare = commands.add_parser('prepare')
    prepare.add_argument('--case-dir', type=Path, required=True)
    prepare.add_argument('--run-dir', type=Path, required=True)
    prepare.add_argument('--config', type=Path, required=True)
    prepare.add_argument('--focus-file', type=Path,
        help='Caller scientific focus appended to the fixed case question; no action sequence is installed.')
    run = commands.add_parser('run')
    run.add_argument('--run-dir', type=Path, required=True)
    run.add_argument('--policy', type=Path)
    run.add_argument('--parameters', type=Path)
    run.add_argument('--resume', action='store_true')
    args = parser.parse_args(argv)
    if args.command == 'prepare':
        value = prepare_case_run(args.case_dir, args.run_dir, tomllib.loads(args.config.read_text()),
            focus=args.focus_file.read_text() if args.focus_file is not None else None)
        result = {'state': 'prepared', 'run_dir': value['run_dir'], 'target_ref': value['target_ref'],
                  'context_source_ref': value['context_source_ref'], 'native_or_model_jobs_launched': 0}
    else:
        parameters = json.loads(args.parameters.read_text()) if args.parameters is not None else None
        result = asyncio.run(run_prepared_case(args.run_dir, policy_file=args.policy, parameters=parameters, resume=args.resume))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    # Policy factories import this module's public PolicyBindings class. Route
    # script execution through that same module so __main__ does not create a
    # competing class identity and reject a valid factory result.
    from gene_annotation_episode.case_execution import main as case_main
    case_main()
