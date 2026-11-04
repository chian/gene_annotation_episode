"""Private ORF operand snapshots through actual Store/sequence/library owners.

Inputs and external metadata are engineered. A mapped-product fixture uses the
existing sequence.view publisher before the snapshot baseline; no ORF native
call, ORF calculation, scientific worker or model runs. A real unexecuted root
provides receipt/table witnesses, not authentication of a selected ORF action.
"""
from copy import deepcopy
import hashlib
import json

import pytest

from gene_annotation_episode import materials, orf_measurements
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from tests.test_library_targets import library, members, work
from tests.test_runtime import FixtureController, ScriptedProvider


def _forbidden(*_args, **_kwargs):
    raise AssertionError("private operand preparation attempted ORF/model/native work")


def _credit(*_args, **_kwargs):
    return 0


@pytest.fixture(autouse=True)
def no_orf_execution(monkeypatch):
    monkeypatch.setattr(orf_measurements, "build_orf_sheet", _forbidden)
    monkeypatch.setattr(orf_measurements, "calculate_orf_components", _forbidden)
    monkeypatch.setattr("gene_annotation_episode.molecular_sequence_native.execute_molecular_sequence_request", _forbidden)
    monkeypatch.setattr("subprocess.Popen", _forbidden)
    monkeypatch.setattr("socket.create_connection", _forbidden)


def _root(store, tools, tmp_path):
    provider = ScriptedProvider([])
    scope = store.validate_scope()
    initial = list(scope["subject_refs"])
    for reference in scope["subject_refs"]:
        record = store.get(reference)
        if record["record_type"] == "input" and record.get("sequence_ref") is not None:
            initial.append(record["sequence_ref"])
    workflow = Workflow(store, tools, provider, tmp_path / "run", "orf-private-operand-control",
        lambda path, initial, **_kwargs: FixtureController(str(path), initial, 1), _credit,
        episode_record_receipts=True, initial_known_record_refs=initial)
    root = workflow.build("annotation", "root", "Inspect only a private input snapshot", scope)
    assert provider.contexts == []
    return workflow, root


def _state(store):
    names = [row[0] for row in store.db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ) if row[0] != "artifacts"]
    return {name: sorted((tuple(row) for row in store.db.execute(
        'SELECT * FROM "' + name.replace('"', '""') + '"'
    )), key=repr) for name in names}


def _known(workflow, root):
    return set(workflow.receipts.known(root.source.episode_id))


