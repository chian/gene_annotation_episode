"""Caller-owned configured demonstration; no private decision loop or model answers.

Preparation freezes source code and original caller contracts without inference.
Execution uses the ordinary Workflow/Episode with a fixed caller return on its
annotation parent. That parent owns its actual literature child commissions.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tomllib
import uuid

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
PIN = HERE / 'source_pin_001'
CASE = HERE / 'configured_001'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')


def freeze():
    if PIN.exists():
        raise ValueError('source_pin_already_exists')
    rows = []
    for package in ('gene_annotation_episode', 'method_loop'):
        for source in sorted((REPO/package).rglob('*')):
            if not source.is_file() or '__pycache__' in source.parts or source.suffix == '.pyc':
                continue
            target = PIN/source.relative_to(REPO)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            rows.append({'path': str(source.relative_to(REPO)), 'sha256': digest(target), 'bytes': target.stat().st_size})
    shutil.copyfile(__file__, PIN/'caller_001.py')
    rows.append({'path': 'caller_001.py', 'sha256': digest(PIN/'caller_001.py'), 'bytes': (PIN/'caller_001.py').stat().st_size})
    write(HERE/'SOURCE_PIN_001.json', {'version': 'complete_package_source_pin_v1', 'files': rows})


def imports():
    # Every application/shared-loop import must come from the immutable pin.
    sys.path[:] = [str(PIN)] + [p for p in sys.path if Path(p or '.').resolve() not in (REPO, HERE)]
    os.environ['PYTHONPATH'] = str(PIN)


def verify_pin():
    saved = json.loads((HERE/'SOURCE_PIN_001.json').read_text())
    for row in saved['files']:
        if digest(PIN/row['path']) != row['sha256']:
            raise ValueError('frozen_implementation_changed:' + row['path'])


def verify_entrypoint():
    manifest = json.loads((HERE/'ENTRYPOINT_PIN_002.json').read_text())
    for row in manifest['files']:
        if digest(HERE/row['path']) != row['sha256']:
            raise ValueError('original_caller_entrypoint_or_contract_changed')


def public_exception(error):
    """Public type and declared contract identifier only; no provider strings."""
    import re
    from gene_annotation_episode.domain import ContractError
    from gene_annotation_episode.communication import ReportBoundaryError
    from method_loop.durable import DurableExecutionError
    code = (error.args[0] if isinstance(error, ContractError) and error.args else
        error.diagnostic.get('code') if isinstance(error, ReportBoundaryError) else
        error.failure.get('code') if isinstance(error, DurableExecutionError) else None)
    if not isinstance(code, str) or re.fullmatch(r'[a-z][a-z0-9_]{0,127}', code) is None:
        code = None
    return {'exception_type': type(error).__name__, 'public_contract_code': code}


def imported_local():
    rows = []
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, '__file__', None)
        if name.split('.')[0] not in ('gene_annotation_episode', 'method_loop') or path is None:
            continue
        p = Path(path).resolve()
        if not p.is_relative_to(PIN):
            raise ValueError('unfrozen_local_import:' + str(p))
        if p.suffix == '.py':
            rows.append({'module': name, 'path': str(p.relative_to(PIN)), 'sha256': digest(p)})
    return rows


QUESTION = (
    'Determine what the retained original experimental paper establishes about the catalytic '
    'activity of its D101A/E322Y alkaline-phosphatase construct in the reported pNPP assay. '
    'Investigate the source contents and select the relevant original row, units, Methods and '
    'applicable footnotes yourself. Return the source-reported catalytic-efficiency parameter '
    'and the uncertainty/replication components for that same report, with actual subject, '
    'construct, preparation, substrate, conditions, endpoint and normalization. Establish what '
    'each number evaluates. Keep reported SD, relative SD, physical independent-preparation '
    'count, statistical estimator count and estimated mean standard error distinct. Unknown '
    'statistical hierarchy or assumptions must remain unknown; no hypothetical scenario is '
    'requested. Preserve the relation between repeated numerical views of the same report. '
    'Interpret the result\'s bearing on molecular activity and the limits of effect isolation, '
    'including background contributors and what the measured endpoint establishes. Distinguish '
    'comparability outside an intended change from attribution of the observed effect. '
    'Use only the one supplied primary-source record and its retained representations; no new '
    'paper search or reacquisition is in scope. No annotation-target sequence is supplied. '
    'Possible functional assertions may emerge from the evidence. Choose your own actual '
    'literature child assignments, return forms, reads, interpretation and operation choices. '
    'Integrate only the typed information actually returned to you. Retain useful partial '
    'results and specific unavailable reasons. This is reference experimental evidence; '
    'target correspondence, W05 aggregation and final annotation credit are outside scope.'
)


def options(prepared):
    from gene_annotation_episode.runtime import controller_from_settings
    from gene_annotation_episode.investigation_progress import ScientificFindingProgress, FindingProgressPolicy
    progress = prepared['configuration']['scientific_progress']
    scientific = ScientificFindingProgress(FindingProgressPolicy(progress['finding_unit']), progress['loss_preview_size'])
    return dict(controller_factory=controller_from_settings(prepared['settings']), project_credit=scientific,
        project_child_credit=scientific, initial_known_record_refs=[prepared['source_ref']],
        episode_binding_descriptors=[prepared['episode_binding_descriptor']],
        annotation_child_roles=('literature',), episode_record_receipts=True)


def assemble(store, prepared, provider=None):
    from gene_annotation_episode.runtime import assemble_workflow, TypedReportContract
    from gene_annotation_episode.tool_configuration import build_tools
    from gene_annotation_episode.literature_a105_worksheet import validate_a105_worksheet_links
    tools = build_tools(store, prepared['tool_configuration'])
    workflow = assemble_workflow(store, tools, provider, CASE/'run', prepared['run_id'], prepared['settings'], **options(prepared))
    scope = prepared['scope']
    bound = {}

    def resolve(ref, namespace=None):
        return workflow.resolver(scope, source=bound.get('root_source'))(ref, namespace)

    def validate(value):
        source = bound['root_source']
        workflow.validate_report(value, scope, grain='annotation', schema=prepared['expanded_form'], source=source)
        ctx = workflow.binding_context(source)
        known = set(ctx.received_record_refs)
        validate_a105_worksheet_links(value, prepared['expanded_form'], prepared['assignment'],
            read_public_record=lambda ref: store.get(ref) if ref in known else None)

    contract = TypedReportContract(prepared['return_purpose'], prepared['expanded_form'], resolve, validate)
    root = workflow.build('annotation', 'root', prepared['scientific_question'], scope,
        contract=contract, initial=prepared['initial_report'], episode_assignment=prepared['assignment'],
        report_contract_declaration=prepared['contract_declaration'])
    bound['root_source'] = root.source
    return workflow, root, tools


def prepare():
    freeze()
    imports()
    verify_pin()
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.literature_a105_worksheet import a105_worksheet_template, NATIVE, SUMMARY, VERSION
    from gene_annotation_episode.episode_contract_information import expand_fact_form
    from gene_annotation_episode.providers import default_config_path
    from gene_annotation_episode.public_configuration import configured_tools
    from gene_annotation_episode.runtime import _effective_configuration, _effective_restoration_configuration, _run_location, _now
    from gene_annotation_episode.episode_journal import Journal
    from gene_annotation_episode.default_scientific_binding import bind_default_science
    from gene_annotation_episode.numerical import ESTIMATOR_VERSION, SOURCE_SHA256
    original = REPO/'verification/literature_reference_evidence_2026-10-25_001/a105_summary_precision_components_248'
    old_manifest = json.loads((original/'PIN_MANIFEST_006.json').read_text())
    source_rows = []
    (HERE/'source_originals_001').mkdir()
    for suffix in ('pdf', 'txt'):
        row = next(row for row in old_manifest['files'] if row['path'].endswith('/sources/elife-06181-v2.' + suffix))
        source = original/'pin_006'/row['path']
        if digest(source) != row['sha256']:
            raise ValueError('original_primary_source_changed')
        target = HERE/'source_originals_001'/source.name
        shutil.copyfile(source, target)
        source_rows.append({**row, 'original_path': str(source), 'retained_path': str(target)})
    shutil.copyfile(original/'PIN_MANIFEST_006.json', HERE/'ORIGINAL_SOURCE_MANIFEST_248_006.json')
    acquisition = REPO/'research/experimental_scoring_review_2026-10-23/a105_independent_preparation_case_242/sources/pdf_acquisition.json'
    shutil.copyfile(acquisition, HERE/'ORIGINAL_PDF_ACQUISITION_242.json')
    CASE.mkdir()
    manifest = CASE/'source_only_input_manifest.json'
    write(manifest, {'schema_version': 1, 'entries': []})
    config = tomllib.loads(default_config_path().read_text())
    with Store(CASE/'state') as store:
        store.create_problem(manifest_path=manifest)
        pdf = HERE/'source_originals_001/elife-06181-v2.pdf'
        text = HERE/'source_originals_001/elife-06181-v2.txt'
        artifact = store.artifact(pdf.read_bytes(), 'application/pdf')
        text_ref = store.artifact(text.read_bytes(), 'text/plain')
        source_ref = store.put('source', {'provider': 'caller_retained_original_primary278',
            'accession': None, 'uri': json.loads(acquisition.read_text())['url'],
            'artifact_ref': artifact, 'text_ref': text_ref, 'request_ref': None, 'version': None,
            'retrieved_at': None}, origin='caller')['id']
        descriptor = LiteratureEpisodes.reference_evidence(None, source_refs=[source_ref]).as_record()
        template = a105_worksheet_template([
            {'field': 'native_parameter', 'source': NATIVE, 'components': ['numerator_parameter']},
            {'field': 'precision', 'source': SUMMARY, 'components': ['source_reported_parameter',
                'source_reported_sd', 'source_relative_reported_sd', 'source_independent_preparation_count',
                'source_statistical_estimator_count', 'source_mean_standard_error']},
        ])
        facts = LiteratureEpisodes.reference_evidence(None, source_refs=[source_ref]).received_report_sources('annotation')
        submitted = json.dumps(template['submitted_form'], ensure_ascii=False)
        expanded = expand_fact_form(submitted, child_role='annotation', facts_by_role={'annotation': facts}, permitted_child_roles=['annotation'])
        directory, run_id = _run_location(store, CASE/'run', False)
        models, control = _effective_configuration(config)
        science = bind_default_science(store, run_dir=directory, resume=False, provider_config=config,
            credit_policy=None, initial_known_record_refs=[source_ref], project_child_credit=None,
            project_annotation_score=None, binding_definitions=None)
        settings = {'schema_version': 1, 'directory': str(directory), 'problem': store.problem(),
            'models': models, 'controller': control, 'goal': QUESTION, 'credit_policy': None,
            'bindings': {'controller': 'gene_annotation_episode.numerical.YieldController',
                'credit': 'gene_annotation_episode.investigation_progress.ScientificFindingProgress',
                'scientific_child_credit': 'gene_annotation_episode.investigation_progress.ScientificFindingProgress'},
            'binding_versions': {'controller': {'estimator_version': ESTIMATOR_VERSION, 'template_sha256': SOURCE_SHA256},
                'credit': {'requirement': 'same_caller_injected_executable'},
                'scientific_child_credit': {'requirement': 'same_caller_injected_executable'}},
            'binding_definitions': science['binding_definitions'],
            'restoration': _effective_restoration_configuration(config),
            'decision_protocol': 'decision_exchange_v1', 'annotation_child_roles': ['literature'],
            'root_action_boundary': 'root_child_only_boundary_v1',
            'episode_record_receipts': {'version': 'explicit_store_record_receipts_v1', 'enabled': True},
            'episode_progress_receipts': {'version': 'received_progress_order_v1'},
            'wait_inputs': {'version': 'wait_inputs_binding_v2'},
            'completed_action_inputs': {'version': 'completed_action_inputs_binding_v1'},
            'scientific_knowledge': {'version': 'episode_received_record_refs_v1', 'initial_known_record_refs': [source_ref]},
            'episode_bindings': [descriptor]}
        from gene_annotation_episode.composition_information import ROOT_BOUNDARY_VERSION
        from gene_annotation_episode.episode_receipts import RECEIPT_VERSION
        settings['root_action_boundary'] = ROOT_BOUNDARY_VERSION
        settings['scientific_knowledge']['version'] = RECEIPT_VERSION
        prepared = {'version': 'configured_original_common_worksheet_caller278_v1', 'run_id': run_id,
            'source_ref': source_ref, 'artifact_ref': artifact, 'text_ref': text_ref,
            'source_identities': source_rows, 'scope': store.validate_scope(),
            'scientific_question': QUESTION, 'return_purpose': 'Return the requested common worksheet with native parameter, source random-precision components and constrained relationships; interpret the molecular-activity assertion and its limitations from admitted child evidence.',
            'template': template, 'expanded_form': expanded['expanded_schema'],
            'contract_declaration': expanded['declaration'],
            'assignment': {'version': 'literature_assignment_v1', 'source_refs': [source_ref],
                'question_context_refs': [], **template['assignment_rosters']},
            'initial_report': {'assessment_context': {'version': VERSION, 'assertion_refs': [], 'quantity_links': [], 'assertion_links': []}},
            'episode_binding_descriptor': descriptor, 'configuration': config,
            'tool_configuration': configured_tools({k: config[k] for k in ('public', 'local_tools', 'local_jobs', 'knowledge_library_directory', 'history', 'resource_id') if k in config}),
            'settings': settings,
            'execution_mode': 'ordinary shared Workflow and method_loop; blocking children, no independent-process binding; actual configured provider; caller-fixed parent return; model-selected children and operations'}
        journal = Journal(store, run_id)
        journal.save('runtime_runs', {'settings': json.dumps(settings), 'state': 'prepared', 'summary': None, 'started_at': _now(), 'updated_at': _now()})
        write(directory/'run.json', {'run_id': run_id, **settings})
        workflow, root, tools = assemble(store, prepared)
        prepared['settings']['initial_tool_resources'] = tools.resource_binding()
        journal.save('runtime_runs', {'settings': json.dumps(prepared['settings']), 'state': 'prepared', 'summary': None, 'started_at': _now(), 'updated_at': _now()})
        write(directory/'run.json', {'run_id': run_id, **prepared['settings']})
        write(CASE/'prepared_caller.json', prepared)
        write(HERE/'PREPARATION_PUBLIC_001.json', {'prepared_at_utc': _now(), 'run_id': run_id,
            'root_episode_id': root.source.episode_id, 'original_source_identities': source_rows,
            'model_settings': models, 'controller': control, 'execution_mode': prepared['execution_mode'],
            'runtime_actions': store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0],
            'runtime_observations': store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0],
            'model_calls': store.db.execute('SELECT count(*) FROM runtime_model_calls').fetchone()[0],
            'root_original_request': root.request.as_record(), 'actual_local_imports': imported_local(),
            'proposed_command': str(REPO/'.venv/bin/python')+' -B '+str(HERE/'caller_001.py')+' execute'})
    verify_pin()


async def execute():
    imports()
    verify_pin()
    verify_entrypoint()
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.providers import ModelConnection
    from gene_annotation_episode.runtime import _now
    from gene_annotation_episode.execution_timing import _process_identity
    prepared = json.loads((CASE/'prepared_caller.json').read_text())
    status = {'state': 'started', 'started_at_utc': _now(), 'process_identity': _process_identity(),
        'run_id': prepared['run_id'], 'entrypoint_manifest': str(HERE/'ENTRYPOINT_PIN_002.json')}
    write(HERE/'STATUS_002.json', status)
    with Store(CASE/'state') as store:
        from gene_annotation_episode.episode_journal import Journal
        journal = Journal(store, prepared['run_id'])

        def save_state(state, summary=None):
            prior = journal.row('runtime_runs')
            journal.save('runtime_runs', {'settings': prior['settings'], 'state': state,
                'summary': None if summary is None else json.dumps(summary, allow_nan=False),
                'started_at': prior['started_at'], 'updated_at': _now()})

        workflow = None
        save_state('running')
        try:
            from gene_annotation_episode.tool_configuration import build_tools
            tools = build_tools(store, prepared['tool_configuration'])
            provider = ModelConnection(prepared['settings']['models'], CASE/'run/providers'/uuid.uuid4().hex,
                PIN, image_resolver=getattr(tools, 'resolve_image_input', None))
            workflow, root, tools = assemble(store, prepared, provider)
            async with provider:
                record = await root.run_async(workflow.context)
                result = await root.build_result(record)
                value = result.as_record()['form']
                root.request.report_contract.admit(value, audit_identifiers=())
                write(HERE/'PUBLIC_TYPED_RETURN_002.json', value)
                pending = workflow.pending_handles(root.source)
                closed_state = 'yielded_with_pending_work' if pending else 'yielded'
                summary = {'state': closed_state, 'ended_by': record.ended_by,
                    'scientific_completion': 'not_established_by_termination',
                    'root_actions': record.units_consumed,
                    'actions': store.db.execute('SELECT count(*) FROM runtime_actions').fetchone()[0],
                    'observations': store.db.execute('SELECT count(*) FROM runtime_observations').fetchone()[0],
                    'episodes': store.db.execute('SELECT count(*) FROM runtime_episodes').fetchone()[0],
                    'successful_typed_child_deliveries': store.db.execute('SELECT count(*) FROM runtime_report_attempts WHERE failure IS NULL AND form IS NOT NULL').fetchone()[0],
                    'pending_handles': pending}
                save_state(closed_state, summary)
                write(HERE/'PUBLIC_SUMMARY_002.json', summary)
                write(HERE/'STATUS_002.json', {**status, **summary, 'finished_at_utc': _now()})
        except BaseException as error:
            state = 'interrupted' if isinstance(error, (KeyboardInterrupt, asyncio.CancelledError)) else 'operational_failure'
            failure = public_exception(error)
            save_state(state, failure)
            write(HERE/'STATUS_002.json', {**status, 'state': state, 'finished_at_utc': _now(), **failure})
            raise
        finally:
            if workflow is not None:
                for row in store.db.execute('SELECT episode_id FROM runtime_episodes'):
                    await workflow.release(row[0])
            write(HERE/'ACTUAL_IMPORTS_002.json', imported_local())
            verify_pin()
            verify_entrypoint()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['execute'])
    args = parser.parse_args()
    asyncio.run(execute())
