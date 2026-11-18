"""Exact original typed admission and recursion over controlled saved records.

This is not a historical Store replay, native producer test or full Workflow.
Original no-new-action/zero-observation, source possession and value assertions
are retained. A protocol mismatch is a baseline finding, never bypassed here.
"""
import pytest
from gene_annotation_episode.episodic_workflow.root.a101.state import Store
from gene_annotation_episode.episodic_workflow.root.a101.library.retained_input_authority.bvbrc_phylogeny_returns import FACT_SOURCES
from .bvbrc_phylogeny_saved_fixture import projection, fact_form, ref
from .bvbrc_phylogeny_return_fixture import ReturnFixture
from .test_bvbrc_phylogeny_saved_positive import no_acquisition_or_scientific_work

@pytest.fixture
def run(tmp_path):
    with Store(tmp_path / "state") as store:
        yield ReturnFixture(store)

def test_real_typed_admission_and_recursive_forwarding_keep_all_eight_families(run):
    body, sheet = projection()
    root = run.saved.root
    parent = run.child(root, "sequence_homology_evidence", body)
    producer = run.child(parent, "results", body)
    publication = run.publications.add(producer, body, sheet)
    schema = fact_form(*FACT_SOURCES)
    expected = run.host.facts(producer, schema)
    count = run.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0]
    assert run.host.received_context(root) == run.host.received_context(parent) == []
    _, _, _, references = run.admit(parent, producer, receive=False)
    assert references == [publication["source_ref"]]
    assert run.host.received_facts(parent, schema) == expected
    assert run.host.received_context(root) == []
    run.saved.receipts.receive(parent.episode_id, references, kind="child_form", source_index=0)
    run.admit(root, parent)
    assert run.host.received_facts(root, schema) == expected
    assert run.host.resolve_received(root, ref("function", "enzyme / original label"), "bvbrc_phylogeny_function")
    assert not run.host.resolve_received(root, ref("function", "not_received"), "bvbrc_phylogeny_function")
    assert run.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == count
    assert run.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
