"""B001 real local publication, custody, and offline recalculation checks.

The sequences are synthetic test operands. Native Biopython/Pyrodigal execution
is real; the BLAST protocol fixture is offline and never contacts a service.
"""
from copy import deepcopy
import json
from pathlib import Path
import socket

import pytest

from gene_annotation_episode.biopython_pairwise_grader import calculate_biopython_pairwise_scores
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.prodigal_grader import calculate_prodigal_scores
from gene_annotation_episode.sequence_composition_grader import calculate_sequence_composition_scores
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import (
    MEDIA_TYPE, retain_tool_grading, source_tool_gradings,
)
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
META_INPUT = ROOT / "verification/tool_graders_batch_001/prodigal/meta.input.fna"


def numerical(observation):
    return {row["name"]: row["value"]["value"] for row in observation["measurements"]
            if row["value"]["type"] == "number"}


def only_grading(store, source_ref):
    grading, = source_tool_gradings(store, source_ref)
    return grading


def operation_count(store, name):
    return store.db.execute("SELECT count(*) FROM tool_operations WHERE name=?", (name,)).fetchone()[0]


def gene_input():
    return "".join(line for line in META_INPUT.read_text().splitlines() if not line.startswith(">"))


def quality_library(store, tmp_path, *, long_read=False):
    sequence = "ACGT" * (4000 if long_read else 2)
    content = (f"@same high\n{sequence}\n+\n{'I' * (len(sequence)-1)}!\n"
               f"@same low\n{sequence}\n+\n{'!' * len(sequence)}\n").encode()
    path = tmp_path / "reads.fastq"
    path.write_bytes(content)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": 2, "entries": [{"path": path.name,
        "molecule": "dna", "quality_encoding": "phred33"}]}))
    target, = store.create_problem(manifest_path=manifest)["subject_refs"]
    selected = ToolRegistry(store).execute("library.members", {"library_ref": target}, operation_key="members")
    assert selected["status"] == "completed", selected
    return target, selected["result"]["members"], content


@pytest.mark.parametrize("molecule,sequence", [("dna", "ACGTTGCA"), ("rna", "ACGUUGCA"),
                                               ("protein", "MACDEFGH")])
@pytest.mark.parametrize("mode", ["local", "global"])
def test_real_pairwise_worker_retains_complete_sheet_on_existing_observation(tmp_path, molecule, sequence, mode):
    directory = tmp_path / "state"
    with Store(directory) as store:
        target, = store.create_problem(raw_sequence=sequence, molecule=molecule)["subject_refs"]
        registry = ToolRegistry(store)
        args = {"query_ref": target, "reference_ref": target, "molecule": molecule, "mode": mode}
        result = registry.execute("sequence.align", args, operation_key="align")
        assert result["status"] == "completed", result
        source = store.get(result["result"]["source_ref"])
        native_bytes = store.get_artifact(source["artifact_ref"])
        native = json.loads(native_bytes)
        grading = only_grading(store, source["id"])
        assert grading["sheet"]["native_result"] == native
        assert grading["sheet"]["molecule"] == molecule and grading["sheet"]["mode"] == mode
        assert native["aligned_query"] == native["aligned_reference"] == sequence.replace("U", "T")
        assert len(native["coordinates"]) == 2
        scores = grading["scores"]
        assert scores["paired_positions"] == scores["identical_positions"] == 8
        assert scores["paired_identity"] == scores["query_paired_coverage"] == 1
        assert scores["denominators"]["paired_identity"] == 8
        measured = numerical(store.get(result["result"]["observation_ref"]))
        for alias, component in (("identity_fraction", "paired_identity"),
                ("query_coverage", "query_aligned_coverage"), ("target_coverage", "reference_aligned_coverage")):
            assert measured[alias] == scores[component]
        assert native["native_format"] == "biopython_pairwise_native_v2"
        for field in ("paired_positions", "identical_positions", "identity_fraction", "query_coverage", "reference_coverage"):
            assert field not in native
        assert result["result"]["identity_fraction"] == scores["paired_identity"]
        assert result["result"]["reference_coverage"] == scores["reference_aligned_coverage"]
        assert measured["paired_positions"] == 8 and measured["paired_identity"] == 1
        assert measured["query_length"] == measured["reference_length"] == 8
        assert store.count("observation") == 1 and operation_count(store, "sequence.align") == 1
        assert registry.execute("sequence.align", args, operation_key="align") == result
        assert store.count("observation") == 1 and operation_count(store, "sequence.align") == 1
        assert "sheet" not in result["result"] and "scores" not in result["result"]
        assert result["result"]["local_job"]["policy"]["memory_bytes"] == 20 * 1024**3
        assert result["result"]["local_job"]["policy"]["scratch_bytes"] == 4 * 1024**3
    with Store(directory) as store:
        saved = only_grading(store, source["id"])
        assert store.get_artifact(source["artifact_ref"]) == native_bytes
        assert calculate_biopython_pairwise_scores(saved["sheet"]) == scores
        assert operation_count(store, "sequence.align") == 1


