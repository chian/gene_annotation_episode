"""Authenticate one retained paired BLAST HSP for the existing column reader.

The caller first checks explicit receipt and scope. This host-only adapter uses
the original source-associated collection and frozen publication rows. It does
not publish, run a grading worker/calculator, launch BLAST or acquire anything.
"""
from __future__ import annotations

from copy import deepcopy
import json

from .alignment_site_native import immutable_record
from .blast_pairwise_result_views import NATIVE_BLAST_METRICS, projected_measurements
from .blast_pairwise_results import _validate
from .blast_search import PROGRAM_UNITS
from .domain import ContractError
from .episode_return_records import EpisodeReturnRecords
from .materials import artifact_path
from .native_blast_contracts import native_blast_digest, validate_native_blast_requested_job
from .native_blast_result_publication import (_read_json, _captured_paths, _binding_snapshots,
    _validate_sequence, _reference, _record)
from .native_blast_result_worker import (_input_records, _invocation, _hsp_values, record_key,
    validate_native_blast_correspondence_collections)
from .tool_grading_artifacts import MEDIA_TYPE, SCHEMA


_equal = EpisodeReturnRecords._equal
_STABLE_FIELDS = {"schema", "bundle_sha256", "sheet_artifact_ref", "sheet_schema",
    "scores_artifact_ref", "scores_schema", "complete_rows_artifact_ref",
    "sequence_artifact_refs", "captured_artifacts"}


def _require(condition, code):
    if not condition:
        raise ContractError("native_blast_hsp_" + code)


def _one(rows, code):
    values = list(rows)
    _require(len(values) == 1, code)
    return values[0]


def _source_grading(store, source, bundle):
    candidates = []
    for reference in source.get("auxiliary_artifact_refs", []):
        if store.get(reference).get("media_type") != MEDIA_TYPE:
            continue
        envelope = _read_json(store, reference)
        grading = envelope.get("grading", {})
        if grading.get("schema") not in {"native_blast_retained_grading_v1", "native_blast_retained_grading_v2"}:
            continue
        _require(set(envelope) == {"schema", "provider", "native_artifact_ref", "grading"}
            and envelope["schema"] == SCHEMA and envelope["provider"] == source["provider"]
            and envelope["native_artifact_ref"] == source["artifact_ref"], "grading_source_conflict")
        _require(set(grading) == _STABLE_FIELDS
            and grading["bundle_sha256"] == native_blast_digest(bundle), "source_grading_conflict")
        candidates.append(grading)
    return _one(candidates, "source_grading_required")


