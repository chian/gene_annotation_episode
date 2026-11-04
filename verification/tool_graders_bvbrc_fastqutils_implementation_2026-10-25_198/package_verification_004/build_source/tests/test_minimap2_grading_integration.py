"""B002 production custody and selected-child integration.

Native tests run the pinned minimap2 binary on tiny synthetic sequence inputs
through the existing bounded runner. Deliberately malformed/failed process
fixtures are identified separately. Scripted choices test communication, not
scientific interpretation or configured-model decision quality.
"""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import socket
import subprocess

from Bio.Seq import Seq
import pytest

from gene_annotation_episode import read_mapping
from gene_annotation_episode.domain import ContractError, canonical
from gene_annotation_episode.minimap2_grader import (
    calculate_minimap2_placement_scores, calculate_minimap2_query_scores,
)
from gene_annotation_episode.runtime import Workflow
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_grading_artifacts import MEDIA_TYPE, source_tool_gradings
from gene_annotation_episode.tools import ToolRegistry
from test_native_read_mapping import binary, fixture, sequence
from test_published_axis_workflow import PUBLICATION, ScriptedDecisions, select
from test_read_mapping_failures import BAD_SYNTHETIC_ROW, setup_synthetic_process_case
from test_tool_grading_child_returns import RETURN_FORM, fixed_completion_estimate, zero_fixture_credit
from test_tool_grading_publication import numerical, operation_count


ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"memory_bytes": 20 * 1024**3, "scratch_bytes": 4 * 1024**3, "wall_seconds": None}


def grading_collection(store, source_ref):
    """Read only the supplied source's explicit custody, never discover data."""
    source = store.get(source_ref)
    collection, = source_tool_gradings(store, source_ref)
    assert collection["schema"] == "minimap2_grading_collection_v1"
    assert collection["rows_artifact_ref"] in source["auxiliary_artifact_refs"]
    assert collection["query_scores_artifact_ref"] in source["auxiliary_artifact_refs"]
    envelopes = [json.loads(store.get_artifact(ref)) for ref in source["auxiliary_artifact_refs"]
                 if store.get(ref).get("media_type") == MEDIA_TYPE]
    envelope, = envelopes
    assert envelope["provider"] == "minimap2.mapping"
    assert envelope["native_artifact_ref"] == source["artifact_ref"]
    metadata = json.loads(store.get_artifact(source["artifact_ref"]))
    assert metadata["artifacts"]["mappings.paf"] == source["stdout_ref"]
    rows = [json.loads(line) for line in store.get_artifact(collection["rows_artifact_ref"]).splitlines()]
    queries = [json.loads(line) for line in store.get_artifact(collection["query_scores_artifact_ref"]).splitlines()]
    assert len(rows) == collection["placement_count"]
    return collection, rows, queries


