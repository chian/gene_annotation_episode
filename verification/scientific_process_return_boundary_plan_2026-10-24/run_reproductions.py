"""Read-only boundary reproductions; all generated data stays beside this file.

No production replacement, job execution, transport, or provider invocation.
The only pytest invocation is the pre-existing isolated failing regression.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def sources():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ("gene_annotation_episode", "method_loop", "tests")
            for p in sorted((ROOT / folder).rglob("*.py"))}


def observed(fn):
    try:
        value = fn()
        return {"accepted": True, "value": value}
    except Exception as exc:
        return {"accepted": False, "exception": type(exc).__name__,
                "message": str(exc), "diagnostic": getattr(exc, "diagnostic", None)}


def main():
    before = sources()
    (HERE / "tmp").mkdir(exist_ok=True)
    env = {**os.environ, "TMPDIR": str(HERE / "tmp")}
    args = [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "tests/test_scientific_process_episodes.py::test_mother_report_resolver_honors_process_metadata_and_validates_result_bodies",
        "--tb=short", "--basetemp=" + str(HERE / "pytest-tmp")]
    run = subprocess.run(args, cwd=ROOT, env=env, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (HERE / "isolated-regression.log").write_text(run.stdout)

    from gene_annotation_episode.communication import validate_closed_schema, validate_form
    from gene_annotation_episode.domain import obj
    from gene_annotation_episode.episode_bindings import BindingContext
    from gene_annotation_episode.scientific_process_episodes import ScientificProcessEpisodes
    from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
    from gene_annotation_episode.scientific_process_records import scientific_invocation_ref, validate_selection
    from gene_annotation_episode.scientific_process_reports import build_process_result, report_sources, validate_process_result
    from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
    from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
    from test_scientific_process_episodes import ContractLibrary, PRIMITIVE, CATALOG
    from test_scientific_process_reports import context, snapshot

    old_library = ContractLibrary()
    old_tools = ScientificToolLibrary.freeze(HERE / "legacy-tools", catalog=[PRIMITIVE])
    old_ctx = context(old_library)
    old_result = build_process_result(old_ctx, snapshot(old_ctx))
    old_schema = obj({"chosen_name": report_sources(old_library, old_tools)["scientific_process_results"]["report_schema"]})

    publication = ROOT / "research/slotted_process_library/publications/2026-10-24-001"
    library = ScientificProcessLibrary.freeze(HERE / "current-library", source=publication)
    # Explicit synthetic operation information, not a measured scientific result.
    primitive = {"name": "fixture.inspect", "resources": "local", "description": "Inspect the supplied fixture.",
                 "instructions": "Read only the explicitly supplied fixture input.", "input_schema": obj({})}
    tools = ScientificToolLibrary.freeze(HERE / "current-tools", catalog=[primitive], tool_info=True)
    selection = {"version": "scientific_process_selection_v3", "evidence_axis": library.reference("A104"),
                 "thought_pattern": library.reference("P01"), "child_tool_info": tools.resolve_tool_info([
                     {"name": "fixture.inspect", "resources": "local"}])}
    assignment = {"selection": selection, "evidence_refs": [], "constraints": {}, "context": {}}
    path = (("annotation", "root"), ("scientific_process", "current"))
    ctx = BindingContext("fixture-run", "private-audit", "scientific_process", path,
        {"subject_refs": []}, assignment, {"message": {"episode_assignment": deepcopy(assignment),
        "scientific_invocation_ref": scientific_invocation_ref("fixture-run", path)}})
    result = build_process_result(ctx, snapshot(ctx))
    schema = obj({"chosen_name": report_sources(library, tools)["scientific_process_results"]["report_schema"]})

    # Demonstrate that naming the four current tool-info fields in a return
    # cannot make unrestricted descriptions/instructions a closed parent form.
    info_schema = obj({"selected_information": {"type": "array", "items": obj({
        "name": {"type": "string", "enum": ["fixture.inspect"]},
        "resources": {"type": "string", "enum": ["api", "local", "hpc"]},
        "description": {"type": "string"}, "instructions": {"type": "string"}})}})
    parent_view_schema = deepcopy(info_schema)
    item = parent_view_schema["properties"]["selected_information"]["items"]
    item["properties"].pop("instructions")
    item["required"].remove("instructions")

    legacy_corrected_version_only = deepcopy(old_schema)
    selection_schema = legacy_corrected_version_only["properties"]["chosen_name"]["items"]["properties"]["selection"]
    selection_schema["properties"]["version"]["const"] = "scientific_process_selection_v2"

    setup_missing_resource = observed(lambda: prepare_scientific_binding(
        run_directory=HERE / "setup-missing-resource", source_directory=CATALOG,
        tool_catalog=[PRIMITIVE], child_roles=("scientific_process", "literature")))
    setup_fixed = prepare_scientific_binding(run_directory=HERE / "setup-explicit-resource",
        source_directory=CATALOG, tool_catalog=[{**PRIMITIVE, "resources": "local"}],
        child_roles=("scientific_process", "literature"))
    from test_semantic_actual_tool_retrieval import CONFIG
    semantic_fixed = prepare_scientific_binding(run_directory=HERE / "setup-explicit-resource",
        source_directory=CATALOG, tool_catalog=[{**PRIMITIVE, "resources": "local"}],
        child_roles=("scientific_process", "literature"), tool_retrieval=CONFIG)

    checks = {
        "legacy_full_record": observed(lambda: validate_process_result(old_result, library=old_library, tool_library=old_tools)),
        "legacy_form_current_schema": observed(lambda: validate_form({"chosen_name": [old_result]}, old_schema, lambda *_: True)),
        "legacy_form_change_only_version": observed(lambda: validate_form({"chosen_name": [old_result]}, legacy_corrected_version_only, lambda *_: True)),
        "current_canonical_selection": observed(lambda: validate_selection(selection)),
        "current_full_record_unbound": observed(lambda: validate_process_result(result)),
        "current_full_record_bound_library": observed(lambda: validate_process_result(result, library=library)),
        "current_full_record_bound_tools": observed(lambda: validate_process_result(result, tool_library=tools)),
        "current_full_record_bound_both": observed(lambda: validate_process_result(result, library=library, tool_library=tools)),
        "current_form_current_schema": observed(lambda: validate_form({"chosen_name": [result]}, schema, lambda *_: True)),
        "four_field_info_is_closed_form": observed(lambda: validate_closed_schema(info_schema)),
        "three_field_parent_view_is_closed_form": observed(lambda: validate_closed_schema(parent_view_schema)),
        "setup_without_resource": setup_missing_resource,
        "setup_explicit_resource": {"version": setup_fixed["version"], "tool_library": setup_fixed["configuration"]["tool_library"]},
        "setup_explicit_resource_semantic": {"version": semantic_fixed["version"], "tool_library": semantic_fixed["configuration"]["tool_library"]},
    }
    write("legacy-row.json", old_result)
    write("legacy-current-generated-schema.json", old_schema)
    write("current-row.json", result)
    write("current-generated-schema.json", schema)
    write("checks.json", checks)
    after = sources()
    write("VERIFICATION.json", {"command": args, "returncode": run.returncode,
        "scope": "One existing isolated failing regression and pure record/schema/setup examples only.",
        "production_and_tests_unchanged": before == after,
        "source_sha256_before": before, "source_sha256_after": after,
        "external_calls": 0, "model_calls": 0, "scientific_jobs": 0})
    print(json.dumps({"isolated_returncode": run.returncode, "source_unchanged": before == after,
        "checks": {key: {k: v for k, v in item.items() if k != "value"} for key, item in checks.items()}}, indent=2))


if __name__ == "__main__":
    main()