def _prepare(store, tools, workflow, root, reference, *, scope=None):
    """Only artifact registration may change; this helper grants no delivery."""
    before, known = _state(store), _known(workflow, root)
    result = tools._prepare_orf_sequence_operand(reference,
        scope=store.validate_scope() if scope is None else scope)
    assert set(result) == {"version", "subject", "sequence", "parent_mapping", "mapping_failure",
        "input_file", "associations", "footprint"}
    assert result["version"] == "ordinary_orf_sequence_operand_v1"
    assert result["subject"] == store.get(reference)
    assert result["associations"] == {key: value for key, value in result["subject"].items()
        if key.endswith(("_ref", "_refs"))}
    assert result["footprint"] == store.coverage(reference)
    raw = result["sequence"].encode("ascii")
    assert result["input_file"] == {"artifact_ref": "artifact_" + hashlib.sha256(raw).hexdigest(),
        "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "format": "ascii_sequence"}
    assert _state(store) == before and _known(workflow, root) == known
    assert workflow.provider.contexts == []
    assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 0
    assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 0
    assert store.db.execute("SELECT count(*) FROM runtime_model_calls").fetchone()[0] == 0
    return result


def _feature(store, parent, segments, strand="+"):
    return store.put("feature", {"subject_ref": parent, "kind": "sequence_region",
        "segments": segments, "strand": strand, "context_refs": []}, origin="caller")


def _external(store, *, sequence="aCgTuN"):
    """Offline external record fixture, not a live provider/acquisition claim."""
    artifact = store.artifact(b"engineered external sequence record", "text/plain")
    source = store.put("source", {"provider": "engineering_external_sequence_input",
        "accession": "offline-control", "uri": None, "artifact_ref": artifact, "text_ref": artifact,
        "request_ref": None, "version": "engineered_v1", "retrieved_at": None}, origin="external")
    reference = store.put("reference", {"reference_type": "dna", "source_ref": source["id"],
        "accession": "offline-sequence", "label": "offline lowercase sequence",
        "sequence_ref": None if sequence is None else store.artifact(sequence, "text/plain"),
        "molecule": "dna", "length": None if sequence is None else len(sequence),
        "term_refs": [], "context_refs": []}, origin="external")
    return source, reference


def _mapped_product(store, tools, target):
    result = work(tools, "sequence.view", {"subject_ref": target, "molecule": "dna",
        "segments": [{"start": 1, "end": 7}], "orientation": "reverse_complement"})
    return store.get(result["records"][0]["product_ref"])


def test_supplied_input_freezes_actual_symbols_and_can_share_an_already_received_file(tmp_path):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="ATGAAATAA", molecule="dna")["subject_refs"]
        tools = ToolRegistry(store)
        workflow, root = _root(store, tools, tmp_path)
        original = store.get(target)
        assert original["sequence_ref"] in _known(workflow, root)
        artifacts = store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0]
        snapshot = _prepare(store, tools, workflow, root, target)
        assert snapshot["sequence"] == "ATGAAATAA"
        assert snapshot["input_file"]["artifact_ref"] == original["sequence_ref"]
        assert snapshot["parent_mapping"] == {"version": "oriented_source_subject_path_v2",
            "units_per_symbol": 1, "symbol_length": 9,
            "path": [{"subject_ref": target, "start": 0, "end": 9, "unit": "nt", "strand": "+"}]}
        assert snapshot["mapping_failure"] is None
        assert store.db.execute("SELECT count(*) FROM artifacts").fetchone()[0] == artifacts
        assert materials.artifact_path(store, snapshot["input_file"]["artifact_ref"]).read_bytes() == b"ATGAAATAA"


def test_external_reference_preserves_lowercase_and_original_associations_without_receipt_grants(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="ATGTAA", molecule="dna")
        source, reference = _external(store)
        tools = ToolRegistry(store)
        workflow, root = _root(store, tools, tmp_path)
        assert reference["id"] not in _known(workflow, root)
        snapshot = _prepare(store, tools, workflow, root, reference["id"])
        assert snapshot["sequence"] == "aCgTuN" and snapshot["footprint"] == []
        assert snapshot["parent_mapping"]["path"] == [{"subject_ref": reference["id"],
            "start": 0, "end": 6, "unit": "nt", "strand": "+"}]
        assert snapshot["associations"]["source_ref"] == source["id"]
        assert snapshot["input_file"]["artifact_ref"] == reference["sequence_ref"]
        assert snapshot["input_file"]["artifact_ref"] not in _known(workflow, root)
        assert store.get(source["id"]) == source


@pytest.mark.parametrize("mapped", [False, True])
def test_nucleotide_products_distinguish_actual_mapping_from_legacy_aggregate_footprint(tmp_path, mapped):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="AATGCCGTTA", molecule="dna")["subject_refs"]
        tools = ToolRegistry(store)
        if mapped:
            product = _mapped_product(store, tools, target)
        else:
            product = store.put("product", {"parent_refs": [target], "molecule": "dna",
                "sequence_ref": store.artifact("ATGCCG", "text/plain"), "derivation": "extraction",
                "context_refs": [], "footprint": [{"target_ref": target, "start": 1, "end": 7, "unit": "nt"}]},
                origin="caller")
        workflow, root = _root(store, tools, tmp_path)
        snapshot = _prepare(store, tools, workflow, root, product["id"])
        assert snapshot["sequence"] == ("CGGCAT" if mapped else "ATGCCG")
        assert snapshot["footprint"] == [{"target_ref": target, "start": 1, "end": 7, "unit": "nt"}]
        if mapped:
            assert snapshot["parent_mapping"] == product["mapping"]
            assert snapshot["parent_mapping"]["path"] == [{"subject_ref": target,
                "start": 1, "end": 7, "unit": "nt", "strand": "-"}]
            assert snapshot["mapping_failure"] is None
            assert snapshot["associations"]["mapping_source_ref"] == product["mapping_source_ref"]
        else:
            assert snapshot["parent_mapping"] is None
            assert snapshot["mapping_failure"] == {"code": "subregion_mapping_unavailable"}


