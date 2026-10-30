"""Controlled original-source assay population and saved-only typed return.

Scientific selections and stopping controllers are explicit fixtures. This is
not configured-model literature execution and creates no annotation assessment.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from functools import partial
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace


OUTPUT = Path(__file__).resolve().parent
ROOT = OUTPUT.parents[2]
EVIDENCE = OUTPUT.parent
PIN = EVIDENCE / "literature_model_run_023/pin_001"
PIN_SHA = "4f2233d6bae4e5078a157a514051b41fe320a4f43db6551efc95a89ff2a95ef7"
SOURCE_CASE = EVIDENCE / "calibration_case_025"
COMPONENTS = ["protein_amount", "corrected_activity"]
FIELDS = {"HFP": "reported_reference_amount", "IMP": "comparison_recipe_cells"}
BASIS = "nominal_recipe"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_new(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def verify_pin():
    path = PIN / "SOURCE_MANIFEST.json"
    assert sha(path) == PIN_SHA
    manifest = json.loads(path.read_bytes())
    expected = set()
    for row in manifest["files"]:
        relative = row["pin_relative_path"]
        assert relative not in expected
        expected.add(relative)
        path = (PIN / relative).resolve()
        assert path.is_relative_to(PIN) and not path.is_symlink()
        assert path.stat().st_size == row["size"] and sha(path) == row["sha256"]
    actual = {str(p.relative_to(PIN)) for p in PIN.rglob("*") if p.is_file()
              and p != PIN / "SOURCE_MANIFEST.json"}
    assert actual == expected
    return len(expected)


def configure():
    assert verify_pin() == 631
    sys.dont_write_bytecode = True
    # The repository's virtualenv is a dependency installation, not a mutable
    # application import root. Retain it while excluding repository/test roots.
    sys.path[:] = [str(PIN), str(PIN / "tests"), *[entry for entry in sys.path
        if entry and Path(entry).resolve() not in {ROOT, ROOT / "tests", OUTPUT}]]


def rebind(value, old, new):
    if isinstance(value, dict):
        return {key: rebind(child, old, new) for key, child in value.items()}
    if isinstance(value, list):
        return [rebind(child, old, new) for child in value]
    return new if value == old else value


def table_state(store):
    return {row[0]: store.db.execute('SELECT count(*) FROM "' + row[0] + '"').fetchone()[0]
        for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")}


def main(directory):
    configure()
    from gene_annotation_episode import providers
    from gene_annotation_episode.communication import form_with_facts, plain, validate_form
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.episode_receipts import EpisodeReceipts
    from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    from gene_annotation_episode.literature_assay_storage import LiteratureAssayRepository, assay_cells_schema
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes
    from gene_annotation_episode.runtime import run_workflow
    from gene_annotation_episode.state import Store
    from gene_annotation_episode.tools import ToolRegistry
    from test_runtime import FixtureController, ScriptedProvider

    directory.mkdir(exist_ok=False)
    blocked_model_calls = []
    def no_model(*args, **kwargs):
        blocked_model_calls.append(True)
        raise AssertionError("controlled_exercise_forbids_model_calls")
    for cls in (providers.ModelConnection, providers._SessionConnection):
        for name in ("__init__", "__aenter__", "complete", "catalog"):
            setattr(cls, name, no_model)
    providers._SessionConnection._rpc = no_model

    scope_info = json.loads((SOURCE_CASE / "PRIMARY_READ_SCOPE_001.json").read_bytes())
    source_paths = scope_info["source_paths"]
    for item in source_paths:
        assert sha(Path(item["path"])) == item["sha256"]
    original = next(item for item in source_paths if item["path"].endswith(".html"))
    projection = next(item for item in source_paths if item["path"].endswith(".txt"))
    existing = json.loads((SOURCE_CASE / "EXISTING_READER_CHECK_001.json").read_bytes())
    expected = {row["arm"]: row["extraction"]["values"]["E"] for row in existing["checks"]}
    assert expected == {"HFP": 8.4, "IMP": 8.8}
    reset = json.loads((OUTPUT / "RESET_001.json").read_bytes())
    assert reset["full_documents_read"] == 20
    metadata = json.loads((PIN / "inputs/SOURCE_INPUT_METADATA.json").read_bytes())
    fasta_path = PIN / "inputs" / metadata["target"]["filename"]
    assert sha(fasta_path) == metadata["target"]["sha256"]
    fasta = fasta_path.read_text()
    assert sum(line.startswith(">") for line in fasta.splitlines()) == 1
    sequence = "".join(line.strip() for line in fasta.splitlines() if not line.startswith(">"))
    assert len(sequence) == 762

    controllers, admitted, argument_sets, child_contexts = [], {}, {}, []
    forms = {arm: obj({FIELDS[arm]: assay_cells_schema(), "amount_basis": {
        "type": "string", "enum": ["unresolved", "nominal_recipe", "independently_calibrated_active_amount"]}})
        for arm in ("HFP", "IMP")}

    with Store(directory / "state") as store:
        store.create_problem(raw_sequence=sequence, molecule=metadata["target"]["molecule"])
        original_ref = store.artifact(Path(original["path"]).read_bytes(), "text/html")
        text_ref = store.artifact(Path(projection["path"]).read_bytes(), "text/plain")
        source = store.put("source", {"provider": "retained.primary_pmc", "accession": "PMC12051542",
            "uri": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/", "artifact_ref": original_ref,
            "text_ref": text_ref, "request_ref": None, "version": "10.1016/j.jbc.2025.108443",
            "retrieved_at": None, "parent_source_refs": []}, origin="caller")
        for row in existing["checks"]:
            args = row["arguments"]
            argument_sets[row["arm"]] = rebind(args, args["source_ref"], source["id"])
        source_count = len(store.list("source"))
        scope = plain(store.validate_scope())

        def inspect_reports(inputs):
            for report in inputs.get("child_reports", ()):
                for arm, field in FIELDS.items():
                    if field not in report:
                        continue
                    assert report["amount_basis"] == BASIS
                    cells = plain(report[field])
                    assert [cell["component"] for cell in cells] == COMPONENTS
                    assert cells[0]["value"] == expected[arm] and cells[0]["unit"] == "uM"
                    assert cells[0]["origin"] == "reported" and cells[0]["status"] == "populated"
                    assert cells[1]["value"] is None and cells[1]["status"] == "unavailable"
                    assert cells[1]["unavailable_reason"] == "endpoint_requires_different_model"
                    assert all(cell["evidence_source_ref"] == source["id"] for cell in cells)
                    assert all(cell["endpoint_kind"] == "other_measured_endpoint" for cell in cells)
                    assert all(cell["arrangement_kind"] == "replacement" for cell in cells)
                    assert store.get(cells[0]["assayed_subject_ref"])["label"] == arm
                    if arm in admitted:
                        assert admitted[arm] == report
                    admitted[arm] = deepcopy(report)

        def commission(arm):
            def select(inputs):
                inspect_reports(inputs)
                return {"selection": {"kind": "episode_child", "role": "literature",
                    "assignment": {"version": "literature_assignment_v1", "question_context_refs": [],
                        "source_refs": [source["id"]], "requested_assay_components": COMPONENTS},
                    "goal": "Retain the reported nominal " + arm + " recipe concentration for the one-pot static optical assay; preserve missing rate/calibration/contamination information.",
                    "scope": scope, "purpose": "Return only protein_amount and corrected_activity, distinguishing nominal recipe amount from calibrated active-site amount.",
                    "schema_json": json.dumps(forms[arm]), "initial_report_json": json.dumps({"amount_basis": "unresolved"})},
                    "report_update": {}}
            return select

        def populate(arm):
            def select(inputs):
                assert inputs["literature_assignment"]["requested_assay_components"] == COMPONENTS
                assert inputs["requested_form"] == forms[arm]
                assert not inputs["child_reports"]
                return {"selection": {"kind": "tool", "tool": "literature.assay.populate",
                    "arguments": argument_sets[arm]}, "report_update": {"amount_basis": BASIS}}
            return select

        def integrate(inputs):
            inspect_reports(inputs)
            assert set(admitted) == {"HFP", "IMP"}
            # A selected source-reference reasoning commit, with no fabricated
            # target hypothesis, observation, assessment or numerical credit.
            commit = {name: [] for name in store.reasoning_schema()["required"]}
            witness = argument_sets["HFP"]["assay"]["molecule"]
            anchor = {k: witness[k] for k in ("source_ref", "start", "end", "quote")}
            anchor["artifact_ref"] = text_ref
            commit["source_subjects"] = [{"alias": "reported_hfp", "reference_type": "assay",
                "source_ref": source["id"], "label": "HFP", "anchor": anchor}]
            return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}

        def controller(path, initial):
            value = FixtureController(str(path), initial, 3 if len(path) == 1 else 1)
            controllers.append(value)
            return value

        provider = ScriptedProvider([commission("HFP"), populate("HFP"), commission("IMP"), populate("IMP"), integrate])
        scorer = ScientificFindingProgress(FindingProgressPolicy(1))
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=directory / "run", controller_factory=controller, project_credit=scorer,
            goal="Evaluate the reported HFP/IMP nominal recipe amounts and preserve unavailable corrected activity for this reference-source optical endpoint.",
            initial_known_record_refs=[source["id"]],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[source["id"]]),),
            binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0 and not blocked_model_calls
        assert len(provider.contexts) == 5
        assert [item.scores for item in controllers] == [[0, 0, 0], [0], [0]]
        assert not store.list("observation") and not store.list("assessment")
        assert len(store.list("source")) == source_count + 2
        counts = table_state(store)
        assert counts["runtime_actions"] == counts["runtime_observations"] == 5
        assert counts["runtime_report_attempts"] == counts["runtime_forms"] == 2
        assert counts["literature_assay_operations"] == counts["literature_assay_received"] == 2
        operations = []
        receipts = EpisodeReceipts.__new__(EpisodeReceipts)
        receipts.store, receipts.db, receipts.run_id = store, store.db, summary["run_id"]
        for row in store.db.execute("SELECT * FROM literature_assay_operations ORDER BY rowid"):
            outcome = json.loads(row["outcome"])
            repo = LiteratureAssayRepository(store, row["run_id"])
            saved = repo.read(outcome["result"]["sheet_ref"])
            args = json.loads(store.get_artifact(store.get(outcome["result"]["sheet_ref"])["request_ref"]))["arguments"]
            arm = saved["sheet"]["extraction"]["assay"]["molecule"]["value"]
            assert args == argument_sets[arm]
            assert saved["sheet"]["extraction"]["values"]["E"] == expected[arm]
            assert all(v is None for k, v in saved["sheet"]["extraction"]["values"].items() if k != "E")
            episode = store.db.execute("SELECT * FROM runtime_episodes WHERE run_id=? AND episode_id=?",
                (row["run_id"], row["episode_id"])).fetchone()
            request = json.loads(episode["request"])
            replay_context = {"path": json.loads(episode["path"]),
                "scope": request["message"]["scope"],
                "assignment": request["message"].get("episode_assignment", {}),
                "request": request, "received_record_refs": list(receipts.known(row["episode_id"]))}
            operations.append({"run_id": row["run_id"], "episode_id": row["episode_id"],
                "operation_key": row["operation_key"], "arm": arm, "arguments": args,
                "sheet_ref": outcome["result"]["sheet_ref"], "outcome": outcome,
                "replay_context": replay_context})
        forms_saved = [dict(row) for row in store.db.execute("SELECT * FROM runtime_forms ORDER BY rowid")]
        attempts = [dict(row) for row in store.db.execute("SELECT * FROM runtime_report_attempts ORDER BY rowid")]
        assert all(row["failure"] is None for row in attempts)
        save_new(directory / "CONTROLLED_RESULT.json", {"model_backed": False,
            "fixture_kind": "original_source_values_with_scripted_scientific_choices_and_controllers",
            "source_ref": source["id"], "source_original_artifact": original_ref, "source_text_artifact": text_ref,
            "source_paths": source_paths, "target_fasta_sha256": sha(fasta_path),
            "summary": summary, "admitted": admitted, "operations": operations,
            "counts": counts, "controller_scores": [item.scores for item in controllers],
            "model_calls_attempted": blocked_model_calls,
            "limitations": ["Nominal recipe amount is not calibrated active-site amount.",
                "Exact source quotes do not prove scientific role assignments.",
                "No matched blank/rate/contamination/recovery/nuisance-control inputs supplied.",
                "Supplement remains uninspected; original025 access exception preserved."]})

    # A genuinely read-only reopen. Neither initialization/migration nor the
    # reader/calculator is used to reconstruct the original admitted subset.
    class ReadOnlyStore(Store):
        def __init__(self, path):
            self.path = Path(path).resolve()
            self.db = sqlite3.connect("file:" + str(self.path / "state.sqlite3") + "?mode=ro&immutable=1", uri=True)
            self.db.row_factory = sqlite3.Row
            self._savepoint = 0
            self.db.create_function("library_scope_record", 2, self._scope_filter_record)
        def get_artifact(self, ref):
            assert ref not in {original_ref, text_ref}, "primary_artifact_reacquisition_forbidden"
            return super().get_artifact(ref)

    import gene_annotation_episode.literature_assay_inputs as reader
    import gene_annotation_episode.literature_activity_calculations as calculator
    def no_recompute(*args, **kwargs):
        raise AssertionError("saved_only_reconstruction_forbids_source_parser_and_calculator")
    reader.read_assay_inputs = no_recompute
    calculator.populate_corrected_activity = no_recompute
    database_path = directory / "state/state.sqlite3"
    assert not database_path.with_name(database_path.name + "-wal").exists()
    before_sha = sha(database_path)
    reconstructed = {}
    with ReadOnlyStore(directory / "state") as reopened:
        before = table_state(reopened)
        repo = LiteratureAssayRepository(reopened, operations[0]["run_id"])
        for operation in operations:
            arm = operation["arm"]
            frozen_context = operation["replay_context"]
            context = BindingContext(operation["run_id"], operation["episode_id"], "literature",
                frozen_context["path"], frozen_context["scope"], frozen_context["assignment"],
                frozen_context["request"], frozen_context["received_record_refs"])
            assert repo.populate(context, operation["arguments"], operation["operation_key"]) == operation["outcome"]
            cells = repo.project_cells([operation["sheet_ref"]],
                permitted_record_refs=[operation["sheet_ref"]], components=COMPONENTS)
            assert cells == admitted[arm][FIELDS[arm]]
            repo.validate_returned_values(cells, permitted_record_refs=[operation["sheet_ref"]])
            frozen = next(row for row in forms_saved if row["episode_id"] == operation["episode_id"])
            facts, form = json.loads(frozen["facts"]), json.loads(frozen["form"])
            interpretations = facts.pop("interpretations")
            assert form_with_facts(interpretations, forms[arm], facts) == form == admitted[arm]
            validate_form(form, forms[arm], lambda ref, namespace=None:
                reopened.get(ref).get("record_type") == namespace and bool(reopened.reference_subset([ref], scope)))
            reconstructed[arm] = {"cells": cells, "original_facts_rebuild_exact_form": True,
                "original_outcome_replay_equal": True, "amount_basis": form["amount_basis"]}
        assert before == table_state(reopened) and reopened.db.total_changes == 0
    assert sha(database_path) == before_sha
    assert verify_pin() == 631
    imports = []
    for name, module in sorted(sys.modules.items()):
        if name.split(".")[0] in {"gene_annotation_episode", "method_loop"} and getattr(module, "__file__", None):
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(PIN), (name, str(path))
            imports.append({"module": name, "path": str(path), "sha256": sha(path)})
    save_new(directory / "RECONSTRUCTION.json", {"status": "passed", "read_only": True,
        "primary_source_io_forbidden": True, "source_parser_and_calculator_forbidden": True,
        "database_sha256_unchanged": before_sha, "original_action_and_observation_counts_unchanged": True,
        "reconstructed": reconstructed, "pin_files_unchanged": 631})
    save_new(directory / "IMPORT_PROOF.json", {"all_runtime_imports_under_selected_pin": True,
        "pin_manifest_sha256": PIN_SHA, "imports": imports})
    print(json.dumps({"status": "passed", "model_backed": False, "admitted_numerical_cells": 4,
        "protein_amounts_uM": expected, "corrected_activity": None,
        "corrected_activity_reason": "endpoint_requires_different_model", "ordinary_observations": 5,
        "scientific_credit": 0, "verified_runtime_imports": len(imports), "saved_only_reconstruction": True}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    destination = args.directory.resolve()
    assert destination.is_relative_to(OUTPUT) and destination != OUTPUT
    try:
        main(destination)
    except BaseException as error:
        if destination.is_dir():
            save_new(destination / "FAILURE.json", {"type": type(error).__name__, "message": str(error)})
        raise
