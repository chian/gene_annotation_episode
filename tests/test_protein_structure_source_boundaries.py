"""Source-only receipt and generic result exclusions, using real Store records.

The protein bundle bytes are deliberately synthetic and not a scientific result.
These checks exercise the actual receipt, selection and resolver methods; they
do not assert a protein descriptor grant or production protein-host integration.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_journal import Journal
from gene_annotation_episode.episode_receipts import EpisodeReceipts
from gene_annotation_episode.execution_episodes import ExecutionEpisodes, RESULT_PROVIDER
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


PROTEIN_VERSION = "native_protein_structure_bundle_v1"
NATIVE_RESULT_VERSIONS = (
    "native_hmmer_bundle_v1", "native_blast_bundle_v1",
    "native_blast_database_bundle_v1", "native_blast_standard_database_bundle_v1",
    "native_infernal_bundle_v1", "native_infernal_preparation_bundle_v1",
    "native_hmmer_preparation_bundle_v1", "native_rna_structure_bundle_v1",
    PROTEIN_VERSION,
)


def source_record(store, *, version=PROTEIN_VERSION, provider=RESULT_PROVIDER):
    bundle = store.artifact(b"Synthetic bundle bytes; not native protein output.")
    selected = store.artifact(b"Explicitly selected synthetic artifact.")
    hidden = store.artifact(b"Unrequested synthetic auxiliary artifact.")
    source = store.put("source", {"provider": provider,
        "accession": "source-boundary-fixture", "uri": None,
        "artifact_ref": bundle, "text_ref": None, "request_ref": None,
        "version": version, "retrieved_at": None,
        "auxiliary_artifact_refs": [selected, hidden]}, origin="tool")["id"]
    return source, bundle, selected, hidden


def receipt_rows(store):
    return [tuple(row) for row in store.db.execute(
        "SELECT * FROM runtime_record_receipts ORDER BY receipt_index")]


def forbid_bytes(*args, **kwargs):
    pytest.fail("source classification must not read artifact bytes")


@pytest.mark.parametrize("kind", ["initial", "decision_input", "own_action",
    "child_form", "report_redelivery"])
def test_protein_source_receipt_is_not_an_auxiliary_grant_and_freezes_inheritance(
        tmp_path, monkeypatch, kind):
    with Store(tmp_path / "store") as store:
        source, bundle, selected, hidden = source_record(store)
        original = deepcopy(store.get(source))
        Journal(store, "boundary-run")
        receipts = EpisodeReceipts(store, "boundary-run")
        receipts.bind("parent")
        monkeypatch.setattr(store, "get_artifact", forbid_bytes)
        receipts.receive("parent", [source], kind=kind, source_index=0)
        assert set(receipts.known("parent")) == {source}
        frozen = receipts.bind("child", "parent")
        receipts.bind("grandchild", "child")
        receipts.receive("parent", [selected, source], kind=kind, source_index=1)
        assert set(receipts.known("parent")) == {source, selected}
        assert set(receipts.known("child")) == {source}
        assert set(receipts.known("grandchild")) == {source}
        receipts.bind("later_child", "parent")
        assert set(receipts.known("later_child")) == {source, selected}
        before = receipt_rows(store)
        receipts.receive("parent", [source, selected], kind=kind, source_index=2)
        assert receipt_rows(store) == before
        assert store.get(source) == original
        assert store.get(bundle)["record_type"] == store.get(hidden)["record_type"] == "artifact"
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    with Store(tmp_path / "store") as store:
        receipts = EpisodeReceipts(store, "boundary-run")
        assert receipts.bind("child", "parent") == frozen
        assert set(receipts.known("child")) == {source}
        assert set(receipts.known("grandchild")) == {source}
        assert set(receipts.known("later_child")) == {source, selected}
        assert receipt_rows(store) == before


@pytest.mark.parametrize("source_first", [False, True])
def test_explicit_artifact_in_same_delivery_survives_source_exclusion(
        tmp_path, monkeypatch, source_first):
    with Store(tmp_path / "store") as store:
        source, bundle, selected, hidden = source_record(store)
        receipts = EpisodeReceipts(store, "boundary-run")
        receipts.bind("parent")
        monkeypatch.setattr(store, "get_artifact", forbid_bytes)
        references = [source, selected] if source_first else [selected, source]
        receipts.receive("parent", references, kind="child_form", source_index=0)
        assert set(receipts.known("parent")) == {source, selected}
        assert bundle not in set(receipts.known("parent"))
        assert hidden not in set(receipts.known("parent"))


@pytest.mark.parametrize(("provider", "version"), [
    ("caller", PROTEIN_VERSION), (RESULT_PROVIDER, "ordinary_source_v1")])
def test_unrelated_source_dependencies_are_unchanged(tmp_path, monkeypatch, provider, version):
    with Store(tmp_path / "store") as store:
        references = source_record(store, provider=provider, version=version)
        receipts = EpisodeReceipts(store, "boundary-run")
        receipts.bind("parent")
        monkeypatch.setattr(store, "get_artifact", forbid_bytes)
        receipts.receive("parent", [references[0]], kind="child_form")
        assert set(receipts.known("parent")) == set(references)


@pytest.mark.parametrize("version", ["native_infernal_preparation_bundle_v1",
    "native_hmmer_preparation_bundle_v1", "native_blast_database_bundle_v1",
    "native_rna_structure_bundle_v1"])
def test_existing_native_receipt_exclusions_are_unchanged(tmp_path, version):
    with Store(tmp_path / "store") as store:
        source, _, _, _ = source_record(store, version=version)
        receipts = EpisodeReceipts(store, "boundary-run")
        receipts.bind("parent")
        receipts.receive("parent", [source], kind="child_form")
        assert set(receipts.known("parent")) == {source}


@pytest.fixture
def execution_host(tmp_path):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="MARGKKIGYS", molecule="protein")["subject_refs"]
        journal = Journal(store, "boundary-run")
        receipts = EpisodeReceipts(store, journal.run_id)
        receipts.bind("receiver")
        workspace = tmp_path / "project"
        workspace.mkdir()
        family = ExecutionEpisodes(None, store=store, directory=tmp_path / "run",
            run_id=journal.run_id, resources={"here": {"kind": "local",
                "workspace": str(workspace), "policy": {'memory_bytes': 21474836480, 'scratch_bytes': 4294967296}}},
            initial_information={}, tool_registry=ToolRegistry(store), handoff_unit=3,
            acquired_record_unit=2, log_window_bytes=4, log_roles=["stdout", "stderr"])
        context = BindingContext(journal.run_id, "receiver", "scientific_process",
            (("scientific_process", "receiver"),), {"subject_refs": [target]}, {}, {})
        yield SimpleNamespace(store=store, receipts=receipts, family=family, context=context)


@pytest.mark.parametrize("version", NATIVE_RESULT_VERSIONS)
def test_native_source_never_enters_generic_result_reader(execution_host, monkeypatch, version):
    h = execution_host
    source, _, _, _ = source_record(h.store, version=version)
    h.receipts.receive(h.context.episode_id, [source], kind="child_form")
    before = receipt_rows(h.store)

    def forbidden_result_reader(*args, **kwargs):
        pytest.fail("specialized native source entered generic _read_result")

    monkeypatch.setattr(h.family, "_read_result", forbidden_result_reader)
    monkeypatch.setattr(h.store, "get_artifact", forbid_bytes)
    selected, handoffs, results = h.family._received(h.context)
    assert source in selected["known_record_refs"]
    assert handoffs == results == {}
    for namespace in (None, "source", "execution_result", "artifact"):
        assert h.family.resolve(h.context, source, namespace) is False
    assert receipt_rows(h.store) == before
    assert h.store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0
    assert h.store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0


def test_same_version_from_unrelated_provider_remains_an_ordinary_source(execution_host, monkeypatch):
    h = execution_host
    source, _, _, _ = source_record(h.store, provider="caller")
    h.receipts.receive(h.context.episode_id, [source], kind="initial")
    monkeypatch.setattr(h.store, "get_artifact", forbid_bytes)
    selected, handoffs, results = h.family._received(h.context)
    assert source in selected["known_record_refs"]
    assert handoffs == results == {}
    assert h.family.resolve(h.context, source, "source") is True