def verify_native_join(store, outcome):
    """Join observations, saved sheets and bytes by the exact native locator."""
    result = outcome["result"]
    source = store.get(result["source_ref"])
    raw = store.get_artifact(source["stdout_ref"])
    metadata = json.loads(store.get_artifact(source["artifact_ref"]))
    operands = {}
    for role, filename in (("query", "queries.fasta"), ("reference", "references.fasta")):
        retained = store.get_artifact(metadata["artifacts"][filename])
        assert hashlib.sha256(retained).hexdigest() == metadata["input_metadata"][role + "_fasta_sha256"]
        lines = retained.decode("ascii").splitlines()
        assert len(lines) % 2 == 0 and all(line.startswith(">") for line in lines[::2])
        operands[role] = {lines[index][1:]: lines[index + 1] for index in range(0, len(lines), 2)}
        assert len(operands[role]) == len(lines) // 2
    assert len(operands["query"]) == metadata["input_metadata"]["query_count"]
    assert set(operands["reference"]) == set(result["reference_refs"])
    collection, rows, queries = grading_collection(store, source["id"])
    observations = [store.get(ref) for ref in outcome["record_refs"]
                    if store.get(ref).get("kind") == "alignment"]
    by_locator = {(row["native_minimap2"]["row_start"], row["native_minimap2"]["row_end"]): row
                  for row in observations}
    assert len(by_locator) == len(rows) == result["reported_placement_count"]
    for row in rows:
        locator = (row["row_start"], row["row_end"])
        original = raw[slice(*locator)]
        native = read_mapping.parse_paf_line(original)
        observation = by_locator[locator]
        assert row["line_number"] == observation["native_minimap2"]["line_number"]
        assert row["query_name"] == native["query_name"] == observation["subject_refs"][0]
        assert row["reference_name"] == native["reference_name"] == observation["source_subject_refs"][0]
        sheet, scores = row["grading"]["sheet"], row["grading"]["scores"]
        assert sheet["schema"] == "minimap2_placement_sheet_v1"
        for key, value in native.items():
            assert sheet["native_result"][key] == value
        assert sheet["preset"] == metadata["settings"]["preset"]
        assert sheet["native_version"] == metadata["native_version"]
        assert sheet["native_parameters"] == metadata["settings"]
        for role in ("query", "reference"):
            name = row[role + "_name"]
            assert sheet["metadata"][role]["supplied"] == {"name": name, "length": len(operands[role][name])}
            assert sheet["metadata"][role]["status"] == "valid"
        assert scores == calculate_minimap2_placement_scores(deepcopy(sheet))
        measured = numerical(observation)
        for name in ("paired_positions", "alignment_columns", "native_block_length",
                     "native_ambiguity_count", "inserted_bases", "deleted_bases",
                     "query_paired_coverage", "reference_paired_coverage", "mapping_quality"):
            if scores[name] is None:
                assert name not in measured
            else:
                assert measured[name] == scores[name]
    assert len(queries) == metadata["input_metadata"]["query_count"]
    for query in queries:
        sheets = (row["grading"]["sheet"] for row in rows
                  if row["query_name"] == query["query_metadata"]["name"])
        assert query["scores"] == calculate_minimap2_query_scores(sheets,
            query_metadata=query["query_metadata"], output_complete=query["output_complete"])
        assert query["output_complete"] is collection["output_complete"]
    return source, metadata, collection, rows, queries


@pytest.mark.parametrize("preset", read_mapping.PRESETS)
def test_actual_six_presets_publish_native_numerical_components_and_original_custody(tmp_path, preset):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        args = {**args, "preset": preset, "parameters": {"seed": 19, "max_secondary": 3}}
        before = store.count("observation")
        outcome = tools.execute("reads.map", args, scope=selected["scope"], operation_key="preset-" + preset)
        assert outcome["status"] == "completed", outcome
        source, metadata, collection, rows, queries = verify_native_join(store, outcome)
        assert source["version"] == "2.31-r1302"
        assert len(rows) == len(queries) == 2
        assert collection["output_complete"] is True
        assert metadata["settings"]["preset"] == preset
        assert metadata["settings"]["overrides"] == args["parameters"]
        assert metadata["settings"]["fragment_mode"] == "unpaired"
        assert metadata["settings"]["quality_used_for_mapping"] is False
        command = metadata["commands"]["map"]
        assert command[command.index("-x") + 1] == preset
        assert command[command.index("--seed") + 1] == "19"
        assert command[command.index("-N") + 1] == "3"
        assert "--frag=no" in command and "--cs=long" in command and "-c" in command
        assert metadata["configuration"]["job_limits"] == LIMITS
        assert metadata["configuration"]["executable_sha256"] == hashlib.sha256(Path(binary()).read_bytes()).hexdigest()
        assert all(job["policy"] == LIMITS for job in metadata["local_jobs"].values())
        plus = next(row["grading"]["scores"] for row in rows if row["grading"]["sheet"]["native_facts"]["strand"] == "+")
        minus = next(row["grading"]["scores"] for row in rows if row["grading"]["sheet"]["native_facts"]["strand"] == "-")
        assert (plus["query_length"], plus["reference_length"], plus["paired_positions"],
                plus["inserted_bases"], plus["deleted_bases"], plus["alignment_columns"]) == (5001, 6000, 4998, 3, 2, 5003)
        assert plus["query_paired_coverage"] == pytest.approx(4998 / 5001)
        assert plus["reference_paired_coverage"] == pytest.approx(4998 / 6000)
        assert plus["native_alignment_identity"] == pytest.approx(4998 / 5003)
        assert minus["paired_positions"] == 5000 and minus["native_alignment_identity"] == 1
        assert minus["query_paired_coverage"] == 1 and minus["reference_paired_coverage"] == pytest.approx(5 / 6)
        assert store.count("observation") == before + 3  # Two placements and the existing source-content record.
        assert operation_count(store, "reads.map") == 1 and store.count("annotation") == 0
        assert len([row for row in store.list("source") if row["provider"] == "minimap2.mapping"]) == 1
        assert "minimap2_placement_sheet_v1" not in json.dumps(outcome)
        assert not any("native_line" in row for row in outcome["result"]["records"])
        assert not list(store.path.glob(".native-read-mapping-*"))
        (tmp_path / "numerical-example.json").write_text(json.dumps({"preset": preset, "plus": plus,
            "minus": minus, "native_commands": metadata["commands"]}, indent=2))


