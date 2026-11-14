"""Original explicit application-return protocol for an API without a private owner.

Private operational bindings supply their own complete directional bodies.
This default retains existing standalone API construction and saved readers.
"""
from __future__ import annotations
from copy import deepcopy
from ..communication import plain
from ..execution_contracts import canonical
from ..form_reference_validation import _binding_key, form_validation_value
from ..bvbrc_appservice_saved_results import read_latest_adapter_result
from .bvbrc_application_facts import FACT_SOURCE, IDENTIFIER_NAMESPACE, _ADAPTERS, requested_sources, project_application_facts


class StandaloneApplicationReturns:
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

    def _application_resolve_own(self, returns, context, reference, namespace):
        if namespace not in {None, "source", "execution_result", IDENTIFIER_NAMESPACE}:
            return None
        schema = (plain(context.request).get("report_contract") or {}).get("measurements", {}).get("schema", {})
        facts = form_validation_value((returns, "own", _binding_key(context), canonical(schema)), lambda: returns.facts(context, schema))
        return returns.records._resolve(context, facts.get(FACT_SOURCE, []), reference, namespace)

    def _application_resolve_received(self, returns, context, reference, namespace):
        if namespace not in {None, "source", "execution_result", IDENTIFIER_NAMESPACE}:
            return None
        groups = form_validation_value((returns, "received", _binding_key(context)), lambda: returns.received_context(context))
        return returns.records._resolve(context, [row for group in groups for row in group["facts"]], reference, namespace)


    def _application_resolve_reference(self, returns, context, reference, namespace):
        return (returns.resolve_own(context, reference, namespace)
            if context.role == 'results' else
            returns.resolve_received(context, reference, namespace))

