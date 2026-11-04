"""Captured native outputs plus explicitly synthetic Store bindings/faults.

These tests execute the bounded deterministic grading worker, not HMMER or an
episode. Real native search receipts belong to the existing producer fixtures.
"""
from copy import deepcopy
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.hmmer_native_result_views import NATIVE_HMMER_METRICS, family_for_program
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.materials import artifact_file
from gene_annotation_episode.native_hmmer_contracts import requested_job_from_native, native_hmmer_digest
from gene_annotation_episode.native_hmmer_result_publication import (
    prepare_native_hmmer_grading, publish_selected_native_hmmer_rows)
from gene_annotation_episode.native_hmmer_result_worker import _fasta
from gene_annotation_episode.state import Store


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "verification/tool_graders_native_hmmer_producer_2026-10-24/runs"
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def selector(program, *, offset=0, limit=100, keys=None, metrics=None):
    family = family_for_program(program)
    return {"version": "native_hmmer_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"family": family, "rows": {"record_keys": keys} if keys is not None else
            {"offset": offset, "limit": limit}, "metrics": list(metrics or NATIVE_HMMER_METRICS[family])}}


def fixture_bundle(store, name, *, bindings=(), edits=None):
    directory = RUNS / name / "attempt"
    bundle = json.loads((directory / "bundle.json").read_text())
    artifacts = []
    for kind, rows in (("input", bundle["inputs"]), ("output", bundle["artifacts"])):
        for row in rows:
            path = directory / row["relative_path"]
            contents = (edits or {}).get(row["role"])
            reference = store.artifact(contents) if contents is not None else artifact_file(store, path)
            captured = store.get(reference)
            if contents is not None:
                row.update(size_bytes=captured["size"])
                if kind == "input":
                    row.update(actual_sha256=captured["sha256"], expected_sha256=captured["sha256"],
                               expected_size_bytes=captured["size"])
                else:
                    row["sha256"] = captured["sha256"]
            artifacts.append({"role": row["role"], "format": row["format"],
                "relative_path": row["relative_path"], "artifact_ref": reference})
    bundle["operand_bindings"] = list(bindings)
    job = bundle["requested_job"]["native_hmmer"]
    job["operand_bindings"] = list(bindings)
    for operand in job["operands"]:
        record = next(r for r in bundle["inputs"] if r["role"] == operand["role"])
        operand.update(sha256=record["actual_sha256"], size_bytes=record["size_bytes"])
    bundle["requested_job"] = requested_job_from_native(job)
    bundle["identity"]["requested_job_sha256"] = native_hmmer_digest(bundle["requested_job"])
    return bundle, store.artifact(canonical(bundle), "application/json"), artifacts


def prepare(store, tmp_path, bundle, reference, artifacts, selected):
    return prepare_native_hmmer_grading(store, bundle=bundle, bundle_artifact_ref=reference,
        artifacts=artifacts, directory=tmp_path, policy=POLICY, selector=selected)


def source(store, prepared):
    return store.put("source", {"provider": "episode.execution_result", "accession": None,
        "uri": None, "artifact_ref": prepared["bundle_artifact_ref"], "text_ref": None,
        "request_ref": None, "version": "native_hmmer_result_v1", "retrieved_at": None,
        "auxiliary_artifact_refs": [prepared["source_grading_artifact_ref"]]}, origin="tool")


def publish(store, bundle, prepared, selected):
    original = source(store, prepared)
    return publish_selected_native_hmmer_rows(store, source_ref=original["id"], bundle=bundle,
        prepared=prepared, scope=store.validate_scope(), selector=selected)


def actual_input(name, role, ordinal=0):
    directory = RUNS / name / "attempt"
    bundle = json.loads((directory / "bundle.json").read_text())
    native = next(r for r in bundle["inputs"] if r["role"] == role)
    return _fasta((directory / native["relative_path"]).read_text())[ordinal]


