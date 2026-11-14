from __future__ import annotations
from copy import deepcopy
import json
from gene_annotation_episode.episodic_workflow.root.a110.communication import plain, validate_form
from gene_annotation_episode.episodic_workflow.root.a110.episode_receipts import EpisodeReceipts
from gene_annotation_episode.episodic_workflow.root.a110.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.episodic_workflow.root.a110.execution_contracts import checked, digest, obj
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_acquisition import ORIGIN, decode_json, is_native_rna_structure_target, qualify_target_plan, require, retained, rna_structure_source_payload, validate_capture
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_result_publication import publish_selected_rna_structure_rows, validate_prepared_rna_grading, authenticate_rna_results_commission
from gene_annotation_episode.episodic_workflow.root.a110.practical_execution_state import _read
from gene_annotation_episode.episodic_workflow.root.a110.progress_records import validate_resource_observation
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_contracts import validate_rna_issue
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.rna_structure_result_views import FAMILY_SOURCES, IDENTIFIER_NAMESPACES, REFERENCE_SOURCE, SAVED_SOURCE, merge_issues, prepare_rna_structure_failure_selection, project_rna_structure_failure_rows, result_receipt_key, validate_rna_structure_result_selector, validate_rna_structure_row, validate_saved_rna_input
VERSION = 'native_rna_structure_acquired_result_v1'
FIELDS = {'version', 'run_id', 'episode_id', 'scope', 'assignment', 'operation_key', 'tool_name', 'arguments', 'target', 'observation', 'capture', 'prepared', 'source_ref', 'record_refs', 'rows', 'failures', 'failure_selection', 'native_success', 'capture_complete', 'delivery_complete'}

def operation_catalog():
    return [{'name': 'execution.results.status', 'description': 'Read the original attempt or assigned retained-sheet status without scientific execution.', 'input_schema': obj({})}, {'name': 'execution.results.collect', 'description': 'Capture, parse, calculate and project the assigned original data, or calculate the explicitly received saved sheet; no new native scientific execution.', 'input_schema': obj({})}]