def test_real_local_no_alignment_is_zero_positions_and_unknown_identity(tmp_path):
    fasta = tmp_path / "pair.fna"
    fasta.write_text(">query\nAAAA\n>reference\nTTTT\n")
    with Store(tmp_path / "state") as store:
        query, reference = store.create_problem(fasta, molecule="dna")["subject_refs"]
        result = ToolRegistry(store).execute("sequence.align", {"query_ref": query,
            "reference_ref": reference, "molecule": "dna", "mode": "local"}, operation_key="no-alignment")
        assert result["status"] == "completed", result
        grading = only_grading(store, result["result"]["source_ref"])
        assert grading["sheet"]["alignment_state"] == "no_alignment"
        assert grading["scores"]["paired_positions"] == 0
        assert grading["scores"]["paired_identity"] is None
        assert result["result"]["identity_fraction"] is None
        assert result["result"]["query_coverage"] == result["result"]["reference_coverage"] == 0
        values = numerical(store.get(result["result"]["observation_ref"]))
        assert values["paired_positions"] == 0 and values["query_paired_coverage"] == 0
        assert "paired_identity" not in values and "identity_fraction" not in values
        assert store.count("observation") == 1


def test_valid_gap_only_native_fixture_does_not_publish_zero_denominator_identity(tmp_path, monkeypatch):
    """A real Biopython zero-gap-cost output injected at the worker seam.

    The standard selected ToolRegistry alignment uses different gap costs; this
    case verifies publication of a valid native format, not selectable costs.
    """
    from gene_annotation_episode.domain import canonical
    from gene_annotation_episode.tools import SequenceWork
    native = json.loads((ROOT / "verification/tool_graders_batch_001/integration/gap_only.native_fixture.json").read_text())
    native_bytes = canonical(native).encode()
    fasta = tmp_path / "pair.fna"
    fasta.write_text(">query\nA\n>reference\nT\n")
    with Store(tmp_path / "state") as store:
        query_ref, reference_ref = store.create_problem(fasta, molecule="dna")["subject_refs"]
        registry = ToolRegistry(store)
        calls = []
        async def supplied_worker(operation, arguments, *, directory):
            assert not store.db.in_transaction
            assert operation == "align_pair" and arguments["query"] == "A" and arguments["reference"] == "T"
            calls.append(operation)
            output = directory / "supplied-native-result.json"
            output.write_bytes(native_bytes)
            return SequenceWork(output, {"fixture": "real_native_zero_gap_penalty_output"})
        monkeypatch.setattr(registry, "_sequence_worker_async", supplied_worker)
        args = {"query_ref": query_ref, "reference_ref": reference_ref, "molecule": "dna", "mode": "global"}
        result = registry.execute("sequence.align", args, operation_key="gap-only-native")
        assert result["status"] == "completed", result
        source = store.get(result["result"]["source_ref"])
        assert store.get_artifact(source["artifact_ref"]) == native_bytes
        grading = only_grading(store, source["id"])
        assert grading["sheet"]["native_result"]["identity_fraction"] == 0.0
        assert result["result"]["identity_fraction"] is None
        assert result["result"]["query_coverage"] == result["result"]["reference_coverage"] == 1
        assert grading["scores"]["paired_positions"] == 0
        assert grading["scores"]["paired_identity"] is None
        assert grading["scores"]["denominators"]["paired_identity"] == 0
        values = numerical(store.get(result["result"]["observation_ref"]))
        assert "identity_fraction" not in values and "paired_identity" not in values
        assert values["alignment_columns"] == 2 and values["alignment_identity"] == 0
        assert values["query_gap_columns"] == values["reference_gap_columns"] == 1
        assert registry.execute("sequence.align", args, operation_key="gap-only-native") == result
        assert calls == ["align_pair"] and store.count("observation") == 1
        assert operation_count(store, "sequence.align") == 1