def _selected_native(store, bundle, grading, sheet, scores, row, marker):
    collection = sheet["collection"]
    _require(collection["schema"] == "blast_report_collection_v1", "collection_required")
    search = _one((item for item in collection["searches"]
        if _equal(item["search_key"], marker["search_key"])), "original_search_conflict")
    saved_sheet = _one((item for item in sheet["searches"]
        if _equal(item["search_key"], marker["search_key"])), "original_sheet_conflict")
    saved_scores = _one((item for item in scores["searches"]
        if _equal(item["search_key"], marker["search_key"])), "original_scores_conflict")
    _require(saved_sheet["failure"] is None and saved_scores["failure"] is None
        and saved_sheet["sheet"]["schema"] == "blast_pairwise_result_sheet_v1"
        and saved_scores["scores"]["schema"] == "blast_pairwise_result_components_v1"
        and _equal(saved_sheet["sheet"]["search"], search), "search_grading_conflict")
    bindings = saved_sheet["sheet"]["operand_bindings"]
    normalized = _validate(search, bindings)  # Validation of saved facts; no calculation.
    context = search["program_context"]
    _require(context["execution_program"] == context["geometry_program"] == bundle["program"]
        and context["scientific_mode"] == "pairwise", "program_conflict")
    hit, mapping = _one(((hit, mapping) for hit, mapping in zip(normalized["hits"], search["row_map"])
        if mapping["hit_index"] == marker["hit_ordinal"]), "original_hit_conflict")
    index, native = _one(((index, hsp) for index, (hsp, ordinal) in enumerate(
        zip(hit["hsps"], mapping["hsp_ordinals"])) if ordinal == marker["hsp_ordinal"]),
        "original_hsp_conflict")
    component = saved_scores["scores"]["components"]["hsps"][index]
    if grading["schema"] == "native_blast_retained_grading_v2":
        search_index = scores["searches"].index(saved_scores)
        pointer = "/searches/" + str(search_index) + "/scores/components"
        instance = _one((item for item in scores["correspondence"]["instances"]
            if item["legacy_pointer"] == pointer and item["axis_basis"] == "qualified"), "common_components_required")
        expected_values = _hsp_values(component["components"], instance["components"]["rows"][index])
    else:
        expected_values = _hsp_values(component["components"], archived_values=row["values"])
    _require(component["hsp_index"] == index and _equal(component["native"], native)
        and _equal(row["values"], expected_values), "frozen_measurement_conflict")

    artifact_key = marker["search_key"]["artifact_key"]
    artifact = _one((item for item in grading["captured_artifacts"]
        if item["kind"] == "output" and item["relative_path"] == artifact_key
        and item["role"] in {"primary_report", "tabular_report"}), "captured_report_required")
    declared = _one((item for item in bundle["requested_job"]["native_blast"]["outputs"]
        if item["relative_path"] == artifact_key and item["role"] == artifact["role"]), "report_binding_conflict")
    actual = store.get(artifact["artifact_ref"])
    expected = {"artifact_key": artifact_key, **{key: declared[key]
        for key in ("role", "format", "fields", "delimiter")},
        "sha256": actual["sha256"], "size_bytes": actual["size"]}
    descriptor = _one((item for item in collection["artifacts"]
        if item["artifact_key"] == artifact_key), "report_descriptor_conflict")
    _require(_equal(descriptor, expected) and artifact["format"] == declared["format"]
        and normalized["native"]["sha256"] == actual["sha256"]
        and marker["search_key"]["member_ordinal"] is None, "report_descriptor_conflict")
    raw = store.get_artifact(artifact["artifact_ref"])
    if declared["format"] == "json15":
        _require(normalized["format"] == "json2" and
            _equal(json.loads(raw), normalized["native"]["document"]), "original_report_conflict")
        format_name = "native_blast_json_hsp"
    else:
        _require(declared["format"] in {"tabular6", "tabular7"}
            and normalized["format"] == "tabular", "retained_format_unsupported")
        _tabular_native(raw, declared, search, marker, native)
        format_name = "native_blast_tabular_hsp"
    return native, search, bindings, artifact, format_name


def _tabular_native(raw, declared, search, marker, native):
    """Check the selected frozen normalized fields against their original lexemes.

    Reuse the producer's field conversion rules; no score is calculated and no
    report collection is reconstructed. Native row ordinals include bad siblings.
    """
    from . import blast_grading_inputs as reader
    from .blast_report_collection import _sections
    text = raw.decode("utf-8")
    _require(search["native"]["report"]["text"] == text, "original_report_conflict")
    sections = _sections(text, declared)
    _, lines = _one(((index, lines) for index, lines in enumerate(sections)
        if marker["search_key"]["search_pointer"] == "/sections/" + str(index)), "tabular_search_conflict")
    _require(marker["search_key"]["report_index"] == 0
        and search["native"]["search"]["text"] == "".join(line for _, line in lines), "tabular_search_conflict")
    fields = reader._fields(declared["fields"])
    _require(search["native"]["search"]["fields"] == fields, "tabular_fields_conflict")
    data_lines = [(number, line.rstrip("\r\n")) for number, line in lines
        if line.strip() and not line.startswith("#")]
    number, line = data_lines[marker["hsp_ordinal"]]
    values = line.split(declared["delimiter"] or "\t")
    _require(len(values) == len(fields), "tabular_row_conflict")
    fields = dict(zip(fields, values))
    original = search["native"]["search"]["rows"][marker["hsp_ordinal"]]
    _require(_equal(original, {"line": number, "values": values, "fields": fields})
        and search["native"]["line_numbers"][marker["hsp_ordinal"]] == number, "tabular_row_conflict")
    numbers = {key: reader._tab_number(value, key) for key, value in fields.items()
        if key in reader._TAB_INTS | reader._TAB_NUMBERS}
    expected = {target: numbers[key] if key in numbers else fields[key]
        for key, target in reader._TAB_HSP.items() if key in fields
        and (key not in numbers or numbers[key] is not None)}
    if fields.get("frames"):
        parts = fields["frames"].split("/")
        _require(len(parts) == 2, "tabular_frames_conflict")
        for key, value in zip(("query_frame", "hit_frame"), parts):
            value = reader._tab_number(value, "qframe")
            _require(key not in expected or expected[key] == value, "tabular_frames_conflict")
            if value is not None:
                expected[key] = value
    if fields.get("sstrand") in ("plus", "minus", "Plus", "Minus"):
        expected["hit_strand"] = fields["sstrand"].title()
    _require(_equal(native, reader._hsp(expected, [])), "tabular_hsp_conflict")