def subject_binding(store, name, role, ordinal=0, *, wrong_sequence=False):
    native = actual_input(name, role, ordinal)
    program = name.split("_")[0]
    sequence = native["sequence"]
    if wrong_sequence:
        sequence = ("A" if sequence[0] != "A" else "C") + sequence[1:]
    store.create_problem(raw_sequence=sequence, molecule="dna" if program.startswith("nhmm") else "protein")
    target = store.validate_scope()["subject_refs"][0]
    return {"operand_role": role, "record_ordinal": ordinal, "native_name": native["name"],
            "native_accession": None, "subject_ref": target, "reference_ref": None}


def saved_grading(store, prepared):
    return (json.loads(store.get_artifact(prepared["sheet_artifact_ref"])),
            json.loads(store.get_artifact(prepared["scores_artifact_ref"])))


CAPTURED_MODES = (
    "hmmalign_align_mapali", "hmmalign_align_ordinary", "hmmalign_align_trim",
    "hmmscan_search_ordinary", "hmmsearch_search_empty", "hmmsearch_search_ordinary",
    "jackhmmer_search_ordinary", "nhmmer_alignment_ordinary", "nhmmer_profile_ordinary",
    "nhmmer_profile_watson", "nhmmer_sequence_ordinary", "nhmmscan_search_ordinary",
)


@pytest.mark.parametrize("name", CAPTURED_MODES)
def test_all_retained_native_modes_populate_full_sheets_and_recalculate_offline(tmp_path, monkeypatch, name):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="ACDEFGHIKLMNPQRSTVWY", molecule="protein")
        bundle, ref, artifacts = fixture_bundle(store, name)
        selected = selector(bundle["program"], limit=2)
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        assert prepared["sheet_artifact_ref"], prepared
        sheet, scores = saved_grading(store, prepared)
        for records in sheet["publication_inputs"]["parsed_records"].values():
            assert all(r["valid"] for r in records), records
        collection = {"protein_domain": "domains", "nucleotide_locus": "loci", "alignment_sequence": "sequences"}[family_for_program(bundle["program"])]
        assert len(scores[collection]) == len(sheet[collection])
        if "empty" in name:
            assert scores[collection] == []
        else:
            assert scores[collection]
        from gene_annotation_episode.hmmer_search_grader import calculate_hmmer_search_scores
        from gene_annotation_episode.nhmmer_grader import calculate_nhmmer_scores
        from gene_annotation_episode.hmmalign_grader import calculate_hmmalign_scores
        calculator = {"protein_domain": calculate_hmmer_search_scores,
            "nucleotide_locus": calculate_nhmmer_scores, "alignment_sequence": calculate_hmmalign_scores}[family_for_program(bundle["program"])]
        before = deepcopy(sheet)
        def prohibited(*a, **kw):
            raise AssertionError("offline recalculation attempted acquisition or native execution")
        with monkeypatch.context() as isolated:
            isolated.setattr(socket, "socket", prohibited)
            isolated.setattr(subprocess, "Popen", prohibited)
            isolated.setattr("builtins.open", prohibited)
            assert calculator(sheet, parameters={}) == scores
            assert sheet == before


@pytest.mark.parametrize("name,role", [
    ("hmmscan_search_ordinary", "query_sequence"),
    ("hmmsearch_search_ordinary", "sequence_database"),
    ("jackhmmer_search_ordinary", "query_sequence"),
    ("nhmmer_profile_ordinary", "sequence_database"),
    ("nhmmscan_search_ordinary", "query_sequence"),
    ("hmmalign_align_trim", "sequences"),
])
def test_bound_actual_input_to_store_subject_publishes_typed_numbers(tmp_path, name, role):
    with Store(tmp_path / "store") as store:
        binding = subject_binding(store, name, role)
        bundle, ref, artifacts = fixture_bundle(store, name, bindings=[binding])
        selected = selector(bundle["program"])
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        published = [r for r in result["rows"] if r["status"] == "published"]
        assert published, result
        for row in published:
            obs = store.get(row["observation_ref"])
            assert obs["subject_refs"] == [binding["subject_ref"]]
            assert obs["native_hmmer"]["record_key"] == row["record_key"]
            assert obs["native_hmmer"]["bundle_artifact_ref"] == ref
            assert row["observation_ref"] in result["record_refs"]
            for value in row["measurements"]:
                assert {"name": value["name"], "value": {"type": "number", "value": value["value"], "unit_ref": None}} in obs["measurements"]
            assert obs["operand_intervals"][0]["subject_ref"] == binding["subject_ref"]
        assert not store.current_annotations()


