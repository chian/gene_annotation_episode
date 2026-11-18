"""Original standalone authenticated result readers."""
from ..sample_context_evidence_provenance import _detached, _load

def received_results(provenance, context):
        with provenance.store.read_snapshot():
            provenance._authenticate(context)
            return provenance._received_results(context.episode_id)

def frozen_results(provenance, context):
        """Read this original episode's literal closing source, without projection.

        Missing closure/source is distinct from a recorded empty array. Only the
        declared process-result position is loaded; other facts, interpretations
        and archived histories remain outside this validation port.
        """
        with provenance.store.read_snapshot():
            provenance._authenticate(context, require_saved=True)
            row = provenance.store.db.execute("SELECT\n                json_type(facts, '$.sample_context_evidence_results') AS source_type,\n                json_extract(facts, '$.sample_context_evidence_results') AS results\n                FROM runtime_forms WHERE run_id=? AND episode_id=?", (provenance.journal.run_id, context.episode_id)).fetchone()
            if row is None or row['source_type'] is None:
                return None
            if row['source_type'] != 'array':
                raise ValueError('scientific_frozen_results_invalid')
            return _detached(_load(row['results']))