def ambiguity_fixture(tmp_path):
    reference = sequence()
    reference = reference[:2500] + "R" + reference[2501:]
    plus = reference[500:5500]
    plus = plus[:2000] + "Y" + plus[2001:]  # Original R != Y; both normalize to N in native cs.
    reads = [plus, str(Seq(reference[500:5500]).reverse_complement())]
    path = tmp_path / "ambiguous.fastq"
    path.write_text("".join(f"@duplicate title\n{value}\n+\n{'I' * len(value)}\n" for value in reads))
    store = Store(tmp_path / "state")
    store.create_problem(path, molecule="dna")
    target, = store.targets()
    tools = ToolRegistry(store, minimap2_executable=binary())
    material = store.register_material(data=">one\n" + reference + "\n>two\n" + reference + "\n",
                                      format="fasta", molecule="dna")
    parsed = store.parse_material(material["id"])
    references = [store.material_reference(row["id"])["id"]
                  for row in store.material_members(parsed["collection_ref"])["members"]]
    result = tools.execute("library.select", {"library_ref": target["id"], "ordinal_ranges": [{"start": 0, "end": 2}]})
    assert result["status"] == "completed", result
    selected = result["result"]
    return store, tools, selected, {"query_selection_ref": selected["selection"]["id"],
        "reference_refs": references, "preset": "map-ont", "parameters": {"secondary": True, "max_secondary": 5}}


def verify_local_example_reader(tmp_path, raw):
    """Replay actual PAF through the existing reader with a synthetic job row.

    This exercises extraction only. The small registered lifecycle below does
    not claim a new independently running native job or episode deployment.
    """
    from gene_annotation_episode.local_example.service import JobStore
    directory = tmp_path / "recorded-block-reader"
    directory.mkdir()
    native = directory / "block.paf"
    native.write_bytes(raw)
    jobs = JobStore(directory)
    try:
        cfg = {"workload_ref": "synthetic-reader-workload", "workspace_ref": "synthetic-reader-workspace"}
        jobs.db.execute("INSERT INTO example_configuration VALUES(1,?)", (canonical(cfg),))
        jobs.save_setup("inputs", {"read_count": 2})
        jobs.db.execute("INSERT INTO detached_jobs(job_ref,workload_ref,state,submitted_at,started_at,finished_at) "
            "VALUES(?,?,?,?,?,?)", ("synthetic-completed-reader-job", cfg["workload_ref"], "completed",
                "2026-10-24T00:00:00+00:00", "2026-10-24T00:00:00+00:00", "2026-10-24T00:00:01+00:00"))
        jobs.db.execute("INSERT INTO mapping_blocks(block_index,read_count,state,elapsed_seconds,result_path,result_sha256) "
            "VALUES(?,?,?,?,?,?)", (0, 2, "completed", 1.0, str(native), hashlib.sha256(raw).hexdigest()))
        jobs.db.commit()
        result = jobs.extract(jobs.handoff("synthetic-completed-reader-job"), 0, "synthetic-reader-owner")
        assert {key: result[key] for key in ("input_reads", "mapped_reads", "reported_alignments",
            "primary_alignments", "reverse_alignments", "aligned_query_bases")} == {
                "input_reads": 2, "mapped_reads": 2, "reported_alignments": 4,
                "primary_alignments": 2, "reverse_alignments": 2, "aligned_query_bases": 20000}
        decoded = [json.loads(line) for line in native.with_suffix(".parsed.jsonl").read_text().splitlines()]
        assert len(decoded) == 4 and all(row["block_length"] == 4999 for row in decoded)
        assert all(next(tag["value"] for tag in row["tags"] if tag["name"] == "nn") == "1" for row in decoded)
        assert jobs.delivered_summary()["reported_alignments"] == 4
    finally:
        jobs.close()