def test_profile_query_without_explicit_database_binding_stays_unbound(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="ACDEFGHIKLMNPQRSTVWY", molecule="protein")
        bundle, ref, artifacts = fixture_bundle(store, "hmmsearch_search_ordinary")
        selected = selector("hmmsearch", limit=1)
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert result["rows"][0]["status"] == "unbound"
        assert result["rows"][0]["subject_ref"] is None
        assert result["rows"][0]["measurements"]
        assert not store.list("observation")


def test_different_selectors_reuse_source_and_original_observation(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = subject_binding(store, "hmmscan_search_ordinary", "query_sequence")
        bundle, ref, artifacts = fixture_bundle(store, "hmmscan_search_ordinary", bindings=[binding])
        first = selector("hmmscan", limit=1, metrics=["native_domain_score_bits"])
        one = prepare(store, tmp_path / "first", bundle, ref, artifacts, first)
        result_one = publish(store, bundle, one, first)
        second = selector("hmmscan", keys=[result_one["rows"][0]["record_key"]], metrics=["paired_positions", "paired_sequence_coverage"])
        two = prepare(store, tmp_path / "second", bundle, ref, artifacts, second)
        result_two = publish(store, bundle, two, second)
        assert one["sheet_artifact_ref"] == two["sheet_artifact_ref"]
        assert one["scores_artifact_ref"] == two["scores_artifact_ref"]
        assert one["source_grading_artifact_ref"] == two["source_grading_artifact_ref"]
        assert result_one["rows"][0]["source_ref"] == result_two["rows"][0]["source_ref"]
        assert result_one["rows"][0]["observation_ref"] == result_two["rows"][0]["observation_ref"]
        assert [x["name"] for x in result_two["rows"][0]["measurements"]] == second["projection"]["metrics"]
        assert len(store.list("observation")) == 1


def test_wrong_subject_sequence_never_attaches_native_numbers(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = subject_binding(store, "hmmscan_search_ordinary", "query_sequence", wrong_sequence=True)
        bundle, ref, artifacts = fixture_bundle(store, "hmmscan_search_ordinary", bindings=[binding])
        selected = selector("hmmscan")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert all(r["status"] == "invalid" for r in result["rows"])
        assert any(r["code"] == "native_hmmer_subject_sequence_mismatch" for r in result["failures"])
        assert not store.list("observation")


def test_wrong_binding_name_and_missing_selected_key_remain_specific(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = subject_binding(store, "hmmscan_search_ordinary", "query_sequence")
        binding["native_name"] = "wrong"
        bundle, ref, artifacts = fixture_bundle(store, "hmmscan_search_ordinary", bindings=[binding])
        selected = selector("hmmscan")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert not store.list("observation")
        assert all(r["status"] == "invalid" for r in result["rows"])
        assert any(r["code"] == "native_hmmer_operand_binding_identity_mismatch" for r in result["failures"])
        missing = selector("hmmscan", keys=["exactly-this-missing-native-record"])
        bad = prepare(store, tmp_path / "missing", bundle, ref, artifacts, missing)
        assert bad["sheet_artifact_ref"] == prepared["sheet_artifact_ref"]
        assert bad["failures"][-1] == {"stage": "selection", "code": "native_hmmer_selected_record_missing", "record_key": "exactly-this-missing-native-record"}


def test_invalid_explicit_binding_preserves_valid_and_unbound_siblings(tmp_path):
    name = "hmmalign_align_ordinary"
    with Store(tmp_path / "store") as store:
        good = subject_binding(store, name, "sequences")
        bad = {**good, "record_ordinal": 1, "native_name": actual_input(name, "sequences", 1)["name"]}
        bundle, ref, artifacts = fixture_bundle(store, name, bindings=[good, bad])
        selected = selector("hmmalign")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert [r["status"] for r in result["rows"]] == ["published", "invalid", "unbound", "unbound"]
        assert len(store.list("observation")) == 1
        assert all(r["measurements"] for r in result["rows"])
        assert all(r["observation_ref"] is None for r in result["rows"][1:])
        assert any(f["code"] == "native_hmmer_subject_length_mismatch" and
            f["record_key"] == result["rows"][1]["record_key"] for f in result["failures"])


def test_host_never_hydrates_native_output_or_full_sheet_and_replay_does_not_run(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        binding = subject_binding(store, "hmmscan_search_ordinary", "query_sequence")
        bundle, ref, artifacts = fixture_bundle(store, "hmmscan_search_ordinary", bindings=[binding])
        selected = selector("hmmscan", limit=1)
        original = store.get_artifact
        forbidden = {r["artifact_ref"] for r in artifacts}
        def bounded_get(reference):
            assert reference not in forbidden, "host hydrated a complete native input/output or sheet"
            return original(reference)
        monkeypatch.setattr(store, "get_artifact", bounded_get)
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        forbidden.update([prepared["sheet_artifact_ref"], prepared["scores_artifact_ref"]])
        assert publish(store, bundle, prepared, selected)["rows"][0]["status"] == "published"
        def prohibited(*a, **kw):
            raise AssertionError("replay repeated deterministic work")
        monkeypatch.setattr("gene_annotation_episode.native_hmmer_result_publication.run_local_job", prohibited)
        assert prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected) == prepared


def test_partial_malformed_table_preserves_stdout_and_valid_siblings(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = subject_binding(store, "hmmsearch_search_ordinary", "sequence_database")
        original = (RUNS / "hmmsearch_search_ordinary/attempt/outputs/domtblout").read_text()
        bundle, ref, artifacts = fixture_bundle(store, "hmmsearch_search_ordinary", bindings=[binding],
                                               edits={"domtblout": original + "malformed later row\n"})
        selected = selector("hmmsearch")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        assert not prepared["numerical_complete"]
        result = publish(store, bundle, prepared, selected)
        assert any(row["status"] == "published" for row in result["rows"])
        assert any(row["code"] == "hmmer_truncated_table_row" for row in result["failures"])


def test_conflicting_supplied_metadata_never_overrides_actual_input(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = subject_binding(store, "hmmscan_search_ordinary", "query_sequence")
        bundle, _, artifacts = fixture_bundle(store, "hmmscan_search_ordinary", bindings=[binding])
        bundle["requested_job"]["native_hmmer"]["metadata"]["query"]["sequence"] = "X" * 20
        ref = store.artifact(canonical(bundle), "application/json")
        selected = selector("hmmscan")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        sheet, _ = saved_grading(store, prepared)
        assert sheet["inputs"]["query"]["sequence"] == actual_input("hmmscan_search_ordinary", "query_sequence")["sequence"]
        assert sheet["publication_inputs"]["supplied_metadata"]["query"]["sequence"] == "X" * 20
        assert any(f["code"] == "native_hmmer_supplied_metadata_conflict" for f in prepared["failures"])
        assert any(r["status"] == "published" for r in publish(store, bundle, prepared, selected)["rows"])


def test_exact_native_reverse_loci_and_dependent_jackhmmer_rounds_retained(tmp_path):
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="ACDEFGHIKLMNPQRSTVWY", molecule="protein")
        for name in ("nhmmer_profile_ordinary", "jackhmmer_search_ordinary"):
            bundle, ref, artifacts = fixture_bundle(store, name)
            prepared = prepare(store, tmp_path / name, bundle, ref, artifacts, selector(bundle["program"]))
            _, scores = saved_grading(store, prepared)
            if bundle["program"] == "nhmmer":
                assert {r["strand"] for r in scores["loci"]} == {"+", "-"}
                assert all(r["coordinates"]["sequence_interval"][0] < r["coordinates"]["sequence_interval"][1] for r in scores["loci"])
            else:
                assert {r["iteration"] for r in scores["domains"]} >= {1, 2}
                assert all(r["sequence_identity_fraction"] is None for r in scores["domains"] if r["iteration"] > 1)


@pytest.mark.parametrize("mode", ["mapali", "fragment_mapali", "fragment_mapali_trim"])
def test_actual_inherited_mapali_sequence_binds_with_original_coordinates(tmp_path, mode):
    from gene_annotation_episode.native_hmmer_result_worker import _stockholm
    retained = ROOT / "verification/tool_graders_hmmalign_2026-10-24"
    fragment = mode.startswith("fragment")
    native = retained / "native"
    prefix = "fragment_" if fragment else ""
    seed = (native / (prefix + "seed.sto")).read_text()
    records = _stockholm(seed, "mapali", "fixture:mapali")
    ordinal = 2 if fragment else 0
    actual = records[ordinal]
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence=actual["sequence"], molecule="protein")
        binding = {"operand_role": "mapali", "record_ordinal": ordinal,
            "native_name": actual["name"], "native_accession": None,
            "subject_ref": store.validate_scope()["subject_refs"][0], "reference_ref": None}
        # These are complete retained B003 bytes placed in a synthetic custody
        # manifest; no claim of a new producer invocation is made.
        bundle, _, artifacts = fixture_bundle(store, "hmmalign_align_mapali", bindings=[binding], edits={
            "profile": (native / (prefix + "profile.hmm")).read_text(),
            "sequences": (native / (prefix + "sequences.fa")).read_text(),
            "mapali": seed, "stockholm": (native / mode / "stdout.txt").read_text()})
        job = bundle["requested_job"]["native_hmmer"]
        job["metadata"] = json.loads((retained / "saved" / mode / "inputs.json").read_text())
        job["options"] = ["--trim"] if mode.endswith("trim") else []
        bundle["requested_job"] = requested_job_from_native(job)
        bundle["identity"]["requested_job_sha256"] = native_hmmer_digest(bundle["requested_job"])
        ref = store.artifact(canonical(bundle), "application/json")
        selected = selector("hmmalign")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        published = [r for r in result["rows"] if r["status"] == "published"]
        assert len(published) == 1, result
        obs = store.get(published[0]["observation_ref"])
        assert obs["operand_intervals"][0]["start"] == 0
        assert obs["operand_intervals"][0]["end"] == actual["length"]
        values = {r["name"]: r["value"] for r in published[0]["measurements"]}
        assert values["original_length"] == actual["length"]
        if fragment:
            assert values["missing_model_positions"] == 6
            assert values["model_occupancy"] == 0.7


def test_duplicate_database_names_are_unbound_and_valid_sibling_is_preserved(tmp_path):
    name = "hmmsearch_search_ordinary"
    database = (RUNS / name / "attempt/inputs/sequence_database.fa").read_text()
    originals = _fasta(database)
    first, sibling = originals[0], originals[1]
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence=sibling["sequence"], molecule="protein")
        subject = store.validate_scope()["subject_refs"][0]
        bindings = [{"operand_role": "sequence_database", "record_ordinal": ordinal,
            "native_name": original["name"], "native_accession": None,
            "subject_ref": subject, "reference_ref": None} for ordinal, original in enumerate(originals[:2])]
        duplicate = database + ">" + first["name"] + "\n" + first["sequence"] + "\n"
        bundle, ref, artifacts = fixture_bundle(store, name, bindings=bindings, edits={"sequence_database": duplicate})
        selected = selector("hmmsearch")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        _, scores = saved_grading(store, prepared)
        names = {r["record_key"]: r["target_name"] for r in scores["domains"]}
        assert all(r["status"] == "unbound" for r in result["rows"] if names[r["record_key"]] == first["name"])
        assert any(r["status"] == "published" for r in result["rows"] if names[r["record_key"]] == sibling["name"]), result


def test_wrong_ordinal_and_malformed_nucleotide_row_preserve_bound_reverse_locus(tmp_path):
    name = "nhmmer_profile_ordinary"
    with Store(tmp_path / "store") as store:
        good = subject_binding(store, name, "sequence_database", ordinal=1)
        wrong = {**good, "record_ordinal": 999}
        table = (RUNS / name / "attempt/outputs/tblout").read_text()
        bundle, ref, artifacts = fixture_bundle(store, name, bindings=[good, wrong],
                                               edits={"tblout": table + "malformed row\n"})
        selected = selector("nhmmer", offset=1, limit=1)
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert len(result["rows"]) == 1
        assert result["rows"][0]["strand"] == "minus"
        assert result["rows"][0]["status"] == "published", result
        assert any(r["code"] == "native_hmmer_operand_binding_record_missing" for r in result["failures"])
        assert not prepared["numerical_complete"]


def test_multiple_actual_query_ordinals_rebuild_corresponding_numerical_inputs(tmp_path):
    name = "hmmscan_search_ordinary"
    directory = RUNS / name / "attempt"
    original = actual_input(name, "query_sequence")
    edits = {role: (directory / "outputs" / role).read_text() for role in ("stdout", "tblout", "domtblout")}
    for role, text in list(edits.items()):
        edits[role] = text + text.replace("test1", "second_query")
    edits["query_sequence"] = ">test1\n" + original["sequence"] + "\n>second_query\n" + original["sequence"] + "\n"
    with Store(tmp_path / "store") as store:
        first = subject_binding(store, name, "query_sequence")
        second = {**first, "record_ordinal": 1, "native_name": "second_query"}
        bundle, ref, artifacts = fixture_bundle(store, name, bindings=[first, second], edits=edits)
        selected = selector("hmmscan")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert {r["query_occurrence"] for r in result["rows"]} == {0, 1}, result
        assert all(r["status"] == "published" for r in result["rows"]), result
        for row in result["rows"]:
            values = {r["name"]: r["value"] for r in row["measurements"]}
            assert values["paired_sequence_coverage"] == 1


def test_worker_resource_failure_retains_custody_and_structured_failure_without_retry(tmp_path, monkeypatch):
    from gene_annotation_episode.acquisition import AcquisitionError
    calls = []
    def resource_failed(*args, **kwargs):
        calls.append(kwargs["policy"])
        raise AcquisitionError("synthetic_worker_resource_failure")
    monkeypatch.setattr("gene_annotation_episode.native_hmmer_result_publication.run_local_job", resource_failed)
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence="ACDEFGHIKLMNPQRSTVWY", molecule="protein")
        bundle, ref, artifacts = fixture_bundle(store, "hmmscan_search_ordinary")
        selected = selector("hmmscan")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        assert prepared["sheet_artifact_ref"] is None
        assert prepared["source_grading_artifact_ref"] and prepared["grading_artifact_ref"]
        assert prepared["failures"][-1]["code"] == "synthetic_worker_resource_failure"
        assert publish(store, bundle, prepared, selected)["rows"] == []
        assert prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected) == prepared
        assert calls == [POLICY]