@pytest.mark.parametrize("mode,query,reference,expected", [
    ("local", "TTACGTTGCAAA", "ACGTTGCA", {"alignment_columns": 8, "paired_positions": 8,
        "identical_positions": 8, "query_paired_coverage": 8 / 12, "alignment_identity": 1.}),
    ("global", "ACGTTGCA", "ACGTCGCA", {"alignment_columns": 8, "paired_positions": 8,
        "identical_positions": 7, "substituted_positions": 1, "paired_identity": 7 / 8}),
    ("global", "ACGTAAAACGT", "ACGTAAACGT", {"alignment_columns": 11, "paired_positions": 10,
        "identical_positions": 10, "reference_gap_columns": 1, "paired_identity": 1.,
        "alignment_identity": 10 / 11, "query_paired_coverage": 10 / 11}),
])
def test_actual_alignment_publication_retains_nontrivial_denominators(tmp_path, mode, query, reference, expected):
    fasta = tmp_path / "pair.fna"
    fasta.write_text(f">query\n{query}\n>reference\n{reference}\n")
    with Store(tmp_path / "state") as store:
        query_ref, reference_ref = store.create_problem(fasta, molecule="dna")["subject_refs"]
        result = ToolRegistry(store).execute("sequence.align", {"query_ref": query_ref,
            "reference_ref": reference_ref, "molecule": "dna", "mode": mode},
            scope={"subject_refs": [query_ref]}, operation_key="nontrivial-alignment")
        assert result["status"] == "completed", result
        grading = only_grading(store, result["result"]["source_ref"])
        observation = store.get(result["result"]["observation_ref"])
        values = numerical(observation)
        for name, expected_value in expected.items():
            assert grading["scores"][name] == pytest.approx(expected_value)
            assert values[name] == pytest.approx(expected_value)
        assert grading["scores"]["denominators"]["query_paired_coverage"] == len(query)
        assert observation["subject_refs"] == [query_ref]
        assert observation["source_subject_refs"] == [reference_ref]
        assert store.count("observation") == 1 and operation_count(store, "sequence.align") == 1


def test_real_meta_prediction_grades_unshifted_result_then_publishes_parent_coordinates(tmp_path):
    region, offset = gene_input(), 13
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="N" * offset + region + "N" * 11,
                                       molecule="dna")["subject_refs"]
        registry = ToolRegistry(store)
        args = {"subject_ref": target, "mode": "meta", "code": 11,
                "start": offset, "end": offset + len(region)}
        result = registry.execute("genes.predict", args, operation_key="meta-offset")
        assert result["status"] == "completed", result
        assert result["result"]["count"] == 1
        grading = only_grading(store, result["result"]["source_ref"])
        sheet, scores = grading["sheet"], grading["scores"]
        assert sheet["mode"] == "meta" and sheet["translation_code"] == 11
        assert sheet["input_start"] == offset and sheet["input_length"] == 306
        row, = scores["candidates"]
        assert row["relative_interval"] == [2, 305] and row["parent_interval"] == [15, 318]
        assert row["interval_length_nt"] == 303 and row["protein_length_aa"] == 101
        assert row["terminal_stop_count"] == 0 and row["internal_stop_count"] == 0
        assert row["partial_begin"] is row["partial_end"] is True
        assert scores["summary"]["union_coding_bases"] == 303
        assert scores["summary"]["coding_coverage"] == 303 / 306
        feature = store.get(result["result"]["records"][0]["feature_ref"])
        assert feature["segments"] == [{"start": 15, "end": 318}]
        native = json.loads(store.get_artifact(store.get(result["result"]["source_ref"])["artifact_ref"]))
        assert native["candidates"][0]["start"] == 15
        assert sheet["native_result"]["candidates"][0]["start"] == 2
        measured = numerical(store.get(result["result"]["records"][0]["observation_ref"]))
        assert measured["interval_length_nt"] == 303 and measured["protein_length_aa"] == 101
        assert measured["native_confidence"] == row["native_confidence_percent"]
        assert measured["model_score"] == row["native_score"]
        assert calculate_prodigal_scores(json.loads(json.dumps(sheet))) == scores
        assert registry.execute("genes.predict", args, operation_key="meta-offset") == result
        assert store.count("observation") == 1 and operation_count(store, "genes.predict") == 1