def test_actual_ambiguity_secondary_reverse_and_site_consumers_share_native_row(tmp_path):
    store, tools, selected, args = ambiguity_fixture(tmp_path)
    with store:
        outcome = tools.execute("reads.map", args, scope=selected["scope"], operation_key="ambiguity")
        assert outcome["status"] == "completed", outcome
        source, metadata, collection, rows, queries = verify_native_join(store, outcome)
        assert len(rows) == 4 and len(queries) == 2
        assert {row["grading"]["sheet"]["native_facts"]["strand"] for row in rows} == {"+", "-"}
        for row in rows:
            scores = row["grading"]["scores"]
            assert scores["paired_positions"] == scores["alignment_columns"] == scores["cs_equal_positions"] == 5000
            assert scores["native_matching_bases"] == scores["native_block_length"] == 4999
            assert scores["native_ambiguity_count"] == 1 and scores["native_alignment_identity"] == 1
            assert scores["original_symbol_equal_positions"] is None
            assert scores["original_symbol_substituted_positions"] is None
            assert scores["mapping_quality"] == 0  # Duplicate references make the ambiguity explicit.
            native = row["grading"]["sheet"]["native_result"]
            assert "N" in native["cs"] and "R" not in native["cs"] and "Y" not in native["cs"]
        for query in queries:
            values = query["scores"]
            assert values["counts_by_native_alignment_type"] == {"P": 1, "S": 1}
            assert values["distinct_reference_count"] == 2
            assert values["query_paired_union_positions"] == values["query_span_union_positions"] == 5000
            assert values["query_paired_union_coverage"] == 1
            assert values["paired_position_observation_count"] == values["distinct_correspondence_count"] == 10000
            assert values["alternative_correspondence_positions"] == 5000
            assert values["repeated_correspondence_count"] == values["exact_duplicate_row_count"] == 0
        for strand in ("+", "-"):
            preview = next(row for row in outcome["result"]["records"] if row["strand"] == strand)
            sites = tools.execute("sequence.sites", {"alignment_ref": preview["observation_ref"],
                "positions": [500, 2500, 5499]}, scope=selected["scope"], operation_key="site-" + strand)
            assert sites["status"] == "completed", sites
            rows_at_sites = sites["result"]["sites"]
            assert [row["query_position"] for row in rows_at_sites] == ([0, 2000, 4999] if strand == "+" else [4999, 2999, 0])
            assert rows_at_sites[1]["reference_residue"] == "R"
            assert rows_at_sites[1]["relationship"] == ("substituted" if strand == "+" else "identical")
            assert rows_at_sites[1]["query_residue"] == ("Y" if strand == "+" else "R")
        raw = store.get_artifact(source["stdout_ref"])
        verify_local_example_reader(tmp_path, raw)
        original_observation = store.get(outcome["result"]["records"][0]["observation_ref"])
        payload = {key: deepcopy(original_observation[key]) for key in ("kind", "subject_refs", "source_subject_refs",
            "source_ref", "measurements", "dependencies", "anchor", "operand_intervals", "native_minimap2")}
        payload["native_minimap2"]["row_start"] += 1
        with pytest.raises(ContractError, match="native_minimap2_row_start_not_line_boundary"):
            store.put("observation", payload, origin="tool")
        payload["native_minimap2"] = deepcopy(original_observation["native_minimap2"])
        payload["source_subject_refs"] = [next(ref for ref in args["reference_refs"]
                                               if ref != original_observation["source_subject_refs"][0])]
        with pytest.raises(ContractError, match="native_minimap2_operand_identity_mismatch"):
            store.put("observation", payload, origin="tool")
        (tmp_path / "native-ambiguity.paf").write_bytes(raw)
        (tmp_path / "numerical-example.json").write_text(json.dumps({"placements": rows, "queries": queries,
            "native_commands": metadata["commands"]}, indent=2))