@pytest.mark.parametrize("molecule,sequence,segments,expected,path_bounds", [
    ("dna", "AACCGGTTACGT", [{"start": 0, "end": 2}, {"start": 8, "end": 12}], "ACGTTT", [(8, 12), (0, 2)]),
    ("rna", "AAUUGCCAAU", [{"start": 1, "end": 4}, {"start": 6, "end": 10}], "AUUGAAU", [(6, 10), (1, 4)]),
])
def test_compound_reverse_features_use_original_segment_order_and_actual_rna_model(
        tmp_path, molecule, sequence, segments, expected, path_bounds):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence=sequence, molecule=molecule)["subject_refs"]
        feature = _feature(store, target, segments, "-")
        tools = ToolRegistry(store)
        workflow, root = _root(store, tools, tmp_path)
        snapshot = _prepare(store, tools, workflow, root, feature["id"])
        assert snapshot["sequence"] == expected
        assert snapshot["parent_mapping"]["path"] == [{"subject_ref": target,
            "start": start, "end": end, "unit": "nt", "strand": "-"} for start, end in path_bounds]
        assert snapshot["parent_mapping"]["symbol_length"] == len(expected)
        assert snapshot["mapping_failure"] is None
        assert snapshot["associations"]["subject_ref"] == target
        assert snapshot["input_file"]["artifact_ref"] not in _known(workflow, root)


def test_lazy_packed_original_read_uses_actual_member_scope_without_get_artifact(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        _problem, target = library(store, tmp_path, molecule="dna")
        first, second = members(store, target)
        tools = ToolRegistry(store)
        selected = work(tools, "library.select", {"library_ref": target["id"], "member_refs": [first["member_ref"]]})
        scope = store.validate_scope(selected["scope"], parent_scope=store.validate_scope())
        workflow, root = _root(store, tools, tmp_path)
        component = store.get(first["member_ref"])["storage"]["components"]["sequence"]
        reference = "artifact_" + component["sha256"]
        assert store.db.execute("SELECT 1 FROM artifacts WHERE id=?", (reference,)).fetchone() is None
        before, known = _state(store), _known(workflow, root)
        with monkeypatch.context() as patch:
            patch.setattr(store, "get_artifact", _forbidden)
            snapshot = _prepare(store, tools, workflow, root, first["id"], scope=scope)
            with pytest.raises(ContractError, match="requested_measurement_outside_assigned_segments_or_members"):
                tools._prepare_orf_sequence_operand(second["id"], scope=scope)
        assert _state(store) == before and _known(workflow, root) == known
        assert snapshot["sequence"] == "ACGTTGCAACGT"
        assert snapshot["input_file"]["artifact_ref"] == reference
        assert snapshot["parent_mapping"]["path"] == [{"subject_ref": first["id"],
            "start": 0, "end": 12, "unit": "nt", "strand": "+"}]
        assert snapshot["footprint"] == [{"target_ref": target["id"], "member_ref": first["member_ref"],
            "start": 0, "end": 12, "unit": "nt"}]
        assert reference not in known and reference not in _known(workflow, root)
        assert store.get_artifact(reference) == b"ACGTTGCAACGT"


@pytest.mark.parametrize("kind,code", [("library", "library_is_not_a_sequence_operand"),
    ("reference", "referenced_record_has_no_sequence"), ("source", "sequence_operand_required")])
def test_whole_library_and_records_without_a_sequence_are_rejected(tmp_path, kind, code):
    with Store(tmp_path / "store") as store:
        if kind == "library":
            _problem, record = library(store, tmp_path, molecule="dna")
        else:
            store.create_problem(raw_sequence="ATGTAA", molecule="dna")
            source, reference = _external(store, sequence=None)
            record = source if kind == "source" else reference
        tools = ToolRegistry(store)
        workflow, root = _root(store, tools, tmp_path)
        before, known = _state(store), _known(workflow, root)
        with pytest.raises(ContractError, match=code):
            tools._prepare_orf_sequence_operand(record["id"], scope=store.validate_scope())
        assert _state(store) == before and _known(workflow, root) == known


def test_partial_scope_denies_a_full_scan_but_allows_the_actual_scoped_feature(tmp_path):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="CCATGAAATAAGG", molecule="dna")["subject_refs"]
        feature = _feature(store, target, [{"start": 2, "end": 11}])
        scope = store.validate_scope({"subject_refs": [target],
            "segments": [{"target_ref": target, "start": 2, "end": 11, "unit": "nt"}]})
        tools = ToolRegistry(store)
        workflow, root = _root(store, tools, tmp_path)
        before, known = _state(store), _known(workflow, root)
        with pytest.raises(ContractError, match="requested_measurement_outside_assigned_segments"):
            tools._prepare_orf_sequence_operand(target, scope=scope)
        assert _state(store) == before and _known(workflow, root) == known
        snapshot = _prepare(store, tools, workflow, root, feature["id"], scope=scope)
        assert snapshot["sequence"] == "ATGAAATAA"
        assert snapshot["parent_mapping"]["path"] == [{"subject_ref": target,
            "start": 2, "end": 11, "unit": "nt", "strand": "+"}]


