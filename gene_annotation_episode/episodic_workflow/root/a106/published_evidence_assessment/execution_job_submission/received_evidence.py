"""Private A106 launch received evidence."""
from __future__ import annotations
from .execution_contracts import plain

from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a106.library.bvbrc_application_facts import FACT_SOURCE, IDENTIFIER_NAMESPACE, requested_sources
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a106.form_reference_validation import _binding_key, form_validation_value

from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_custody import _references
from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_records import PROVIDER
from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_host import SUPPORT_SOURCE
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a106.communication import plain

class ReceivedOperationalEvidence:

    def _appservice_received_support_refs(self, host, context):
        host.custody.authenticate(context, allow_unsaved=True)
        rows = host.store.db.execute('SELECT decision_index FROM runtime_report_attempts WHERE run_id=? AND parent_episode_id=? AND form IS NOT NULL AND failure IS NULL ORDER BY decision_index', (host.run_id, context.episode_id)).fetchall()
        result = []
        for row in rows:
            _, form, schema = host.custody._attempt(context, row['decision_index'])
            for reference, namespace in _references(form, schema):
                if namespace not in {None, 'source', 'bvbrc_appservice_support'}:
                    continue
                if host.store.get(reference).get('provider') != PROVIDER:
                    continue
                record = host.records.read(reference)
                host.custody.possession(context, reference)
                if record['contract'] != 'TaskHandoff' and reference not in result:
                    result.append(reference)
        return result

    def _appservice_validate_received_report(self, host, context, form, schema):
        names = [name for name, node in plain(schema).get('properties', {}).items() if node.get('x-source') == SUPPORT_SOURCE]
        if names:
            expected = host.facts(context)[SUPPORT_SOURCE] if host.owns_context(context) else host.received_support_refs(context)
            if any((canonical(form[name]) != canonical(expected) for name in names)):
                raise ValueError('appservice_received_support_refs_conflict')


    def _application_received_context(self, returns, context):
        rows, seen = [], set()
        for child, form, schema in returns.records.received_attempts(context, allow_unsaved=True):
            if not requested_sources(schema):
                continue
            returns.records._validate_historical(child, form, schema, received_facts=lambda child_context, child_schema: returns.received_facts(child_context, child_schema))
            for row in returns.records._values(form, schema)[FACT_SOURCE]:
                key = canonical(row)
                if key not in seen:
                    rows.append(deepcopy(row)); seen.add(key)
        return [{"fact_source": FACT_SOURCE, "facts": rows}] if rows else []

    def _application_received_facts(self, returns, context, schema):
        if not requested_sources(schema):
            return {}
        groups = returns.received_context(context)
        return {FACT_SOURCE: groups[0]["facts"] if groups else []}

    def _application_validate_received_report(self, returns, context, form, schema):
        if not requested_sources(schema):
            return
        returns.records._authenticate(context)
        values = returns.records._values(plain(form), plain(schema))
        expected = returns.facts(context, schema) if context.role == "results" else returns.received_facts(context, schema)
        returns.records._require(context.role in {"results", "scientific_process", "annotation"}
            and returns.records._equal(values, expected), "returned_facts_conflict")
        returns.records._frozen(context, values)

    def _application_record_admission(self, returns, context, form, schema, operation_key):
        if not requested_sources(schema):
            return []
        child, saved, original_schema = returns.records._attempt(context, returns.records._admission_index(context, operation_key))
        returns.records._require(returns.records._equal(form, saved) and returns.records._equal(schema, original_schema), "admitted_form_conflict")
        returns.records._validate_historical(child, saved, original_schema, received_facts=lambda child_context, child_schema: returns.received_facts(child_context, child_schema))
        return list(dict.fromkeys(row["source_ref"] for row in returns.records._values(saved, original_schema)[FACT_SOURCE]))

    def _application_resolve_received(self, returns, context, reference, namespace):
        if namespace not in {None, "source", "execution_result", IDENTIFIER_NAMESPACE}:
            return None
        groups = form_validation_value((returns, "received", _binding_key(context)), lambda: returns.received_context(context))
        return returns.records._resolve(context, [row for group in groups for row in group["facts"]], reference, namespace)




    def _received(self, context, selection=None, *, _handoff_read=None):
        with self.store.read_snapshot():
            selection = self._selection(context, selection)
            read = self.job_progress_provider.targets._handoff_reader() if _handoff_read is None else _handoff_read
            handoffs = {}
            for reference in dict.fromkeys(selection['known_record_refs']):
                if not self.api_execution.is_handoff_source(reference):
                    continue
                try:
                    target, _, returnable = read(reference, context.scope)
                    self._context_target(context, target)
                except (ValueError, KeyError):
                    continue
                if returnable:
                    handoffs[reference] = target
            return (selection, handoffs, {})

    def received_report_sources(self, role):
        return self._appservice_sources() if role in {'annotation', 'scientific_process'} else {}

    def received_report_facts(self, context):
        schema = (plain(context.request).get('report_contract') or {}).get('measurements', {}).get('schema', {})
        result = {}
        if context.role in {'annotation', 'scientific_process'}:
            if any((node.get('x-source') == 'bvbrc_appservice_support_refs' for node in schema.get('properties', {}).values())):
                result['bvbrc_appservice_support_refs'] = self.api_execution.appservice.received_support_refs(context)
            application = self.api_execution.application_returns.received_facts(context, schema)
            if set(result).intersection(application):
                raise ValueError('received_report_fact_conflict')
            result.update(application)
        return result

    def resolve_received_reference(self, context, reference, namespace):
        fba = self._flux_balance_reference_access(context, reference, namespace)

        if fba is not None:
            return fba

        fluorescence = self._fluorescence_reference_access(context, reference, namespace)

        if fluorescence is not None:
            return fluorescence

        nmf = self._expression_nmf_reference_access(context, reference, namespace)

        if nmf is not None:
            return nmf

        atac = self._atac_reference_access(context, reference, namespace)

        if atac is not None:
            return atac

        chromatin = self._chromatin_reference_access(context, reference, namespace)

        if chromatin is not None:
            return chromatin

        access = self._protein_reference_access(context, reference, namespace)

        if access is not None:
            return access

        from gene_annotation_episode.episodic_workflow.root.a106.library.bvbrc_application_facts import IDENTIFIER_NAMESPACES
        if namespace in IDENTIFIER_NAMESPACES:
            if context.role == 'results':
                return None
            return self.api_execution.application_returns.resolve_received(context, reference, namespace)
        return self.api_execution.appservice.resolve(context, reference, namespace)

    def validate_received_report(self, context, form, schema):
        self.api_execution.appservice.validate_received_report(context, form, schema)
        self.api_execution.application_returns.validate_received_report(context, form, schema)

    def received_form_references(self, context, form, schema, operation_key):
        references = self.api_execution.application_returns.record_admission(context, form, schema, operation_key)
        native_references = set(references)
        for name, declared in plain(schema).get('properties', {}).items():
            if declared.get('x-source') in {'execution_handoff_refs', 'execution_result_refs', 'bvbrc_appservice_support_refs'}:
                for reference in form[name]:
                    namespace = declared['items'].get('x-reference-namespace')
                    already_admitted = namespace == 'execution_result' and reference in native_references
                    if not already_admitted and (not self.resolve(context, reference, namespace)):
                        raise ValueError('execution_received_reference_unqualified')
                    references.append(reference)
        return list(dict.fromkeys(references))