def test_saved_sheets_recalculate_offline_and_committed_operation_replays_without_work(tmp_path, monkeypatch):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        outcome = tools.execute("reads.map", args, scope=selected["scope"], operation_key="offline-replay")
        assert outcome["status"] == "completed", outcome
        source, _, collection, rows, queries = verify_native_join(store, outcome)
        native_bytes = store.get_artifact(source["stdout_ref"])
        source_ref = source["id"]
    with Store(tmp_path / "state") as reopened:
        collection2, rows2, queries2 = grading_collection(reopened, source_ref)
        assert (collection2, rows2, queries2) == (collection, rows, queries)
        sheets = [json.loads(json.dumps(row["grading"]["sheet"])) for row in rows2]
        before = deepcopy(sheets)
        def prohibited(*args, **kwargs):
            pytest.fail("Saved-sheet recalculation or committed-operation replay attempted new work")
        with monkeypatch.context() as blocked:
            blocked.setattr(socket, "create_connection", prohibited)
            blocked.setattr(socket.socket, "connect", prohibited)
            blocked.setattr(subprocess, "Popen", prohibited)
            blocked.setattr(read_mapping, "run_mapping", prohibited)
            for sheet, row in zip(sheets, rows2, strict=True):
                assert calculate_minimap2_placement_scores(sheet) == row["grading"]["scores"]
            for query in queries2:
                assert calculate_minimap2_query_scores((sheet for sheet in sheets
                    if sheet["native_facts"]["query_name"] == query["query_metadata"]["name"]),
                    query_metadata=query["query_metadata"], output_complete=query["output_complete"]) == query["scores"]
            registry = ToolRegistry(reopened, minimap2_executable="/deliberately/unavailable")
            assert registry.execute("reads.map", args, scope=selected["scope"], operation_key="offline-replay") == outcome
        assert sheets == before
        assert reopened.get_artifact(reopened.get(source_ref)["stdout_ref"]) == native_bytes
        assert reopened.count("observation") == 3 and operation_count(reopened, "reads.map") == 1


def test_actual_empty_output_keeps_zero_reported_placements_distinct_from_biological_absence(tmp_path):
    store, tools, target, selected, args = fixture(tmp_path)
    with store:
        material = store.register_material(data=">unmatched\n" + "A" * 1000 + "\n", format="fasta", molecule="dna")
        parsed = store.parse_material(material["id"])
        member, = store.material_members(parsed["collection_ref"])["members"]
        reference = store.material_reference(member["id"])
        args = {**args, "reference_refs": [reference["id"]]}
        outcome = tools.execute("reads.map", args, scope=selected["scope"], operation_key="empty-native")
        assert outcome["status"] == "completed", outcome
        source, _, collection, rows, queries = verify_native_join(store, outcome)
        assert store.get_artifact(source["stdout_ref"]) == b""
        assert collection["output_complete"] is True and collection["placement_count"] == 0 and rows == []
        assert len(queries) == 2
        for query in queries:
            assert query["scores"]["reported_placement_count"] == 0
            assert query["scores"]["query_span_union_positions"] == 0
            assert query["scores"]["query_paired_union_coverage"] == 0
            assert query["scores"]["result_meaning"] == "complete_output_has_zero_reported_placements_not_biological_absence"
        summary = store.get(outcome["result"]["search_result_observation_ref"])
        assert summary["kind"] == "source_content" and numerical(summary)["count"] == 0
        assert store.count("observation") == 1 and store.count("annotation") == 0