@pytest.mark.parametrize("molecule,sequence,gc", [("dna", "ACGTNN", .5), ("rna", "ACGUNN", .5),
                                               ("protein", "ACGTNN", None), ("unspecified", "ACGTNN", None)])
def test_declared_molecule_controls_composition_and_missing_quality_stays_unknown(tmp_path, molecule, sequence, gc):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence=sequence, molecule=molecule)["subject_refs"]
        result = ToolRegistry(store).execute("sequence.inspect", {"subject_ref": target}, operation_key="inspect")
        assert result["status"] == "completed", result
        observation = store.get(result["result"]["observation_ref"])
        grading = only_grading(store, observation["source_ref"])
        scores = grading["scores"]
        assert scores["length"] == 6 and scores["gc_fraction"] == gc
        assert scores["quality_observation_count"] is None and scores["mean_phred"] is None
        assert ("gc_fraction" in numerical(observation)) == (gc is not None)
        assert "mean_phred" not in numerical(observation)
        if molecule in {"dna", "rna"}:
            assert scores["gc_denominator"] == 4 and scores["ambiguity_fraction"] == 2 / 6
        assert calculate_sequence_composition_scores(grading["sheet"]) == scores
        assert store.count("observation") == 1


def test_read_quality_uses_complete_original_members_and_offline_threshold_recalculation(tmp_path, monkeypatch):
    directory = tmp_path / "state"
    with Store(directory) as store:
        target, reads, content = quality_library(store, tmp_path, long_read=True)
        registry = ToolRegistry(store)
        args = {"subject_refs": [row["id"] for row in reads]}
        result = registry.execute("reads.inspect", args, operation_key="read-qc")
        assert result["status"] == "completed", result
        source = store.get(result["result"]["source_ref"])
        collection = only_grading(store, source["id"])
        assert collection["row_count"] == 2
        graded_rows = [json.loads(line) for line in store.get_artifact(collection["rows_artifact_ref"]).splitlines()]
        assert [row["subject_ref"] for row in graded_rows] == args["subject_refs"]
        high, low = [row["grading"] for row in graded_rows]
        assert high["sheet"]["quality_encoding"] == low["sheet"]["quality_encoding"] == "phred33"
        assert len(high["sheet"]["quality"]) == 16000 and high["sheet"]["quality"].endswith("!")
        assert high["scores"]["quality_observation_count"] == 16000
        assert high["scores"]["mean_phred"] == 40 * 15999 / 16000
        assert high["scores"]["expected_error_count"] == pytest.approx(15999 * .0001 + 1)
        assert low["scores"]["mean_phred"] == 0 and low["scores"]["expected_error_count"] == 16000
        observations = [store.get(row["observation_ref"]) for row in result["result"]["records"]]
        assert [row["subject_refs"] for row in observations] == [[row["id"]] for row in reads]
        assert numerical(observations[0])["mean_phred"] == high["scores"]["mean_phred"]
        assert numerical(observations[1])["mean_phred"] == 0
        assert store.get_artifact(store.get(store.get(target)["source_refs"][0])["artifact_ref"]) == content
        assert result["published_batch"]["published_rows_total"] == 2
        assert registry.execute("reads.inspect", args, operation_key="read-qc") == result
        assert operation_count(store, "reads.inspect") == 1 and store.count("observation") == 2
    with Store(directory) as store:
        collection = only_grading(store, source["id"])
        saved = json.loads(store.get_artifact(collection["rows_artifact_ref"]).splitlines()[0])["grading"]
        before = deepcopy(saved)
        monkeypatch.setattr(socket, "create_connection", lambda *a, **k: pytest.fail("network during recalculation"))
        monkeypatch.setattr(ToolRegistry, "execute", lambda *a, **k: pytest.fail("tool rerun during recalculation"))
        assert calculate_sequence_composition_scores(saved["sheet"]) == saved["scores"]
        changed = calculate_sequence_composition_scores(saved["sheet"], quality_thresholds=(0, 40, 41))
        assert [row["count_at_or_above"] for row in changed["quality_thresholds"]] == [16000, 15999, 0]
        assert saved == before and store.count("observation") == 2


