"""Independent narrow probe of actual source-only immediate-child admission.

The imported harness uses a synthetic local PBS/native-byte emitter. No BLAST,
database search, remote transport, API, credentials or model call occurs.
"""
import json

from gene_annotation_episode.native_blast_database_results import REFERENCE_SOURCE
from gene_annotation_episode.native_blast_database_result_publication import _known
from test_native_blast_database_episode_binding import schema_for
from test_native_blast_vdb_function_integration import connected_fixture, results_child


def test_source_only_return_does_not_admit_unrequested_native_artifacts(tmp_path, monkeypatch):
    h, selector = connected_fixture(tmp_path, monkeypatch)
    try:
        child = results_child(h, selector, schema=schema_for(REFERENCE_SOURCE), descriptors=False)
        outcome = h.select(child, 0, 'execution.results.collect')
        assert outcome['status'] == 'completed', outcome
        body = outcome['result']
        assert body['complete'], body['failures']
        source = h.store.get(body['publication']['source_ref'])
        before = _known(h.store, h.root)
        form, schema = h.returned(child)
        after = _known(h.store, h.root)
        auxiliary = set(source['auxiliary_artifact_refs'])
        unseen = auxiliary - before
        leaked = sorted(unseen & after)
        selected_refs = h.family.native_blast_database_returns._references({REFERENCE_SOURCE: [source['id']]})
        evidence = dict(form=form, schema=schema, explicitly_returned_refs=selected_refs,
            source_ref=source['id'], source_auxiliary_artifact_refs=sorted(auxiliary),
            previously_unknown_auxiliary_refs=sorted(unseen), newly_admitted_unrequested_artifacts=leaked,
            resolver_results={ref: h.family.resolve(h.root, ref, 'artifact') for ref in leaked},
            direct_return_resolver_results={ref: h.family.resolve_received_reference(h.root, ref, 'artifact') for ref in leaked},
            receipt_rows=[dict(row) for row in h.store.db.execute(
                'SELECT record_ref,receipt_kind,source_index FROM runtime_record_receipts WHERE run_id=? AND episode_id=?',
                (h.run_id,h.root.episode_id)) if row['record_ref'] in unseen])
        (tmp_path / 'source-only-admission-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
        assert unseen, 'probe requires actual previously unreceived auxiliary artifacts'
        assert not leaked, evidence
    finally:
        h.store.close()