def native_blast_pairwise_hsp(store, observation) -> dict:
    """Return one authenticated original HSP; receipt/scope admission stays caller-owned."""
    try:
        return _native_blast_pairwise_hsp(store, observation)
    except ContractError:
        raise
    except (ValueError, KeyError, IndexError, TypeError, OSError, UnicodeError) as error:
        raise ContractError("native_blast_hsp_retained_record_invalid") from error


def _native_blast_pairwise_hsp(store, observation):
    _require(observation.get("record_type") == "observation" and observation.get("origin") == "tool"
        and observation.get("kind") == "comparison" and "native_blast" not in observation,
        "pairwise_observation_required")
    immutable_record(observation)
    _require(_equal(observation, store.get(observation["id"])), "observation_record_conflict")
    marker = observation["native_blast_pairwise"]
    _require(set(marker) == {"version", "program", "record_key", "search_key", "hit_ordinal",
        "hsp_ordinal", "bundle_artifact_ref"} and marker["version"] == "native_blast_pairwise_observation_v1"
        and marker["program"] in PROGRAM_UNITS, "marker_conflict")
    source = store.get(observation["source_ref"])
    immutable_record(source)
    _require(source.get("record_type") == "source" and source.get("origin") == "tool"
        and source.get("provider") == "episode.execution_result"
        and source.get("version") == "native_blast_bundle_v1"
        and source["artifact_ref"] == marker["bundle_artifact_ref"], "source_required")
    bundle = _read_json(store, source["artifact_ref"])
    request = validate_native_blast_requested_job(bundle["requested_job"])
    _require(bundle["version"] == "native_blast_bundle_v1" and bundle["mode"] == "pairwise"
        and bundle["program"] == request["native_blast"]["program"] == marker["program"]
        and bundle["operand_bindings"] == request["native_blast"]["operand_bindings"]
        and bundle["identity"]["requested_job_sha256"] == native_blast_digest(request)
        and source["accession"] == "native_blast_" + native_blast_digest(bundle["identity"])
        and source["retrieved_at"] == bundle["finished_at"], "original_bundle_conflict")
    grading = _source_grading(store, source, bundle)
    paths, _ = _captured_paths(store, bundle, [{k: v for k, v in item.items() if k != "kind"}
        for item in grading["captured_artifacts"]])
    _require(all(item["artifact_ref"] in source["auxiliary_artifact_refs"] for item in paths)
        and _equal([{k: v for k, v in item.items() if k != "path"} for item in paths],
                   grading["captured_artifacts"]), "captured_artifact_conflict")
    # Unrelated unavailable outputs may survive in a partial source. Required
    # input/report custody is checked below against the actual captured files.
    sheet, scores = (_read_json(store, grading[key]) for key in ("sheet_artifact_ref", "scores_artifact_ref"))
    version = "v2" if grading["schema"] == "native_blast_retained_grading_v2" else "v1"
    _require(sheet["schema"] == grading["sheet_schema"] == "native_blast_sheet_collection_" + version
        and scores["schema"] == grading["scores_schema"] == "native_blast_scores_collection_" + version,
        "grading_collection_required")
    if version == "v2":
        validate_native_blast_correspondence_collections(sheet, scores)
    _require(marker["record_key"] == record_key(bundle, marker["search_key"], "pairwise_hsp",
        marker["hit_ordinal"], marker["hsp_ordinal"]), "complete_row_identity_conflict")
    with artifact_path(store, grading["complete_rows_artifact_ref"]).open(encoding="utf-8") as stream:
        row = _one((row for line in stream if (row := json.loads(line))["record_key"] == marker["record_key"]),
            "complete_row_required")
    scored = _one((item for item in scores["rows"]["pairwise_hsp"]
        if item["record_key"] == marker["record_key"]), "scored_row_required")
    _require(_equal(row, scored) and row["version"] == "native_blast_complete_row_v1"
        and row["family"] == "pairwise_hsp" and row["invalid"] is False
        and all(_equal(row[key], marker[key]) for key in ("search_key", "program", "hit_ordinal", "hsp_ordinal"))
        and row["coordinate_units"] == dict(zip(("query", "reference", "alignment"), PROGRAM_UNITS[bundle["program"]])),
        "complete_row_conflict")
    native, search, bindings, artifact, format_name = _selected_native(store, bundle, grading, sheet, scores, row, marker)
    diagnostics = []
    records = _input_records(bundle, paths, _binding_snapshots(store, bundle), diagnostics)
    _require(not diagnostics and _equal(records, sheet["publication_inputs"]["records"])
        and _equal(row["operands"], {role: {k: v for k, v in operand.items() if k != "sequence"}
            for role, operand in records.items()}), "original_operands_conflict")
    invocation, expected_bindings = _invocation(bundle, records)
    _require(_equal(invocation, sheet["collection"]["invocation"])
        and _equal(bindings, expected_bindings)
        and _equal(sheet["publication_inputs"]["captured_artifacts"], grading["captured_artifacts"]),
        "original_invocation_conflict")
    query = records["query"]["binding"]["subject_ref"]
    _require(observation["subject_refs"] == [query] and len(observation["source_subject_refs"]) == 1,
        "operand_identity_conflict")
    immutable_record(store.get(query))
    _validate_sequence(store, records["query"], query)
    reference_ref = _reference(store, records["reference"], grading, source["id"], None, False)
    reference = store.get(reference_ref)
    immutable_record(reference)
    _require(observation["source_subject_refs"] == [reference_ref], "reference_identity_conflict")
    for role, prefix in (("query", "query"), ("reference", "hit")):
        interval = [min(native[prefix + "_from"], native[prefix + "_to"]) - 1,
                    max(native[prefix + "_from"], native[prefix + "_to"])]
        _require(_equal(row["intervals"][role], interval), "operand_interval_conflict")
    values, _ = projected_measurements(row, NATIVE_BLAST_METRICS["pairwise_hsp"])
    payload = {"subject_refs": [query], "source_subject_refs": [reference_ref], "kind": "comparison",
        "source_ref": source["id"], "measurements": [{"name": item["name"], "value": {
            "type": "number", "value": item["value"], "unit_ref": None}} for item in values],
        "dependencies": list(dict.fromkeys([source["id"], query, reference_ref])), "anchor": None,
        "operand_intervals": [{"role": role, "subject_ref": ref, "start": row["intervals"][role][0],
            "end": row["intervals"][role][1], "unit": row["coordinate_units"][role],
            "model_unit": row["coordinate_units"]["alignment"]}
            for role, ref in (("query", query), ("reference", reference_ref))],
        "native_blast_pairwise": marker}
    _require(_record(store, "observation", payload, None, False) == observation["id"], "frozen_observation_conflict")
    return {"native_hsp": deepcopy(native), "source": source, "reference": reference,
        "source_descriptor": {"alignment_ref": observation["id"], "source_ref": source["id"],
            "native_artifact_ref": artifact["artifact_ref"], "provider": source["provider"], "format": format_name,
            "native_version": search["program_context"]["native_version"],
            "native_locator": {key: deepcopy(marker[key]) for key in ("search_key", "hit_ordinal", "hsp_ordinal")}},
        "program": bundle["program"], "query_length": records["query"]["length"],
        "reference_length": records["reference"]["length"]}


__all__ = ["native_blast_pairwise_hsp"]