@pytest.mark.parametrize("mismatch", ["provider", "native_artifact_ref"])
def test_source_grading_custody_rejects_cross_source_identity(tmp_path, mismatch):
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="ACGT", molecule="dna")["subject_refs"]
        result = ToolRegistry(store).execute("sequence.inspect", {"subject_ref": target})
        observation = store.get(result["result"]["observation_ref"])
        source = store.get(observation["source_ref"])
        bad = retain_tool_grading(store, provider="wrong.provider" if mismatch == "provider" else source["provider"],
            native_artifact_ref=(store.artifact("other native result", "text/plain")
                                 if mismatch == "native_artifact_ref" else source["artifact_ref"]),
            grading={"sheet": None, "scores": None})
        body = {key: value for key, value in source.items() if key not in {"id", "record_type", "origin"}}
        body["auxiliary_artifact_refs"] = [bad]
        invalid = store.put("source", body, origin="tool")
        with pytest.raises(ContractError, match="^tool_grading_source_custody_mismatch$"):
            source_tool_gradings(store, invalid["id"])
        assert only_grading(store, source["id"])["scores"]["length"] == 4
        assert store.count("observation") == 1
        assert store.get(bad)["media_type"] == MEDIA_TYPE


@pytest.mark.parametrize("operation,module,facade", [
    ("sequence.align", "biopython_pairwise_grader", "grade_biopython_pairwise"),
    ("genes.predict", "prodigal_grader", "grade_prodigal"),
    ("sequence.inspect", "sequence_composition_grader", "grade_sequence_composition"),
])
def test_grader_rejection_preserves_native_work_and_explicit_failure_without_zero_scores(
        tmp_path, monkeypatch, operation, module, facade):
    import importlib
    code = "synthetic_malformed_grader_input"
    def reject(*args, **kwargs):
        raise ValueError(code)
    monkeypatch.setattr(importlib.import_module("gene_annotation_episode." + module), facade, reject)
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence=gene_input(), molecule="dna")["subject_refs"]
        args = ({"query_ref": target, "reference_ref": target, "molecule": "dna", "mode": "global"}
                if operation == "sequence.align" else {"subject_ref": target, "mode": "meta", "code": 11}
                if operation == "genes.predict" else {"subject_ref": target})
        registry = ToolRegistry(store)
        result = registry.execute(operation, args, operation_key="grading-failure")
        assert result["status"] == "partial", result
        assert result["feedback"]["category"] == "grading_input"
        assert code in json.dumps(result["feedback"])
        sources = [row for row in store.list("source") if source_tool_gradings(store, row["id"])]
        source, = sources
        grading = only_grading(store, source["id"])
        assert grading == {"sheet": None, "scores": None,
                           "failure": {"code": code, "category": "grading_input"}}
        native = json.loads(store.get_artifact(source["artifact_ref"]))
        if operation == "sequence.align":
            assert native["aligned"] and native["native_score"] == 612
        elif operation == "genes.predict":
            assert native["candidates"][0]["native_score"] > 0
        else:
            assert native["length"] == 306
        assert store.count("observation") == 1
        assert "paired_identity" not in numerical(store.list("observation")[0])
        assert "mean_phred" not in numerical(store.list("observation")[0])
        assert registry.execute(operation, args, operation_key="grading-failure") == result
        assert store.count("observation") == operation_count(store, operation) == 1