@pytest.mark.parametrize("mode", ["partial", "failure"])
def test_synthetic_partial_or_failed_process_retains_valid_siblings_and_incomplete_query_population(tmp_path, mode):
    store, tools, args = setup_synthetic_process_case(tmp_path, mode)
    with store:
        outcome = tools.execute("reads.map", args, operation_key="controlled-" + mode)
        assert outcome["status"] == ("partial" if mode == "partial" else "failed"), outcome
        source, _, collection, rows, queries = verify_native_join(store, outcome)
        assert source["version"] == "synthetic-process-fixture-not-minimap2"
        assert collection["output_complete"] is False
        assert collection["placement_count"] == (2 if mode == "partial" else 0)
        assert len(queries) == 2
        for query in queries:
            assert query["output_complete"] is False
            assert query["scores"]["result_meaning"] == "reported_placements_from_partial_or_unknown_output_no_absence_inference"
            assert query["scores"]["reported_placement_count"] == (1 if mode == "partial" else 0)
        if mode == "partial":
            assert {row["line_number"] for row in rows} == {1, 3}
            assert all(row["grading"]["scores"]["paired_positions"] == 4 for row in rows)
            raw = store.get_artifact(source["stdout_ref"])
            errors = store.get(outcome["result"]["error_source_ref"])
            error, = [json.loads(line) for line in store.get_artifact(errors["artifact_ref"]).splitlines()]
            assert raw[error["row_start"]:error["row_end"]] == BAD_SYNTHETIC_ROW
            assert error["line_number"] == 2
        else:
            assert outcome["result"]["native_returncode"] == 17
        assert operation_count(store, "reads.map") == 1 and store.count("annotation") == 0


def test_nonadjacent_duplicate_synthetic_rows_group_by_exact_query_without_double_counting_union(tmp_path, monkeypatch):
    store, tools, args = setup_synthetic_process_case(tmp_path, "partial")
    original = read_mapping.project_output
    def duplicate_first_row(directory):
        path = Path(directory) / "mappings.paf"
        raw = path.read_bytes()
        path.write_bytes(raw + raw.splitlines(keepends=True)[0])
        return original(directory)
    monkeypatch.setattr(read_mapping, "project_output", duplicate_first_row)
    with store:
        outcome = tools.execute("reads.map", args, operation_key="nonadjacent-synthetic-duplicate")
        assert outcome["status"] == "partial", outcome
        _, _, collection, rows, queries = verify_native_join(store, outcome)
        assert collection["placement_count"] == 3 and [row["line_number"] for row in rows] == [1, 3, 4]
        repeated = next(row["scores"] for row in queries if row["query_metadata"]["name"] == rows[0]["query_name"])
        assert repeated["reported_placement_count"] == 2
        assert repeated["query_paired_union_positions"] == repeated["query_span_union_positions"] == 4
        assert repeated["paired_position_observation_count"] == 8
        assert repeated["distinct_correspondence_count"] == repeated["repeated_correspondence_count"] == 4
        assert repeated["exact_duplicate_row_count"] == 1
        assert repeated["alternative_correspondence_positions"] == 0