def test_synthetic_native_negative_score_and_zero_evalue_publish_as_numbers(tmp_path):
    name = "hmmscan_search_ordinary"
    directory = RUNS / name / "attempt/outputs"
    edits = {role: (directory / role).read_text().replace("72.1", "-2.5").replace("1.1e-24", "0")
             for role in ("stdout", "tblout", "domtblout")}
    with Store(tmp_path / "store") as store:
        binding = subject_binding(store, name, "query_sequence")
        bundle, ref, artifacts = fixture_bundle(store, name, bindings=[binding], edits=edits)
        selected = selector("hmmscan")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert result["rows"][0]["status"] == "published", result
        values = {r["name"]: r["value"] for r in result["rows"][0]["measurements"]}
        assert values["native_domain_score_bits"] == -2.5
        assert values["native_conditional_evalue"] == 0
        assert "sequence_identity_fraction" in {r["name"] for r in result["rows"][0]["unavailable"]}


@pytest.mark.parametrize("missing_role", ["stdout", "domtblout"])
def test_missing_one_native_representation_retains_useful_sibling_outputs(tmp_path, missing_role):
    with Store(tmp_path / "store") as store:
        binding = subject_binding(store, "hmmscan_search_ordinary", "query_sequence")
        bundle, ref, artifacts = fixture_bundle(store, "hmmscan_search_ordinary", bindings=[binding])
        artifacts = [r for r in artifacts if r["role"] != missing_role]
        selected = selector("hmmscan")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert not prepared["numerical_complete"]
        assert prepared["sheet_artifact_ref"] and prepared["scores_artifact_ref"]
        assert any(r["code"] == "native_hmmer_captured_artifact_missing:" + missing_role for r in result["failures"])
        assert any(r["status"] == "published" for r in result["rows"]), result
