"""Synthetic declared records only; none claim native execution or custody."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from gene_annotation_episode.genomic_overlap_inputs import parse_region_set


ROOT = Path(__file__).resolve().parents[2]
PACKET = ROOT / "verification/tool_graders_genomic_overlap_native_contract_2026-10-27_425"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def worked():
    return json.loads((PACKET / "WORKED_EXAMPLE.json").read_text())


def fixture():
    value = worked()
    return value["plan"], value["batch_manifest"]


def job():
    return worked()["plan"]["requested_job"]["native_genomic_overlap"]


def binding():
    return worked()["binding"]


def files(batch):
    return {row["specification"]["file_key"]: row["declaration"] for row in batch["files"]}


def supplied(declaration, raw):
    declaration.update(state="present", sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


def absent(declaration):
    declaration.update(state="absent", sha256=None, size_bytes=None)


def reseal(batch):
    index = files(batch)
    for pair in batch["pairs"]:
        if pair["manifest"] is not None:
            supplied(index[pair["manifest_file_key"]], canonical(pair["manifest"]) + b"\n")


def rehash(plan, batch):
    plan["identity"]["requested_job_sha256"] = digest(plan["requested_job"])
    batch["requested_job_sha256"] = plan["identity"]["requested_job_sha256"]
    batch["plan_sha256"] = digest(plan)
    reseal(batch)


def failure(code, *, stage="input", set_key=None, comparison_key=None, file_key=None):
    return {"code": code, "stage": stage, "set_key": set_key, "comparison_key": comparison_key,
        "file_key": file_key, "field_path": "/fixture", "expected_value": None, "observed_value": None}


def c_case(kind):
    """Modify only supplied C; preserve A/B and its earlier manifest exactly."""
    plan, batch = fixture()
    index = files(batch)
    spec = plan["requested_job"]["native_genomic_overlap"]["request"]["region_sets"][2]
    row = batch["sets"][2]
    if kind in ("empty", "invalid"):
        raw = b"" if kind == "empty" else b"chr1\t10\t10\n"
        original = spec["source"]["file"]
        original.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        original["artifact_ref"] = "fixture:changed:C:" + kind
        parsed = parse_region_set(raw, specification=spec, set_position=2)
        supplied(index["s2:original"], raw)
        row["measured_fingerprint"] = {"set_key": "C", **{k: original[k] for k in ("sha256", "size_bytes", "format")}}
        row["parse_extent"] = parsed["result_extent"]
        supplied(index["s2:parsed"], canonical(parsed) + b"\n")
        if kind == "empty":
            supplied(index["s2:canonical"], b"")
        else:
            absent(index["s2:canonical"])
            batch["failures"] = [failure("invalid_input", set_key="C", file_key="s2:parsed")]
            row["failure_indices"] = [0]
    else:
        parsed = parse_region_set(None, specification=spec, set_position=2)
        supplied(index["s2:parsed"], canonical(parsed) + b"\n")
        row["parse_extent"] = "unavailable"
        absent(index["s2:original"])
        absent(index["s2:canonical"])
        if kind == "missing":
            row.update(input_state="unavailable", measured_fingerprint=None)
            batch["failures"] = [failure("input_unavailable", set_key="C", file_key="s2:original")]
        elif kind == "mismatch":
            raw = b"chr1\t100\t200\n"
            supplied(index["s2:rejected"], raw)
            row.update(input_state="digest_mismatch", measured_fingerprint={"set_key": "C",
                **{k: index["s2:rejected"][k] for k in ("sha256", "size_bytes", "format")}})
            batch["failures"] = [failure("input_digest_mismatch", set_key="C", file_key="s2:rejected")]
        else:
            raise ValueError(kind)
        row["failure_indices"] = [0]
    for pair in batch["pairs"][1:]:
        ordinal = pair["comparison"]["ordinal"]
        for suffix in ("stdout", "stderr"):
            absent(index[f"p{ordinal}:" + suffix])
        if kind in ("empty", "invalid"):
            manifest = pair["manifest"]
            manifest["input_fingerprints"][1] = deepcopy(row["measured_fingerprint"])
            manifest.update(derivation="validated_empty_input" if kind == "empty" else "not_executed_invalid_input",
                outcome="not_executed", software=None, returncode=None, started_at=None, finished_at=None,
                realized_argv=[], environment={}, files=[])
            pair["disposition"] = "analytic_empty" if kind == "empty" else "invalid_input"
        else:
            absent(index[f"p{ordinal}:manifest"])
            pair.update(disposition="input_unavailable", manifest=None, manifest_file_key=None)
        pair["failure_indices"] = [] if kind == "empty" else [0]
    batch["batch_status"] = "complete" if kind == "empty" else "partial"
    rehash(plan, batch)
    return plan, batch


def no_software(*, implementation=False):
    plan, batch = fixture()
    index = files(batch)
    code = "software_identity_mismatch" if implementation else "native_dependency_unavailable"
    batch["failures"] = [failure(code, stage="software")]
    batch["software_verification"].update(state="failed", bedtools_observed=None, version_probe=None, failure_indices=[0])
    for name in ("version_stdout", "version_stderr"):
        absent(index[name])
    if implementation:
        batch["software_verification"]["python_observed"]["sha256"] = "f" * 64
        for row in batch["sets"]:
            row.update(parse_extent=None, failure_indices=[0])
            absent(index[row["parsed_file_key"]])
            absent(index[row["canonical_file_key"]])
    for pair in batch["pairs"]:
        ordinal = pair["comparison"]["ordinal"]
        for suffix in ("manifest", "stdout", "stderr"):
            absent(index[f"p{ordinal}:" + suffix])
        pair.update(disposition="native_unavailable", manifest=None, manifest_file_key=None, failure_indices=[0])
    batch["batch_status"] = "failed"
    return plan, batch


def two_set_job():
    original = job()
    original["request"]["region_sets"] = original["request"]["region_sets"][:2]
    original["request"]["comparisons"] = original["request"]["comparisons"][:1]
    original["inputs"] = original["inputs"][:2]
    original["outputs"] = [r for r in original["outputs"] if r["set_key"] != "C" and
        r["comparison_key"] not in ("comparison_1", "comparison_2")]
    return original


def numerical_example():
    """Recalculate supplied synthetic tables through the unchanged G1 ports."""
    from gene_annotation_episode.genomic_overlap_inputs import (
        parse_bedtools_intersect_wo, extract_overlap_reference_metadata, build_genomic_overlap_sheet,
    )
    from gene_annotation_episode.genomic_overlap_calculations import calculate_genomic_overlap_components
    example = worked()
    request = example["plan"]["requested_job"]["native_genomic_overlap"]["request"]
    sets = [parse_region_set(example["raw_source_strings"][spec["set_key"]].encode(),
        specification=spec, set_position=i) for i, spec in enumerate(request["region_sets"])]
    index = {row["set_key"]: row for row in sets}
    native_pairs = []
    for comparison in request["comparisons"]:
        raw = example["native_output_strings"][f"p{comparison['ordinal']}:stdout"].encode()
        native = {"version": "genomic_overlap_native_pair_receipt_v1", "comparison_key": comparison["comparison_key"],
            "identity": None, "derivation": "supplied_native_output", "outcome": "unknown", "software": None,
            "realized_argv": [], "environment": {}, "returncode": None, "started_at": None, "finished_at": None,
            "writer_closed": None, "capture_extent": "complete", "native_result_extent": "complete",
            "completeness_basis": "supplied_full_output_declaration", "completeness_source_refs": ["fixture:425"],
            "issues": [], "stdout": {"artifact_ref": "fixture:" + comparison["comparison_key"],
                "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw), "format": "bedtools_intersect_wo_bed4_v1"},
            "stderr": None}
        for side in ("a", "b"):
            key = comparison[side + "_set_key"]
            native[side] = {"set_key": key, "original_file": index[key]["source_file"], "canonical_file": None}
        native_pairs.append(parse_bedtools_intersect_wo(raw, pair=comparison, sets=index, native=native))
    references = extract_overlap_reference_metadata(specifications=request["region_sets"], sets=index,
                                                    comparisons=request["comparisons"])
    sheet = build_genomic_overlap_sheet(request=request, sets=sets, native_pairs=native_pairs, reference_relations=references)
    previous = json.loads((ROOT / "verification/tool_graders_genomic_overlap_contract_2026-10-27_418/WORKED_EXAMPLE.json").read_text())
    parameters = previous["components"]["parameters"]
    components = calculate_genomic_overlap_components(sheet, parameters=parameters)
    return {"evidence_label": "hand_worked_synthetic_supplied_data", "native_execution_claim": False,
            "sheet": sheet, "components": components}