def test_synthetic_resource_limit_preserves_row_grading_without_complete_search_claim(tmp_path):
    # This explicitly selected limit belongs to a synthetic waiting process.
    # The actual minimap2 tests use the unchanged 20 GiB / 4 GiB / no-time-limit policy.
    policy = {"memory_bytes": 256 * 1024**2, "scratch_bytes": 2 * 1024**2, "wall_seconds": 1}
    store, tools, args = setup_synthetic_process_case(tmp_path, "resource_after_row", job_limits=policy)
    with store:
        outcome = tools.execute("reads.map", args, operation_key="synthetic-limited-row")
        assert outcome["status"] == "partial", outcome
        assert outcome["feedback"]["code"] == "local_job_resource_limit"
        assert outcome["feedback"]["policy"] == policy
        source, metadata, collection, rows, queries = verify_native_join(store, outcome)
        assert metadata["configuration"]["job_limits"] == policy
        assert collection["output_complete"] is False and len(rows) == 1 and len(queries) == 2
        assert rows[0]["grading"]["scores"]["paired_positions"] == 4
        assert sorted(query["scores"]["reported_placement_count"] for query in queries) == [0, 1]
        assert all(query["output_complete"] is False for query in queries)
        assert outcome["result"]["search_result_observation_ref"] is None
        assert store.count("observation") == 1 and store.count("annotation") == 0


def test_publication_rejects_shifted_grading_row_join_instead_of_reassigning_numbers(tmp_path, monkeypatch):
    store, tools, args = setup_synthetic_process_case(tmp_path, "partial")
    original = tools._retain_mapping_grading
    def shifted(native):
        result = original(native)
        path = native.path("grading-placements.jsonl")
        lines = path.read_text().splitlines(keepends=True)
        assert len(lines) == 2
        path.write_text("".join(reversed(lines)))
        return result
    monkeypatch.setattr(tools, "_retain_mapping_grading", shifted)
    with store:
        outcome = tools.execute("reads.map", args, operation_key="bad-row-join")
        assert outcome["status"] == "partial", outcome
        assert outcome["feedback"]["code"] == "mapping_grading_row_mismatch"
        assert store.count("observation") == 0
        source, = [store.get(ref) for ref in outcome["record_refs"] if store.get(ref).get("provider") == "minimap2.mapping"]
        _, rows, _ = grading_collection(store, source["id"])
        assert [row["line_number"] for row in rows] == [1, 3]  # Original immutable custody survived.