@pytest.mark.parametrize("damage", ["missing", "corrupt"])
def test_missing_or_corrupt_sequence_bytes_are_not_relabelled_as_unavailable_mapping(tmp_path, damage):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="ATGTAA", molecule="dna")["subject_refs"]
        tools = ToolRegistry(store)
        workflow, root = _root(store, tools, tmp_path)
        reference = store.get(target)["sequence_ref"]
        path = store.path / "artifacts" / reference[9:11] / reference[9:]
        if damage == "missing":
            path.unlink()
        else:
            path.write_bytes(b"AAAAAA")
        before, known = _state(store), _known(workflow, root)
        with pytest.raises(FileNotFoundError if damage == "missing" else ContractError,
                match=None if damage == "missing" else "artifact_digest_mismatch"):
            tools._prepare_orf_sequence_operand(target, scope=store.validate_scope())
        assert _state(store) == before and _known(workflow, root) == known


def test_corrupted_real_product_mapping_propagates_its_original_validation_failure(tmp_path):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="AATGCCGTTA", molecule="dna")["subject_refs"]
        tools = ToolRegistry(store)
        product = _mapped_product(store, tools, target)
        feature = _feature(store, product["id"], [{"start": 0, "end": 2}])
        workflow, root = _root(store, tools, tmp_path)
        # Deliberate owned-Store corruption, not an accepted native publication.
        corrupted = deepcopy(product)
        corrupted["mapping"]["symbol_length"] += 1
        store.db.execute("UPDATE records SET data=? WHERE id=?", (json.dumps(corrupted), product["id"]))
        before, known = _state(store), _known(workflow, root)
        with pytest.raises(ValueError, match="mapping_length_mismatch"):
            tools._prepare_orf_sequence_operand(feature["id"], scope=store.validate_scope())
        assert _state(store) == before and _known(workflow, root) == known


def test_returned_snapshot_stays_detached_from_later_owned_store_metadata_changes(tmp_path):
    with Store(tmp_path / "store") as store:
        target, = store.create_problem(raw_sequence="ATGTAA", molecule="dna")["subject_refs"]
        tools = ToolRegistry(store)
        workflow, root = _root(store, tools, tmp_path)
        snapshot = _prepare(store, tools, workflow, root, target)
        before = deepcopy(snapshot)
        changed = deepcopy(store.get(target))
        changed["name"] = "later owned metadata control"
        store.db.execute("UPDATE inputs SET data=? WHERE id=?", (json.dumps(changed), target))
        assert store.get(target)["name"] == "later owned metadata control"
        assert snapshot == before and snapshot["subject"]["name"] != changed["name"]
        second = _prepare(store, tools, workflow, root, target)
        assert second["subject"]["name"] == changed["name"]
        assert second["input_file"] == snapshot["input_file"]
