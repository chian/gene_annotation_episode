"""Private A106 launch to parent."""
from __future__ import annotations
from .execution_contracts import plain, validate_form

from gene_annotation_episode.episodic_workflow.root.a106.library.bvbrc_application_facts import FACT_SOURCE, IDENTIFIER_NAMESPACE, _ADAPTERS, requested_sources, project_application_facts
from gene_annotation_episode.episodic_workflow.root.a106.bvbrc_appservice_saved_results import read_latest_adapter_result
from gene_annotation_episode.episodic_workflow.root.a106.execution_contracts import canonical
from gene_annotation_episode.episodic_workflow.root.a106.form_reference_validation import _binding_key, form_validation_value

class OperationalReport:

    def _application_facts(self, returns, context, schema):
        if not requested_sources(schema):
            return {}
        returns.records._authenticate(context)
        latest = read_latest_adapter_result(returns.records.api.appservice.publications, context, adapter_ids=_ADAPTERS)
        if latest is None:
            return {FACT_SOURCE: []}
        body, sheet, components = latest
        returns.records._original_invocation(context, body)
        values = project_application_facts(body, sheet=sheet, components=components)
        returns.records._possessed_sources(context, values[FACT_SOURCE])
        return values

    def _application_resolve_own(self, returns, context, reference, namespace):
        if namespace not in {None, "source", "execution_result", IDENTIFIER_NAMESPACE}:
            return None
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        facts = form_validation_value((returns, "own", _binding_key(context), canonical(schema)), lambda: returns.facts(context, schema))
        return returns.records._resolve(context, facts.get(FACT_SOURCE, []), reference, namespace)

    def _application_resolve_reference(self, returns, context, reference, namespace):
        return (returns.resolve_own(context, reference, namespace)
            if context.role == 'results' else
            returns.resolve_received(context, reference, namespace))



    def required_return_sources(self, parent, role):
        """Preserve the original job identity across a scientific return."""
        self.credit_kind(role)
        if parent is not None and parent.path[-1][0] == 'perturbation_evidence' and getattr(self.services, 'annotation_task_required', lambda: False)():
            return ('execution_handoff_refs',)
        return ()

    def fact_sources(self, role):
        values = self._appservice_sources()
        for key, namespace, meaning in (('execution_handoff_refs', 'execution_handoff', 'Qualified original handoff sources actually available to this episode.'), ('execution_result_refs', 'execution_result', 'Qualified actual requested result acquisitions available to this episode.')):
            values[key] = {'type': 'array', 'meaning': meaning, 'report_schema': {'type': 'array', 'uniqueItems': True, 'items': {'type': 'string', 'format': 'reference', 'x-reference-namespace': namespace}, 'x-source': key}}
        values['execution_completed'] = {'type': 'boolean', 'meaning': 'Whether this assignment has actual verified endpoint information. Yielding alone is false.'}
        return values

    def facts(self, context, completion_snapshot):
        return {**self._live_facts(context, completion_snapshot), **self._closed_credit_facts(context, completion_snapshot)}

    def _live_facts(self, context, completion_snapshot):
        with self.store.read_snapshot():
            read = self.job_progress_provider.targets._handoff_reader()
            _, handoffs, _ = self._received(context, _handoff_read=read)
            return {'execution_handoff_refs': sorted(handoffs), 'bvbrc_appservice_support_refs': self.api_execution.appservice.received_support_refs(context), 'execution_result_refs': [], 'execution_completed': any((read(reference, context.scope)[1] for reference in handoffs))}

    def resolve(self, context, reference, namespace):
        try:
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

            if self.api_execution.resolve(context, reference, namespace):
                return True
            if self.api_execution.is_handoff_source(reference):
                return False
            if self.services is not None:
                from gene_annotation_episode.episodic_workflow.root.a106.episode_bindings import reference_in_context
                return bool(reference_in_context(self.services, context, reference, namespace))
            source = self.store.get(reference)
            kind = source['record_type']
            return bool(self.store.reference_subset([reference], plain(context.scope)) and (namespace in {None, kind} or (namespace == 'subject' and kind in {'input', 'feature', 'product', 'read_subject'})))
        except (ValueError, KeyError, OSError):
            return False

    def validate_report(self, context, form, original_schema):
        validate_form(form, original_schema, lambda ref, ns: self.resolve(context, ref, ns))
        fact_fields = {name: declared['x-source'] for name, declared in plain(original_schema).get('properties', {}).items() if declared.get('x-source') is not None}
        if not fact_fields:
            return
        facts = self.facts(context, {})
        for name, source in fact_fields.items():
            if source in facts and form[name] != facts[source]:
                raise ValueError('execution_report_disagrees_with_recorded_facts')
