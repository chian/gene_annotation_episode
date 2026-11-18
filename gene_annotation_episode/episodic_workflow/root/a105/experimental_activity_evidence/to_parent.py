"""to parent for this private A105 episode."""
from __future__ import annotations
from .scientific_contracts import build_process_result, merge_process_results, plain, report_sources, scientific_digest, validate_form, validate_process_result
from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError

class ScientificReport:

    def required_return_sources(self, parent, role):
        self._role(role)
        if parent is not None and getattr(self.services, 'annotation_task_required', lambda: False)():
            if len(parent.path) == 1:
                return ('experimental_activity_evidence_results', 'committed_record_refs')
            return ('committed_record_refs',)
        return ()

    def fact_sources(self, role):
        self._role(role)
        return report_sources(self.library, self.tool_library)

    def facts(self, context, completion_snapshot):
        from gene_annotation_episode.episodic_workflow.root.a105.experimental_activity_evidence_reports import project_process_result
        self.validate_context(context)
        own = build_process_result(context, completion_snapshot)
        read_received = getattr(self.services, 'scientific_received_results_for', None)
        received = (read_received(private_received_results, context) if callable(read_received)
            else self.services.scientific_received_results(context))

        def project(value):
            return project_process_result(value, library=self.library, tool_library=self.tool_library)
        facts = {'experimental_activity_evidence_results': merge_process_results(None if own is None else project(own), [project(value) for value in received])}
        return facts

    def validate_report(self, context, form, original_schema):
        self.validate_context(context)
        validate_form(form, original_schema, lambda reference, namespace: self.resolve(context, reference, namespace))
        fields = [name for name, node in plain(original_schema)['properties'].items() if node.get('x-source') == 'experimental_activity_evidence_results']
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
                    raise ValueError('experimental_activity_evidence_result_source_mismatch')
            except ValueError as error:
                raise ReportBoundaryError('Return differs from the original process result', code=str(error), field=name) from error

from ..experimental_activity_evidence_provenance import _detached, _load

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
            row = provenance.store.db.execute("""SELECT
                json_type(facts, '$.experimental_activity_evidence_results') AS source_type,
                json_extract(facts, '$.experimental_activity_evidence_results') AS results
                FROM runtime_forms WHERE run_id=? AND episode_id=?""",
                (provenance.journal.run_id, context.episode_id)).fetchone()
            if row is None or row["source_type"] is None:
                return None
            if row["source_type"] != "array":
                raise ValueError("scientific_frozen_results_invalid")
            return _detached(_load(row["results"]))