def test_read_batch_grading_failure_preserves_valid_neighbor_and_member_identity(tmp_path, monkeypatch):
    from gene_annotation_episode import sequence_composition_grader as module
    original = module.grade_sequence_composition
    def reject_low_quality(sequence, **kwargs):
        if kwargs["quality"] == "!" * len(sequence):
            raise ValueError("synthetic_one_member_grading_failure")
        return original(sequence, **kwargs)
    monkeypatch.setattr(module, "grade_sequence_composition", reject_low_quality)
    with Store(tmp_path / "state") as store:
        _, reads, _ = quality_library(store, tmp_path)
        registry = ToolRegistry(store)
        args = {"subject_refs": [row["id"] for row in reads]}
        result = registry.execute("reads.inspect", args, operation_key="partial-read-grading")
        assert result["status"] == "partial", result
        assert result["feedback"] == {"category": "grading_input", "code": "tool_grading_input_rejected",
            "failures": [{"category": "grading_input", "code": "synthetic_one_member_grading_failure"}]}
        collection = only_grading(store, result["result"]["source_ref"])
        rows = [json.loads(line) for line in store.get_artifact(collection["rows_artifact_ref"]).splitlines()]
        assert [row["subject_ref"] for row in rows] == args["subject_refs"]
        assert rows[0]["grading"]["scores"]["mean_phred"] == 35
        assert rows[1]["grading"]["scores"] is None and rows[1]["grading"]["sheet"] is None
        records = result["result"]["records"]
        assert numerical(store.get(records[0]["observation_ref"]))["mean_phred"] == 35
        assert "mean_phred" not in numerical(store.get(records[1]["observation_ref"]))
        assert store.count("observation") == 2 and result["published_batch"]["published_rows_total"] == 2
        assert registry.execute("reads.inspect", args, operation_key="partial-read-grading") == result
        assert store.count("observation") == 2 and operation_count(store, "reads.inspect") == 1


def test_offline_api_blast_grading_rejection_retains_native_hsp_and_explicit_failure(tmp_path, monkeypatch):
    from gene_annotation_episode import blast_graders
    from gene_annotation_episode.api_blast import NCBIBlastService
    from test_api_blast_service import Client, submit
    def reject(*args, **kwargs):
        raise ValueError("synthetic_blast_grading_input_failure")
    monkeypatch.setattr(blast_graders, "grade_blast_result", reject)
    with Store(tmp_path / "state") as store:
        target, = store.create_problem(raw_sequence="MACDEFGH", molecule="protein")["subject_refs"]
        client = Client()
        registry = ToolRegistry(store, clients=client)
        service = NCBIBlastService(registry)
        scope = store.validate_scope(None)
        request = {"subject_ref": target, "program": "blastp", "database": "swissprot"}
        submission, event = submit(service, request, scope)
        handle = event["native_handle"]
        prepared = service.prepare("api.blast.fetch", request, {}, scope=scope,
            previous_events=[], handle=handle)
        fetched = service.invoke(prepared)
        result = service.publish(request, {}, fetched, scope, "blast-grading-failure",
            submission_snapshot=submission, handle=handle)
        assert result["status"] == "partial", result
        assert result["feedback"] == {"category": "grading_input", "code": "tool_grading_input_rejected",
            "failures": [{"category": "grading_input", "code": "synthetic_blast_grading_input_failure"}]}
        source = store.get(result["result"]["source_ref"])
        assert store.get_artifact(source["artifact_ref"]) == fetched.content
        grading = only_grading(store, source["id"])
        assert grading["sheet"] is grading["scores"] is None
        assert grading["failure"]["code"] == "synthetic_blast_grading_input_failure"
        values = numerical(store.get(result["result"]["records"][0]["observation_ref"]))
        assert values["bitscore"] == 31.5 and values["evalue"] == 1e-5
        assert store.count("observation") == 1 and len(client.calls) == 2
        assert service.publish(request, {}, fetched, scope, "blast-grading-failure",
            submission_snapshot=submission, handle=handle) == result
        assert store.count("observation") == 1 and len(client.calls) == 2
        assert operation_count(store, "internal.api_service.ncbi_blast.result") == 1