class NativeRNAStructureResults:

    def __init__(self, owner):
        self.owner, self.store = (owner, owner.store)
        self.directory = owner.directory / 'native-rna-structure-result-index'
        self.records = EpisodeReturnRecords(owner.store, owner.run_id, failure_prefix='rna_return_')

    def applies(self, context):
        return context.role == 'results' and is_native_rna_structure_target(self.owner._target(context))

    def _saved_directory(self, episode_id, operation_key):
        return self.owner.directory / 'execution-results' / digest([self.owner.run_id, episode_id]) / 'native-rna-structure-actions' / digest(operation_key)

    def _context(self, body):
        context = self.records.context(body['episode_id'])
        authenticate_rna_results_commission(self.store, context)
        require(context.role == 'results' and plain(context.assignment) == body['assignment'] and (plain(context.scope) == body['scope']))
        return context

    def _selector(self, assignment, target):
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.execution_episodes import RESULTS_SCHEMA
        assignment = checked(assignment, RESULTS_SCHEMA, 'rna_invalid_input_schema')
        require(is_native_rna_structure_target(target))
        return validate_rna_structure_result_selector(assignment['selector'], mode=target['assignment']['requested_job']['native_rna_structure']['mode'])

    def _bundle(self, body):
        return decode_json(self.store.get_artifact(body['capture']['bundle_artifact_ref']), canonical_bytes=True)

    def saved_descriptor(self, body, *, verify_bytes=True):
        prepared = body['prepared']
        if prepared is None or prepared['sheet_artifact_ref'] is None:
            return None
        if body['assignment']['selector']['acquisition'] == 'retained_sheet_only':
            return deepcopy(body['assignment']['selector']['saved_input'])
        metadata = self.store.get(prepared['sheet_artifact_ref'])
        if verify_bytes:
            retained(self.store, metadata['id'])
        job = body['target']['assignment']['requested_job']['native_rna_structure']
        return validate_saved_rna_input({'schema': 'rna_structure_saved_sheet_input_v1', 'result_receipt_key': result_receipt_key(body), 'handoff_ref': body['assignment']['handoff_ref'], 'source_ref': body['source_ref'], 'bundle_artifact_ref': body['capture']['bundle_artifact_ref'], 'sheet_artifact_ref': metadata['id'], 'sheet_sha256': metadata['sha256'], **{key: job[key] for key in ('record_key', 'operation', 'mode')}})

    def _validate_body(self, body, scope, *, verify_artifacts=False):
        require(type(body) is dict and set(body) == FIELDS and (body['version'] == VERSION) and (body['run_id'] == self.owner.run_id))
        context = self._context(body)
        self.store.validate_scope(body['scope'], parent_scope=plain(scope))
        target = self.owner.job_progress_provider.targets.read_target(body['assignment']['handoff_ref'], body['scope'])
        require(target == body['target'])
        selector = self._selector(body['assignment'], target)
        require(body['tool_name'] in {item['name'] for item in operation_catalog()} and body['arguments'] == {})
        selected = self.owner._selected_result_action(body['episode_id'], body['operation_key'], body['tool_name'], body['arguments'])
        directory = self._saved_directory(body['episode_id'], body['operation_key'])
        require(_read(directory / 'receipt.json') == body)
        require(_read(directory / 'intent.json') == {key: body[key] for key in ('target', 'assignment', 'operation_key', 'tool_name', 'arguments', 'scope')})
        require(_read(directory / 'observation.json') == body['observation'])
        validate_resource_observation(body['observation'])
        if selected['result'] is not None:
            outcome = json.loads(selected['result'])
            expected = self._outcome(body)
            require(set(outcome) in (set(expected), {*expected, 'pending_work_after_action'}) and self.records._equal({key: outcome[key] for key in expected}, expected))
            if 'pending_work_after_action' in outcome:
                from gene_annotation_episode.episodic_workflow.root.a110.waiting import validate_pending
                validate_pending(outcome['pending_work_after_action'])
        failures = [validate_rna_issue(value) for value in body['failures']]
        saved = selector['acquisition'] == 'retained_sheet_only'
        collecting = body['tool_name'] == 'execution.results.collect'
        bundle = None
        if saved:
            original = self.owner.native_rna_structure_returns.resolve_saved_rna_input(context, selector['saved_input'])
            require(all((body[key] == original[key] for key in ('target', 'observation', 'capture', 'native_success', 'capture_complete'))))
            if collecting:
                require(body['source_ref'] == original['source_ref'])
                bundle = self._bundle(original)
        elif body['capture'] is not None:
            require(collecting and _read(directory / 'capture' / 'capture.json') == body['capture'])
            require(_read(directory / 'capture' / 'capture-intent.json') == {'target': target})
            plan = _read(directory / 'capture' / 'capture-plan.json')
            if plan is not None:
                qualify_target_plan(target, plan)
            if body['capture']['bundle_validated']:
                from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_contracts import validate_rna_structure_bundle
                require(plan is not None)
                bundle = validate_rna_structure_bundle(self._bundle(body), plan=plan)
            if verify_artifacts:
                validate_capture(self.store, body['capture'], bundle=bundle)
        else:
            require(not collecting)
        if body['source_ref'] is None:
            require(not body['record_refs'] and (not body['rows']) and (body['prepared'] is None))
        else:
            require(collecting and bundle is not None and (body['record_refs'] == [body['source_ref']]))
            source = self.store.get(body['source_ref'])
            require(source.get('record_type') == 'source' and source.get('origin') == 'tool' and ({k: v for k, v in source.items() if k not in {'id', 'record_type', 'origin'}} == rna_structure_source_payload(bundle=bundle, capture=body['capture'], prepared=original['prepared'] if saved else body['prepared'])))
        publication = None
        if body['prepared'] is not None:
            require(_read(directory / 'grading' / 'prepared.json') == body['prepared'])
            publication = _read(directory / 'publication.json')
            require(all((publication[key] == body[key] for key in ('source_ref', 'record_refs', 'rows'))))
            if verify_artifacts:
                validate_prepared_rna_grading(self.store, body['prepared'], bundle=bundle, capture=body['capture'], selector=selector)
                require(publication == publish_selected_rna_structure_rows(self.store, context, source_ref=body['source_ref'], bundle=bundle, capture=body['capture'], prepared=body['prepared'], selector=selector))
        else:
            require(not body['rows'])
        for row in body['rows']:
            validate_rna_structure_row(row)
            require(row['family'] == selector['projection']['family'] and row['source_ref'] == body['source_ref'])
        base_failures = _read(directory / 'failure-ledger.json')
        expected = prepare_rna_structure_failure_selection(failures=base_failures, selector=selector, record_key=target['assignment']['requested_job']['native_rna_structure']['record_key'])
        require(expected == {'failures': failures, 'selection': body['failure_selection']})
        if collecting and publication is not None:
            require(base_failures == publication['failures'])
        elif collecting and (not saved) and (bundle is None):
            require(base_failures == body['capture']['failures'])
        elif collecting and bundle is not None and (body['prepared'] is None):
            failure = _read(directory / 'preparation-failure.json')
            require(base_failures == merge_issues([] if saved else bundle['failures'], [] if saved else body['capture']['failures'], [failure]))
        elif not collecting and (not saved):
            require(not base_failures)
        native = saved and body['native_success'] or (bundle is not None and bundle['returncode'] == 0 and (bundle['native_status'] == 'complete'))
        capture_complete = body['capture'] is not None and body['capture']['capture_complete']
        accounted = expected['selection']['requested_rows_accounted_for'] if expected['selection'] is not None else publication is not None and publication['requested_cells_accounted_for']
        sheet_available = body['prepared'] is not None and body['prepared']['sheet_artifact_ref'] is not None
        complete = collecting and body['source_ref'] is not None and accounted and (sheet_available if saved else capture_complete)
        require(all((type(body[key]) is bool for key in ('native_success', 'capture_complete', 'delivery_complete'))))
        require(body['native_success'] == bool(native) and body['capture_complete'] == bool(capture_complete) and (body['delivery_complete'] == bool(complete)))
        return deepcopy(body)

    @staticmethod
    def _outcome(body):
        return {'status': 'completed', 'record_refs': body['record_refs'], 'changed_record_refs': body['record_refs'], 'result': body, 'feedback': None}

    def _own_bodies(self, context, *, verify_artifacts=False):
        self.records.authenticate(context, allow_unsaved=True)
        directory = self._saved_directory(context.episode_id, 'unused').parent
        bodies = [_read(path) for path in directory.glob('*/receipt.json')] if directory.exists() else []
        for body in sorted(bodies, key=lambda item: int(item['operation_key'].rsplit(':', 1)[1])):
            require(body['episode_id'] == context.episode_id and body['assignment'] == plain(context.assignment))
            yield self._validate_body(body, context.scope, verify_artifacts=verify_artifacts)

    def facts(self, context, *, verify_artifacts=True):
        requested = {node.get('x-source') for node in (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {}).get('properties', {}).values()}
        bodies = list(self._own_bodies(context, verify_artifacts=verify_artifacts))
        refs = list(dict.fromkeys((ref for body in bodies for ref in body['record_refs'])))
        result = {'execution_handoff_refs': [], 'execution_blast_hsps': [], 'execution_result_refs': refs, REFERENCE_SOURCE: refs, SAVED_SOURCE: [], **{source: [] for source in FAMILY_SOURCES.values()}, 'execution_completed': any((body['delivery_complete'] for body in bodies)), 'execution_result_origin': deepcopy(ORIGIN) if any((body['native_success'] and body['capture_complete'] and (body['assignment']['selector']['acquisition'] == 'complete_bound_bundle') for body in bodies)) else None}
        for body in bodies:
            selector = body['assignment']['selector']
            family = selector['projection']['family']
            if FAMILY_SOURCES[family] in requested and family != 'failure':
                result[FAMILY_SOURCES[family]].extend(body['rows'])
            if FAMILY_SOURCES['failure'] in requested:
                result[FAMILY_SOURCES['failure']].extend(project_rna_structure_failure_rows(body, selector=selector if family == 'failure' else None))
            if SAVED_SOURCE in requested:
                descriptor = self.saved_descriptor(body, verify_bytes=verify_artifacts)
                if descriptor is not None:
                    result[SAVED_SOURCE].append(descriptor)
        for source in (*FAMILY_SOURCES.values(), SAVED_SOURCE):
            distinct = []
            for row in result[source]:
                if row not in distinct:
                    distinct.append(row)
            result[source] = distinct
        return result

    def resolve(self, context, reference, namespace):
        if not self.applies(context):
            return False
        facts = self.facts(context)
        rows = [row for source in FAMILY_SOURCES.values() for row in facts[source]]
        key = dict(zip(IDENTIFIER_NAMESPACES, ('row_key', 'calculation_key', 'result_receipt_key'))).get(namespace)
        if key:
            return any((row.get(key) == reference for row in rows)) or (namespace == IDENTIFIER_NAMESPACES[2] and any((row['result_receipt_key'] == reference for row in facts[SAVED_SOURCE])))
        allowed = set(facts[REFERENCE_SOURCE])
        allowed.update((row[name] for row in facts[SAVED_SOURCE] for name in ('handoff_ref', 'source_ref', 'bundle_artifact_ref', 'sheet_artifact_ref')))
        if reference not in allowed:
            return False
        return namespace not in {'source', 'artifact'} or self.store.get(reference)['record_type'] == namespace

    def retained_reference_access(self, context, reference, namespace):
        return retained_reference_access(self, context, reference, namespace)

