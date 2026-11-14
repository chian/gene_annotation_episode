"""Private scientific to parent."""
from __future__ import annotations
from .scientific_contracts import ReportBoundaryError, _SCIENTIFIC_NAMESPACES, plain, reference_in_context, report_sources, scientific_digest, validate_form, validate_process_result
from collections.abc import Mapping
from ..method_loop.durable import canonical
from ..method_loop.episode import EpisodeCompletion
from ..scientific_process_records import (_plain, _exact, validate_invocation_ref,
    scientific_invocation_ref, validate_revision_origin)
from ..scientific_process_reports import VERSION, _CREDIT_KINDS, credit_binding_ref

def build_process_result(context, completion_snapshot):
    """Copy one actual closure; never manufacture or refit a closing value."""
    if not isinstance(completion_snapshot, Mapping):
        raise ValueError("scientific_process_completion_snapshot_invalid")
    if completion_snapshot.get("completion") is None:
        return None
    snapshot = _plain(completion_snapshot)
    completion = snapshot["completion"]
    _exact(completion, "ended_by end_reason units_consumed", "scientific_process_completion_invalid")
    EpisodeCompletion(**completion)
    try:
        count = snapshot["own_action_count"]
        if type(count) is not int or count != completion["units_consumed"]:
            raise ValueError("scientific_process_completion_count_mismatch")
        assignment = _plain(context.assignment)
        message = context.request["message"]
        if assignment != _plain(message["episode_assignment"]):
            raise ValueError("scientific_process_result_assignment_mismatch")
        invocation = validate_invocation_ref(message["scientific_invocation_ref"])
        if invocation != scientific_invocation_ref(context.run_id, context.path):
            raise ValueError("scientific_process_result_invocation_mismatch")
        parent = snapshot["parent_invocation_ref"]
        if parent is not None and (len(context.path) < 2 or
                parent != scientific_invocation_ref(context.run_id, context.path[:-1])):
            raise ValueError("scientific_process_result_parent_mismatch")
        origin = assignment.get("revision_origin")
        if "revision_origin" in assignment:
            origin = validate_revision_origin(origin)
            if origin["parent_invocation_ref"] != parent:
                raise ValueError("scientific_process_result_origin_mismatch")
        metadata = snapshot["controller_credit"]
        kind = None
        if metadata is not None:
            _exact(metadata, "credit_kind credit_binding", "scientific_process_credit_metadata_invalid")
            kind = metadata["credit_kind"]
            if (kind not in _CREDIT_KINDS or not isinstance(metadata["credit_binding"], dict)
                    or not metadata["credit_binding"]):
                raise ValueError("scientific_process_credit_metadata_invalid")
        return validate_process_result({"version": VERSION, "invocation_ref": invocation,
            "parent_invocation_ref": parent,
            "origin_kind": "ordinary_child" if origin is None else "approach_revision",
            "preparation_operation_ref": None if origin is None else origin["preparation_operation_ref"],
            "selection": assignment["selection"], "initial_credit": snapshot["initial_credit"],
            "credit": snapshot["credit"], "credit_kind": kind,
            "credit_binding_ref": credit_binding_ref(metadata), "completed_actions": count,
            "episode_yield": snapshot["episode_yield"],
            **({'proposed_annotation_ref': assignment['proposed_annotation_ref']}
               if assignment.get('proposed_annotation_ref') else {})})
    except (KeyError, AttributeError, TypeError) as error:
        raise ValueError("scientific_process_completion_snapshot_invalid") from error

def merge_process_results(own_result, received_results):
    """Stable own-first union; the same invocation cannot acquire a new body."""
    if not isinstance(received_results, (list, tuple)):
        raise ValueError("scientific_process_results_invalid")
    results, known = [], {}
    for candidate in ([own_result] if own_result is not None else []) + list(received_results):
        row = validate_process_result(candidate)
        invocation = row["invocation_ref"]
        body = canonical(row)
        if invocation in known:
            if known[invocation] != body:
                raise ValueError("scientific_process_result_conflict")
            continue
        known[invocation] = body
        results.append(row)
    return results

class ScientificReport:

    def required_return_sources(self, parent, role):
        self._role(role)
        if parent is not None and getattr(self.services, 'annotation_task_required', lambda: False)():
            if len(parent.path) == 1:
                return ('scientific_process_results', 'committed_record_refs')
            return ('committed_record_refs',)
        return ()

    def fact_sources(self, role):
        self._role(role)
        return report_sources(self.library, self.tool_library)

    def facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a106.scientific_process_reports import project_process_result
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        read_received = getattr(self.services, 'scientific_received_results_for', None)
        received = (read_received(private_received_results, context) if callable(read_received)
            else self.services.scientific_received_results(context))

        def project(value):
            return project_process_result(value, library=self.library, tool_library=self.tool_library)
        facts = {'scientific_process_results': merge_process_results(None if own is None else project(own), [project(value) for value in received])}
        facts.update(self._component_scoring_facts(context))
        return facts

    def resolve(self, context, reference, namespace):
        self.validate_context(context)
        if namespace is None or namespace in _SCIENTIFIC_NAMESPACES:
            if self.services.scientific_reference(context, reference, namespace):
                return True
            if namespace in _SCIENTIFIC_NAMESPACES:
                return False
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        self.validate_context(context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        fields = [name for name, node in plain(original_schema)['properties'].items() if node.get('x-source') == 'scientific_process_results']
        if not fields:
            return
        try:
            read_frozen = getattr(self.services, 'scientific_frozen_results', None)
            if not callable(read_frozen):
                raise ValueError('scientific_frozen_results_unavailable')
            private_read = getattr(self.services, 'scientific_frozen_results_for', None)
            frozen = (private_read(private_frozen_results, context) if callable(private_read)
                else read_frozen(context))
        except ValueError as error:
            raise ReportBoundaryError('Original process results unavailable', code=str(error), field=fields[0]) from error
        for name in fields:
            values = plain(form)[name]
            try:
                for value in values:
                    validate_process_result(value, library=self.library, tool_library=self.tool_library)
                if frozen is None or scientific_digest(values) != scientific_digest(frozen):
                    raise ValueError('scientific_process_result_source_mismatch')
            except ValueError as error:
                raise ReportBoundaryError('Return differs from the original process result', code=str(error), field=name) from error


from ..scientific_process_provenance import _detached, _load

def private_received_results(provenance, context):
    with provenance.store.read_snapshot():
        provenance._authenticate(context)
        return provenance._received_results(context.episode_id)

def private_frozen_results(provenance, context):
    """Read this original episode's literal closing source, without projection.

        Missing closure/source is distinct from a recorded empty array. Only the
        declared process-result position is loaded; other facts, interpretations
        and archived histories remain outside this validation port.
        """
    with provenance.store.read_snapshot():
        provenance._authenticate(context, require_saved=True)
        row = provenance.store.db.execute("SELECT\n                json_type(facts, '$.scientific_process_results') AS source_type,\n                json_extract(facts, '$.scientific_process_results') AS results\n                FROM runtime_forms WHERE run_id=? AND episode_id=?", (provenance.journal.run_id, context.episode_id)).fetchone()
        if row is None or row['source_type'] is None:
            return None
        if row['source_type'] != 'array':
            raise ValueError('scientific_frozen_results_invalid')
        return _detached(_load(row['results']))
