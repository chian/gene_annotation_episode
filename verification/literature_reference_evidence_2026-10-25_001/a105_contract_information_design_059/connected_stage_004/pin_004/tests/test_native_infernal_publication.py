"""Retained native bytes through the bounded worker and actual Store publication.

Store bindings, mutations and composed envelopes are explicit engineering test
inputs. None of these tests invokes Infernal or an episode/model/controller.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

import pytest

from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.infernal_native_result_views import NATIVE_INFERNAL_METRICS
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.materials import artifact_file, artifact_path
from gene_annotation_episode.native_infernal_contracts import requested_job_from_infernal, native_infernal_digest
from gene_annotation_episode.native_infernal_result_publication import (
    prepare_native_infernal_grading, publish_selected_native_infernal_rows)
from gene_annotation_episode.native_infernal_result_worker import _fasta
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import retain_tool_grading


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/native_infernal_publication"
POLICY = LocalJobPolicy(20 * 1024**3, 4 * 1024**3, None)


def test_all_native_quantities_have_store_measurement_names():
    from gene_annotation_episode.domain import METRIC_NAMES
    assert set().union(*NATIVE_INFERNAL_METRICS.values()) <= set(METRIC_NAMES)


def selector(family="search_hit", *, keys=None, offset=0, limit=1, metrics=None):
    return {"version": "native_infernal_result_selector_v1", "acquisition": "complete_bound_bundle",
        "projection": {"family": family, "rows": {"record_keys": keys} if keys is not None else
            {"offset": offset, "limit": limit}, "metrics": list(metrics or NATIVE_INFERNAL_METRICS[family])}}


def seal(store, bundle):
    bundle["requested_job"] = requested_job_from_infernal(bundle["requested_job"]["native_infernal"])
    bundle["identity"]["requested_job_sha256"] = native_infernal_digest(bundle["requested_job"])
    return store.artifact(canonical(bundle), "application/json")


def fixture_bundle(store, case="cmsearch", *, bindings=(), edits=None, options=None):
    directory = FIXTURES / case
    bundle = json.loads((directory / "bundle.json").read_bytes())
    artifacts = []
    job = bundle["requested_job"]["native_infernal"]
    for kind, rows in (("input", bundle["inputs"]), ("output", bundle["artifacts"])):
        for row in rows:
            replacement = (edits or {}).get(row["role"])
            ref = store.artifact(replacement) if replacement is not None else artifact_file(store, directory / row["relative_path"])
            actual = store.get(ref)
            if replacement is not None:
                row["size_bytes"] = actual["size"]
                if kind == "input":
                    row.update(actual_sha256=actual["sha256"], expected_sha256=actual["sha256"],
                        expected_size_bytes=actual["size"])
                    operand = next(r for r in job["operands"] if r["role"] == row["role"])
                    operand.update(sha256=actual["sha256"], size_bytes=actual["size"])
                else:
                    row["sha256"] = actual["sha256"]
            artifacts.append({k: row[k] for k in ("role", "format", "relative_path")})
            artifacts[-1]["artifact_ref"] = ref
    job["operand_bindings"] = bundle["operand_bindings"] = list(bindings)
    if options is not None:
        job["options"] = options
    return bundle, seal(store, bundle), artifacts


def bound_subject(store, case="cmsearch", *, ordinal=0, sequence=None, molecule="rna"):
    actual = _fasta((FIXTURES / case / "inputs/sequences.fa").read_text())[ordinal]
    store.create_problem(raw_sequence=sequence or actual["sequence"], molecule=molecule)
    return {"operand_role": "sequences", "record_ordinal": ordinal,
        "native_name": actual["name"], "native_accession": None,
        "subject_ref": store.validate_scope()["subject_refs"][0], "reference_ref": None}


def prepare(store, directory, bundle, reference, artifacts, selected):
    return prepare_native_infernal_grading(store, bundle=bundle, bundle_artifact_ref=reference,
        artifacts=artifacts, directory=directory, policy=POLICY, selector=selected)


def source(store, prepared):
    return store.put("source", {"provider": "episode.execution_result", "accession": None,
        "uri": None, "artifact_ref": prepared["bundle_artifact_ref"], "text_ref": None,
        "request_ref": None, "version": "native_infernal_bundle_v1", "retrieved_at": None,
        "auxiliary_artifact_refs": [prepared["source_grading_artifact_ref"]]}, origin="tool")["id"]


def publish(store, bundle, prepared, selected, *, scope=None, source_ref=None):
    return publish_selected_native_infernal_rows(store, source_ref=source_ref or source(store, prepared),
        bundle=bundle, prepared=prepared, scope=scope or store.validate_scope(), selector=selected)


def rows(store, prepared):
    return [json.loads(line) for line in artifact_path(store, prepared["selected_rows_artifact_ref"]).read_text().splitlines()]


def values(row):
    return {v["name"]: v["value"] for v in row["measurements"]}


def replaced_rows(store, prepared, selected_rows):
    """A deliberately synthetic retained worker envelope for validation tests."""
    prepared = deepcopy(prepared)
    ref = store.artifact("".join(json.dumps(row) + "\n" for row in selected_rows), "application/x-ndjson")
    prepared["selected_rows_artifact_ref"] = ref
    grading = json.loads(store.get_artifact(prepared["grading_artifact_ref"]))["grading"]
    grading["selected_rows_artifact_ref"] = ref
    prepared["grading_artifact_ref"] = retain_tool_grading(store, provider="episode.execution_result",
        native_artifact_ref=prepared["bundle_artifact_ref"], grading=grading)
    return prepared


@pytest.mark.parametrize("case,family", [("cmsearch", "search_hit"), ("cmscan", "search_hit"),
    ("cmsearch", "search_sequence"), ("cmalign", "alignment_sequence"),
    ("cmalign", "alignment_column"), ("cmalign", "alignment_pair")])
def test_native_five_families_and_bounded_receipt(tmp_path, case, family):
    with Store(tmp_path / "store") as store:
        binding = bound_subject(store, case)
        bundle, ref, artifacts = fixture_bundle(store, case, bindings=[binding])
        selected = selector(family)
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        assert prepared["numerical_complete"], prepared
        result = publish(store, bundle, prepared, selected)
        assert len(result["rows"]) == 1
        row = result["rows"][0]
        native = rows(store, prepared)[0]
        assert row["record_key"] == native["record_key"]  # No invented accession conversion.
        assert row["measurements"] == native["measurements"]
        if family in {"alignment_column", "alignment_pair"}:
            assert row["status"] == "unbound" and row["subject_ref"] is None
            assert not store.list("observation")
            assert row["reference_refs"]
            assert all(store.get(r)["reference_type"] == "family" for r in row["reference_refs"])
            assert values(row)["row_count"] == 10
            if family == "alignment_column":
                assert values(row)["occupancy"] == 1
            else:
                assert values(row)["canonical_pair_fraction"] == 1
        else:
            assert row["status"] == "published", result
            observation = store.get(row["observation_ref"])
            assert observation["subject_refs"] == [binding["subject_ref"]]
            assert observation["native_infernal"] == {"version": "native_infernal_observation_v1",
                "program": case, "family": family, "record_key": row["record_key"], "bundle_artifact_ref": ref}
            assert observation["source_subject_refs"] == row["reference_refs"]
            assert observation["anchor"] is None
            assert observation["operand_intervals"] == [{"role": "query", "subject_ref": binding["subject_ref"],
                "start": 0, "end": 72, "unit": "nt", "model_unit": "nt"}]
            assert all(store.get(r)["reference_type"] == "family" for r in row["reference_refs"])
            assert all(not any(t in v["name"] for t in ("time", "seconds", "confidence")) for v in observation["measurements"])
            if family == "search_hit":
                assert values(row)["bitscore"] == 71.4
                assert values(row)["bias_bits"] == 0.0
                if case == "cmsearch":
                    payload = {k: v for k, v in observation.items() if k not in {"id", "record_type", "origin"}}
                    for field, value, code in (("program", "cmscan", "bundle_program_mismatch"),
                            ("family", "alignment_sequence", "program_family_mismatch")):
                        wrong = deepcopy(payload)
                        wrong["native_infernal"][field] = value
                        with pytest.raises(ContractError, match="native_infernal_" + code):
                            store.put("observation", wrong, origin="tool")
                    wrong = deepcopy(payload)
                    wrong["kind"] = "alignment"
                    with pytest.raises(ContractError, match="native_infernal_observation_kind_mismatch"):
                        store.put("observation", wrong, origin="tool")
                    with pytest.raises(ContractError, match="native_infernal_requires_native_tool_source"):
                        store.put("observation", payload, origin="external")
            elif family == "search_sequence":
                assert values(row)["union_numerator"] == 72
                assert values(row)["union_span_fraction"] == 1
            else:
                assert values(row)["native_bit_score"] == 60.03
                assert values(row)["native_avg_pp"] == 1
                assert {v["name"]: v["reason"] for v in row["unavailable"]}["deleted_model_positions"] == "not_measured"
        envelope = json.loads(store.get_artifact(prepared["grading_artifact_ref"]))["grading"]
        assert envelope["worker_receipt"]["policy"] == POLICY.to_dict()
        assert envelope["worker_receipt"]["enforcement"]["wall_time"] == "unset"
        assert not store.current_annotations()


def test_projections_preserve_full_sheet_source_and_observation_identity(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = bound_subject(store)
        bundle, ref, artifacts = fixture_bundle(store, bindings=[binding])
        first = selector(metrics=["bitscore"])
        one = prepare(store, tmp_path / "first", bundle, ref, artifacts, first)
        initial = publish(store, bundle, one, first)
        second = selector(keys=[initial["rows"][0]["record_key"]], metrics=["evalue", "sequence_span_fraction"])
        two = prepare(store, tmp_path / "second", bundle, ref, artifacts, second)
        repeated = publish(store, bundle, two, second)
        for field in ("sheet_artifact_ref", "scores_artifact_ref", "source_grading_artifact_ref"):
            assert one[field] == two[field]
        for field in ("source_ref", "observation_ref", "reference_refs"):
            assert initial["rows"][0][field] == repeated["rows"][0][field]
        assert len(store.list("observation")) == 1
        assert len(store.get(initial["rows"][0]["observation_ref"])["measurements"]) == len(NATIVE_INFERNAL_METRICS["search_hit"])
        third = selector("search_sequence", metrics=["hit_count"])
        three = prepare(store, tmp_path / "third", bundle, ref, artifacts, third)
        assert three["source_grading_artifact_ref"] == one["source_grading_artifact_ref"]
        assert publish(store, bundle, three, third)["rows"][0]["source_ref"] == initial["rows"][0]["source_ref"]


def test_host_no_full_dataset_or_sheet_hydration_and_completed_replay(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        binding = bound_subject(store)
        bundle, ref, artifacts = fixture_bundle(store, bindings=[binding])
        selected = selector()
        original = store.get_artifact
        forbidden = {r["artifact_ref"] for r in artifacts}
        forbidden.add(store.get(binding["subject_ref"])["sequence_ref"])
        def bounded(reference):
            assert reference not in forbidden, "host hydrated full native data, sequence, sheet or scores"
            return original(reference)
        monkeypatch.setattr(store, "get_artifact", bounded)
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        forbidden.update(prepared[k] for k in ("sheet_artifact_ref", "scores_artifact_ref"))
        assert publish(store, bundle, prepared, selected)["rows"][0]["status"] == "published"
        def prohibited(*args, **kwargs):
            raise AssertionError("replay attempted worker execution or scientific calculation")
        monkeypatch.setattr("gene_annotation_episode.native_infernal_result_publication.run_local_job", prohibited)
        monkeypatch.setattr("gene_annotation_episode.native_infernal_result_worker.run", prohibited)
        assert prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected) == prepared
        with pytest.raises(ContractError, match="directory_identity_conflict"):
            prepare(store, tmp_path / "grading", bundle, ref, artifacts, selector(metrics=["bitscore"]))
        receipt = tmp_path / "grading/native-infernal-grading/prepared.json"
        receipt.write_text(json.dumps(prepared, indent=2))
        with pytest.raises(ValueError, match="practical_record_bytes_changed"):
            prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)


@pytest.mark.parametrize("fault,code", [("sequence", "subject_sequence_mismatch"),
    ("unit", "subject_unit_mismatch"), ("name", "operand_binding_identity_mismatch")])
def test_supplied_wrong_subject_is_invalid_not_missing(tmp_path, fault, code):
    with Store(tmp_path / "store") as store:
        actual = _fasta((FIXTURES / "cmsearch/inputs/sequences.fa").read_text())[0]["sequence"]
        sequence = ("C" if actual[0] != "C" else "A") + actual[1:] if fault == "sequence" else actual
        binding = bound_subject(store, sequence=sequence, molecule="unspecified" if fault == "unit" else "rna")
        if fault == "name":
            binding["native_name"] = "wrong"
        bundle, ref, artifacts = fixture_bundle(store, bindings=[binding])
        selected = selector()
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert result["rows"][0]["status"] == "invalid", result
        assert any(f["code"] == "native_infernal_" + code for f in result["failures"])
        assert not store.list("observation")


def test_original_t_and_u_are_not_the_same_store_subject(tmp_path):
    with Store(tmp_path / "store") as store:
        actual = _fasta((FIXTURES / "cmsearch/inputs/sequences.fa").read_text())[0]["sequence"]
        binding = bound_subject(store, sequence=actual.replace("U", "T"), molecule="dna")
        bundle, ref, artifacts = fixture_bundle(store, bindings=[binding])
        selected = selector()
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert result["rows"][0]["status"] == "invalid"
        assert any(f["code"] == "native_infernal_subject_sequence_mismatch" for f in result["failures"])


def test_absent_binding_and_wrong_binding_preserve_valid_sibling(tmp_path):
    with Store(tmp_path / "store") as store:
        good = bound_subject(store, "cmalign")
        original = _fasta((FIXTURES / "cmalign/inputs/sequences.fa").read_text())
        bad = {**good, "record_ordinal": 1, "native_name": original[1]["name"]}
        bundle, ref, artifacts = fixture_bundle(store, "cmalign", bindings=[good, bad])
        selected = selector("alignment_sequence", limit=3)
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert [r["status"] for r in result["rows"]] == ["published", "invalid", "unbound"]
        assert len(store.list("observation")) == 1
        assert all(r["measurements"] for r in result["rows"])


def test_duplicate_names_never_guess_a_subject(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = bound_subject(store, ordinal=1)
        fasta = (FIXTURES / "cmsearch/inputs/sequences.fa").read_text()
        first = _fasta(fasta)[0]
        duplicate = fasta + ">" + first["name"] + "\n" + first["sequence"] + "\n"
        bundle, ref, artifacts = fixture_bundle(store, bindings=[binding], edits={"sequences": duplicate})
        selected = selector(limit=2)
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert [r["status"] for r in result["rows"]] == ["unbound", "published"], result


def test_selected_zero_and_missing_remain_different_completed_quantities(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = bound_subject(store, "cmalign")
        bundle, ref, artifacts = fixture_bundle(store, "cmalign", bindings=[binding])
        selected = selector("alignment_sequence", metrics=["retained_insert_nucleotides", "deleted_model_positions"])
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        assert prepared["numerical_complete"], prepared
        row = publish(store, bundle, prepared, selected)["rows"][0]
        assert row["measurements"] == [{"name": "retained_insert_nucleotides", "value": 0}]
        assert row["unavailable"] == [{"name": "deleted_model_positions", "reason": "not_measured"}]


def test_missing_record_and_partial_output_are_specific_and_keep_valid_work(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = bound_subject(store)
        table = (FIXTURES / "cmsearch/hits.tblout").read_text()
        bundle, ref, artifacts = fixture_bundle(store, bindings=[binding], edits={"tblout": table + "bad native row\n"})
        selected = selector()
        prepared = prepare(store, tmp_path / "partial", bundle, ref, artifacts, selected)
        assert not prepared["numerical_complete"] and prepared["sheet_artifact_ref"]
        assert publish(store, bundle, prepared, selected)["rows"][0]["status"] == "published"
        missing = selector(keys=["the absent raw native key | with whitespace"])
        unavailable = prepare(store, tmp_path / "missing", bundle, ref, artifacts, missing)
        assert any(f["stage"] == "selection" and f["record_key"] == missing["projection"]["rows"]["record_keys"][0]
            for f in unavailable["failures"])
        assert publish(store, bundle, unavailable, missing)["rows"] == []


def test_custody_failure_retains_bytes_excludes_unusable_path_and_does_not_retry(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        bound_subject(store)
        bundle, ref, artifacts = fixture_bundle(store)
        input_row = next(r for r in bundle["inputs"] if r["role"] == "sequences")
        input_row["expected_sha256"] = "0" * 64
        ref = seal(store, bundle)
        selected = selector()
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        assert not prepared["numerical_complete"]
        assert any(f["code"] == "native_infernal_input_not_original_selected_bytes:sequences" for f in prepared["failures"])
        plan = json.loads((tmp_path / "grading/native-infernal-grading/plan.json").read_text())
        assert not any(r["role"] == "sequences" for r in plan["artifacts"])
        stable = json.loads(store.get_artifact(prepared["source_grading_artifact_ref"]))["grading"]
        captured = next(r for r in artifacts if r["role"] == "sequences")
        assert {**captured, "kind": "input"} in stable["captured_artifacts"]
        assert artifact_path(store, captured["artifact_ref"]).is_file()
        monkeypatch.setattr("gene_annotation_episode.native_infernal_result_publication.run_local_job",
            lambda *a, **kw: pytest.fail("completed failure retried"))
        assert prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected) == prepared


def test_failed_worker_receipt_and_interrupted_intent_never_retry(tmp_path, monkeypatch):
    calls = []
    def failed(*args, **kwargs):
        calls.append(kwargs["policy"])
        raise AcquisitionError("synthetic_resource_failure")
    monkeypatch.setattr("gene_annotation_episode.native_infernal_result_publication.run_local_job", failed)
    with Store(tmp_path / "store") as store:
        bound_subject(store)
        bundle, ref, artifacts = fixture_bundle(store)
        selected = selector()
        prepared = prepare(store, tmp_path / "failed", bundle, ref, artifacts, selected)
        assert prepared["sheet_artifact_ref"] is None
        assert any(f["code"] == "synthetic_resource_failure" for f in prepared["failures"])
        assert prepare(store, tmp_path / "failed", bundle, ref, artifacts, selected) == prepared
        assert calls == [POLICY]
        (tmp_path / "failed/native-infernal-grading/prepared.json").unlink()
        with pytest.raises(ContractError, match="original_preparation_incomplete"):
            prepare(store, tmp_path / "failed", bundle, ref, artifacts, selected)
        assert calls == [POLICY]


def test_replay_detects_corrupted_retained_input_without_launch(tmp_path, monkeypatch):
    with Store(tmp_path / "store") as store:
        bound_subject(store)
        bundle, ref, artifacts = fixture_bundle(store)
        selected = selector()
        prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        captured = next(r for r in artifacts if r["role"] == "sequences")
        path = artifact_path(store, captured["artifact_ref"])
        path.write_bytes(b"corrupted retained original input\n")
        monkeypatch.setattr("gene_annotation_episode.native_infernal_result_publication.run_local_job",
            lambda *a, **kw: pytest.fail("replay launched worker after corruption"))
        with pytest.raises(ContractError, match="prepared_grading_identity_mismatch"):
            prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)


def test_publisher_rejects_custody_selector_and_measurement_tampering(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = bound_subject(store)
        bundle, ref, artifacts = fixture_bundle(store, bindings=[binding])
        selected = selector()
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        original = rows(store, prepared)
        original_source = store.get(source(store, prepared))
        wrong_source = {k: v for k, v in original_source.items() if k not in {"id", "record_type", "origin"}}
        wrong_source["version"] = "unrelated_bundle_v1"
        wrong_ref = store.put("source", wrong_source, origin="tool")["id"]
        with pytest.raises(ContractError, match="publication_source_custody_mismatch"):
            publish(store, bundle, prepared, selected, source_ref=wrong_ref)
        with pytest.raises(ContractError, match="prepared_grading_identity_mismatch"):
            publish(store, bundle, prepared, selector(metrics=["bitscore"]))
        bad_bundle = deepcopy(bundle)
        bad_bundle["returncode"] = 17
        with pytest.raises(ContractError, match="bundle_artifact_identity_mismatch"):
            publish(store, bad_bundle, prepared, selected)
        bad = deepcopy(prepared)
        bad["numerical_complete"] = False
        with pytest.raises(ContractError, match="prepared_grading_identity_mismatch"):
            publish(store, bundle, bad, selected)
        duplicate = replaced_rows(store, prepared, original + original)
        with pytest.raises(ContractError, match="duplicate_or_reordered"):
            publish(store, bundle, duplicate, selected)
        wrong = deepcopy(original)
        wrong[0]["measurements"][0]["value"] += 1
        with pytest.raises(ContractError, match="selected_observation_values_mismatch"):
            publish(store, bundle, replaced_rows(store, prepared, wrong), selected)
        outside = deepcopy(original)
        outside[0]["native_ordinal"] = 90
        with pytest.raises(ContractError, match="outside_selector"):
            publish(store, bundle, replaced_rows(store, prepared, outside), selected)


def test_every_interval_is_checked_and_physical_gaps_are_not_enclosed(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = bound_subject(store)
        bundle, ref, artifacts = fixture_bundle(store, bindings=[binding])
        selected = selector()
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        synthetic = rows(store, prepared)
        synthetic[0]["subject_intervals"] = [[0, 10], [20, 30]]
        projected = replaced_rows(store, prepared, synthetic)
        scope = store.validate_scope({"subject_refs": [binding["subject_ref"]], "segments": [
            {"target_ref": binding["subject_ref"], "start": a, "end": b, "unit": "nt"}
            for a, b in ((0, 10), (20, 30))]})
        result = publish(store, bundle, projected, selected, scope=scope)
        assert result["rows"][0]["status"] == "published", result
        observation = store.get(result["rows"][0]["observation_ref"])
        assert [(r["start"], r["end"]) for r in observation["operand_intervals"]] == [(0, 10), (20, 30)]
        for bad_interval in ([20, 73], [10, 30], [True, 3], [4, 4], [-1, 2], [0, 10]):
            bad = deepcopy(synthetic)
            bad[0]["subject_intervals"][1] = bad_interval
            failure = publish(store, bundle, replaced_rows(store, prepared, bad), selected, scope=scope)
            assert failure["rows"][0]["status"] == "invalid", bad_interval
        missing = deepcopy(synthetic)
        missing[0]["subject_intervals"] = []
        assert publish(store, bundle, replaced_rows(store, prepared, missing), selected)["rows"][0]["status"] == "unbound"


def test_explicit_model_reference_must_match_native_identity_and_family(tmp_path):
    with Store(tmp_path / "store") as store:
        binding = bound_subject(store)
        origin = store._caller_source({"fixture": "explicit model reference"}, "caller")
        def model(name, kind):
            return store.put("reference", {"reference_type": kind, "source_ref": origin["id"],
                "accession": name, "label": name, "sequence_ref": None, "molecule": None,
                "length": None, "term_refs": [], "context_refs": []}, origin="caller")["id"]
        for index, (name, kind, status) in enumerate((("tRNA5", "family", "published"),
                ("wrong", "family", "invalid"), ("tRNA5", "sequence", "invalid"))):
            model_binding = {"operand_role": "models", "record_ordinal": 0, "native_name": "tRNA5",
                "native_accession": None, "subject_ref": None, "reference_ref": model(name, kind)}
            bundle, ref, artifacts = fixture_bundle(store, bindings=[binding, model_binding])
            selected = selector()
            prepared = prepare(store, tmp_path / str(index), bundle, ref, artifacts, selected)
            result = publish(store, bundle, prepared, selected)
            assert result["rows"][0]["status"] == status, result
            if status == "published":
                assert result["rows"][0]["reference_refs"] == [model_binding["reference_ref"]]


def test_unbound_population_still_validates_supplied_model_reference(tmp_path):
    with Store(tmp_path / "store") as store:
        bound_subject(store, "cmalign")
        origin = store._caller_source({"fixture": "model reference for a population"}, "caller")
        for index, name in enumerate(("tRNA5", "wrong")):
            reference = store.put("reference", {"reference_type": "family", "source_ref": origin["id"],
                "accession": name, "label": name, "sequence_ref": None, "molecule": None,
                "length": None, "term_refs": [], "context_refs": []}, origin="caller")["id"]
            binding = {"operand_role": "models", "record_ordinal": 0, "native_name": "tRNA5",
                "native_accession": None, "subject_ref": None, "reference_ref": reference}
            bundle, ref, artifacts = fixture_bundle(store, "cmalign", bindings=[binding])
            selected = selector("alignment_column")
            prepared = prepare(store, tmp_path / str(index), bundle, ref, artifacts, selected)
            result = publish(store, bundle, prepared, selected)
            row = result["rows"][0]
            assert row["status"] == ("unbound" if name == "tRNA5" else "invalid")
            assert row["subject_ref"] is None and row["observation_ref"] is None
            assert row["measurements"]
            if name == "tRNA5":
                assert row["reference_refs"] == [reference]
            else:
                assert any(f["code"] == "native_infernal_reference_binding_identity_mismatch" for f in result["failures"])
        assert not store.list("observation")


def test_real_matchonly_omitted_positions_keep_disjoint_original_intervals(tmp_path):
    directory = FIXTURES / "local_end_matchonly"
    metadata = json.loads((directory / "metadata.json").read_text())
    actual = metadata["sequences"][0]
    with Store(tmp_path / "store") as store:
        store.create_problem(raw_sequence=actual["sequence"], molecule="dna")
        subject = store.validate_scope()["subject_refs"][0]
        binding = {"operand_role": "sequences", "record_ordinal": 0, "native_name": actual["name"],
            "native_accession": None, "subject_ref": subject, "reference_ref": None}
        edits = {role: (directory / filename).read_bytes() for role, filename in (
            ("models", "models.cm"), ("stockholm", "alignment.sto"), ("scores", "scores.txt"),
            ("inserts", "inserts.txt"), ("local_ends", "local_ends.txt"))}
        edits["sequences"] = ">" + actual["name"] + "\n" + actual["sequence"] + "\n"
        bundle, ref, artifacts = fixture_bundle(store, "cmalign", bindings=[binding], edits=edits,
            options=["--cpu", "1", "--matchonly", "--miss"])
        selected = selector("alignment_sequence")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        result = publish(store, bundle, prepared, selected)
        assert result["rows"][0]["status"] == "published", result
        observation = store.get(result["rows"][0]["observation_ref"])
        intervals = [(r["start"], r["end"]) for r in observation["operand_intervals"]]
        assert intervals == [(0, 21), (22, 61), (65, 103)]
        assert values(result["rows"][0])["omitted_nucleotides"] == 5


def test_native_failure_preserves_diagnostics_and_no_fake_success(tmp_path):
    with Store(tmp_path / "store") as store:
        bound_subject(store)
        bundle, ref, artifacts = fixture_bundle(store, "cmalign_native_failure")
        selected = selector("alignment_sequence")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selected)
        assert not prepared["numerical_complete"]
        assert any(f["code"] == "native_infernal_native_execution_unsuccessful" for f in prepared["failures"])
        assert publish(store, bundle, prepared, selected)["rows"] == []
        assert not store.list("observation")


def test_saved_full_sheet_recalculates_without_files_network_or_execution(tmp_path, monkeypatch):
    from gene_annotation_episode.cmalign_grader import calculate_cmalign_scores
    with Store(tmp_path / "store") as store:
        bound_subject(store, "cmalign")
        bundle, ref, artifacts = fixture_bundle(store, "cmalign")
        prepared = prepare(store, tmp_path / "grading", bundle, ref, artifacts, selector("alignment_sequence"))
        sheet = json.loads(store.get_artifact(prepared["sheet_artifact_ref"]))
        scores = json.loads(store.get_artifact(prepared["scores_artifact_ref"]))
        before = deepcopy(sheet)
        def prohibited(*args, **kwargs):
            raise AssertionError("saved-sheet recalculation performed an external operation")
        with monkeypatch.context() as isolated:
            isolated.setattr(socket, "socket", prohibited)
            isolated.setattr(subprocess, "Popen", prohibited)
            isolated.setattr("builtins.open", prohibited)
            assert calculate_cmalign_scores(sheet, parameters=bundle["requested_job"]["native_infernal"]["grading_parameters"]) == scores
            assert sheet == before