def retained_reference_access(results, context, reference, namespace):
    """Deny accidental custody expansion, preserving independent operands."""
    if namespace not in {None, 'source', 'artifact', 'execution_result'}:
        return None
    store = results.store
    try:
        record = store.get(reference)
    except (ValueError, KeyError):
        return None
    version = 'native_rna_structure_bundle_v1'
    if record['record_type'] == 'source':
        owns = record.get('provider') == 'episode.execution_result' and record.get('version') == version
    elif record['record_type'] == 'artifact':
        owns = store.db.execute("SELECT 1 FROM records r WHERE r.record_type='source' AND json_extract(r.data,'$.provider')='episode.execution_result' AND json_extract(r.data,'$.version')=? AND (json_extract(r.data,'$.artifact_ref')=? OR EXISTS (SELECT 1 FROM json_each(r.data,'$.auxiliary_artifact_refs') a WHERE a.value=?)) LIMIT 1", (version, reference, reference)).fetchone() is not None
        if not owns:
            owns = store.db.execute("SELECT 1 FROM runtime_actions a WHERE a.run_id=? AND json_extract(a.result,'$.result.version')=? AND EXISTS (SELECT 1 FROM json_each(a.result,'$.result.prepared') p WHERE p.key IN ('sheet_artifact_ref','components_artifact_ref','grading_artifact_ref','selected_rows_artifact_ref','diagnostics_artifact_ref','worker_receipt_artifact_ref') AND p.value=?) LIMIT 1", (context.run_id, VERSION, reference)).fetchone() is not None
    else:
        return None
    if not owns:
        return None
    results.records.authenticate(context, allow_unsaved=True)
    assignment = plain(context.assignment)
    job = assignment.get('requested_job', {}).get('native_rna_structure', {})
    explicit = {row.get('artifact_ref') for row in job.get('operands', [])}
    if reference in explicit:
        from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_result_publication import validate_rna_structure_job_inputs
        return reference in validate_rna_structure_job_inputs(store, context, assignment)
    saved = assignment.get('selector', {}).get('saved_input')
    if saved is not None and reference in {saved[key] for key in ('handoff_ref', 'source_ref', 'bundle_artifact_ref', 'sheet_artifact_ref')}:
        results.owner.native_rna_structure_returns.resolve_saved_rna_input(context, saved)
        return namespace in {None, 'execution_result', record['record_type']}
    if reference in store._refs(assignment) and reference in set(EpisodeReceipts(store, context.run_id).known(context.episode_id, baseline=True)):
        return namespace in {None, 'execution_result', record['record_type']}
    requested = {node.get('x-source') for node in (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {}).get('properties', {}).values()}
    if context.role == 'results' and SAVED_SOURCE in requested:
        for body in results._own_bodies(context):
            action = results.owner._selected_result_action(context.episode_id, body['operation_key'], body['tool_name'], body['arguments'])
            if action['result'] is None:
                continue
            descriptor = results.saved_descriptor(body, verify_bytes=False)
            if descriptor is not None and reference in {descriptor[key] for key in ('handoff_ref', 'source_ref', 'bundle_artifact_ref', 'sheet_artifact_ref')}:
                retained(store, descriptor['sheet_artifact_ref'])
                if record['record_type'] == 'artifact':
                    retained(store, reference)
                return namespace in {None, 'execution_result', record['record_type']}
    scope = store.validate_scope(plain(context.scope))
    for subject in scope.get('subject_refs', []):
        if store.get(subject).get('sequence_ref') == reference:
            return namespace in {None, 'artifact'}
    for action in store.db.execute('SELECT result FROM runtime_actions WHERE run_id=? AND episode_id=? AND result IS NOT NULL', (context.run_id, context.episode_id)):
        outcome = json.loads(action['result'])
        if outcome.get('status') in {'completed', 'partial'} and reference in outcome.get('record_refs', []):
            body = outcome.get('result')
            if isinstance(body, dict) and body.get('version') == VERSION:
                results._validate_body(body, context.scope)
            return namespace in {None, 'execution_result', record['record_type']}
    received = results.owner.native_rna_structure_returns.resolve_received(context, reference, namespace)
    if received is not None:
        return received
    boundary = results.owner.native_rna_structure_returns
    from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_dependencies.native_rna_structure_returns import requested_sources
    for attempt in boundary._attempts(context):
        schema = json.loads(attempt['contract']).get('measurements', {}).get('schema', {})
        if requested_sources(schema):
            continue
        child, form, schema = boundary._attempt(context, attempt['decision_index'])
        references = []

        def collect(value, declared_namespace):
            if declared_namespace in {None, record['record_type']}:
                references.append(value)
            return True
        validate_form(form, schema, collect)
        if reference in references:
            return namespace in {None, 'execution_result', record['record_type']}
    return False