@pytest.mark.parametrize("preset", read_mapping.PRESETS)
def test_current_selected_scientific_child_returns_minimap_numbers_without_extra_action(tmp_path, monkeypatch, preset):
    store, tools, target, selected, args = fixture(tmp_path)
    args = {**args, "preset": preset}
    with store:
        scope = selected["scope"]
        directory = tmp_path / "run"
        descriptor = prepare_scientific_binding(run_directory=directory, source_directory=PUBLICATION,
            tool_catalog=tools.catalog(), child_roles=("scientific_process",))
        library = ScientificProcessLibrary(directory / "scientific-process-library")
        query_refs = [row[0] for row in store.db.execute(
            "SELECT read_ref FROM library_selection_members WHERE selection_ref=? ORDER BY read_ref",
            (args["query_selection_ref"],))]
        commission = {"kind": "episode_child", "role": "scientific_process",
            "goal": "Measure the selected supplied reads against the supplied reference with minimap2 and retain the native correspondence.",
            "scope": scope, "purpose": "Return the recorded numeric placement measurements, with biological function unresolved.",
            "schema_json": json.dumps(RETURN_FORM), "initial_report_json": "{}",
            "assignment": {"selection": {"version": "scientific_process_selection_v3",
                "evidence_axis": library.reference("A101"), "thought_pattern": library.reference("P01"),
                "child_tool_info": [{"name": "reads.map", "resources": "local"}]},
                "evidence_refs": [target["id"], args["query_selection_ref"], *query_refs, *args["reference_refs"]],
                "constraints": {"no_external_acquisition": True}, "context": {"molecule": "dna"}}}
        decisions = ScriptedDecisions([select(commission), select({"kind": "tool", "tool": "reads.map", "arguments": args})])
        workflow = Workflow(store, tools, decisions, directory, "b002-minimap2-child", fixed_completion_estimate,
            zero_fixture_credit, episode_binding_descriptors=[descriptor], episode_record_receipts=True,
            initial_known_record_refs=[], decision_protocol="decision_exchange_v1")
        root = workflow.build("annotation", "root", "Inspect the supplied unnamed sequence material", scope)
        assert workflow.catalog(scope, source=root.source) == []
        assert not workflow.permits_common_action(root.source, "tool")
        parent_info, = [row for row in workflow.scientific_process_binding.tool_library.parent_tool_info()
                        if row["name"] == "reads.map" and row["resources"] == "local"]
        assert set(parent_info) == {"name", "description", "resources"}
        assert parent_info["description"] == tools.catalog()["reads.map"]["description"]
        async def run():
            record = await root.run_async(workflow.context)
            await root.build_result(record)
            return record
        record = asyncio.run(run())
        assert record.units_consumed == 1 and len(decisions.calls) == 2
        child_id = decisions.calls[1]["episode_id"]
        child_info, = decisions.calls[1]["state"]["scientific_process"]["child_tool_info"]
        assert {key: child_info[key] for key in parent_info} == parent_info
        assert (ROOT / "gene_annotation_episode/knowledge/minimap2-placements.md").read_text().strip() in child_info["instructions"]
        assert all(preset in child_info["instructions"] for preset in read_mapping.PRESETS)
        assert "--frag=no" in child_info["instructions"]
        publication_row = store.db.execute("SELECT * FROM tool_operations WHERE name='reads.map'").fetchone()
        publication = json.loads(publication_row["result"])
        assert publication["status"] == "completed", publication
        returned = json.loads(workflow.journal.row("runtime_forms", child_id)["form"])
        assert returned == {"records": publication["record_refs"]}
        source, _, _, rows, _ = verify_native_join(store, publication)
        assert all(row["grading"]["sheet"]["preset"] == preset for row in rows)
        parent_receipts = set(workflow.receipts.known(root.source.episode_id))
        assert set(returned["records"]) <= parent_receipts
        state = workflow.working_state(root.source)
        observations = [row for row in state["observations"] if row["kind"] == "alignment"]
        assert len(observations) == 2
        assert sorted(numerical(row)["paired_positions"] for row in observations) == [4998, 5000]
        assert source["id"] in parent_receipts
        presented = json.dumps(state)
        for forbidden in ("minimap2_placement_sheet_v1", "cg_operations", "cs_operations", "native_line", "measured_counts"):
            assert forbidden not in presented
        for episode_id in (root.source.episode_id, child_id):
            assert store.db.execute("SELECT count(*) FROM runtime_actions WHERE episode_id=?", (episode_id,)).fetchone()[0] == 1
            assert store.db.execute("SELECT count(*) FROM runtime_observations WHERE episode_id=?", (episode_id,)).fetchone()[0] == 1
        before = [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")]
        receipt_count = store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0]
        def prohibited(*args, **kwargs):
            pytest.fail("Redelivery or operation replay reran native work")
        monkeypatch.setattr(read_mapping, "run_mapping", prohibited)
        assert tools.execute("reads.map", args, scope=scope, operation_key=publication_row["operation_key"]) == publication
        decision_index = store.db.execute("SELECT decision_index FROM runtime_actions WHERE episode_id=?",
                                         (root.source.episode_id,)).fetchone()[0]
        workflow.receive_form(root.source, returned, RETURN_FORM, decision_index, redelivery=True)
        assert store.db.execute("SELECT count(*) FROM runtime_record_receipts").fetchone()[0] == receipt_count
        assert [tuple(row) for row in store.db.execute("SELECT * FROM runtime_observations ORDER BY episode_id")] == before
        assert store.count("observation") == 3 and operation_count(store, "reads.map") == 1
        assert store.count("annotation") == 0
        (tmp_path / "typed-return.json").write_text(json.dumps({"return": returned, "preset": preset,
            "numerical_observations": [numerical(row) for row in observations], "parent_actions": 1,
            "child_actions": 1, "decision_calls": len(decisions.calls)}, indent=2))
