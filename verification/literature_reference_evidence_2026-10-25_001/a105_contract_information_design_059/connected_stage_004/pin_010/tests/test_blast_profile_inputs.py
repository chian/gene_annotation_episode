"""Explicitly synthetic profile contexts; these tests do not execute RPS."""
from copy import deepcopy
import hashlib
import io
import json
import zipfile

import pytest

from gene_annotation_episode.blast_profile_inputs import populate_blast_profile_sheet
from gene_annotation_episode.blast_report_collection import parse_blast_report_collection


def provenance(pointer="/models/0"):
    return {"source_ref": "synthetic:explicit-profile-catalog", "pointer": pointer}


def database(program="rpsblast"):
    return {"namespace": "synthetic_profile_database", "value": "synthetic_profiles",
            "version": "1", "release": "synthetic_release_1", "scope": "supplied_models",
            "preparation_type": "delta" if program == "deltablast" else "rps",
            "source": provenance("/database")}


def model_record(number=1, program="rpsblast"):
    return {"profile_key": f"profile_{number}", "database_identity": database(program),
            "model_identifier": {"namespace": "CDD", "value": f"cd{number:05d}", "version": "1"},
            "pssm_key": f"synthetic_pssm_{number}", "num_columns": 100,
            "master_sequence_ref": None, "specific_bits_threshold": 40,
            "reporting_bits_threshold": 35, "source": provenance(f"/models/{number - 1}"),
            "native_record": {"synthetic": True, "numColumns": 100,
                              "params": {"bitScoreThresh": 40, "bitScoreReportingThresh": 35},
                              "unrecognized_supplied_field": ["retained", None]}}


def synthetic_hsp(*, translated=False, reverse=False, start=1, positions=50, bits=42):
    width = 3 if translated else 1
    hsp = {"num": 1, "query_from": start, "query_to": start + width * positions - 1,
           "hit_from": 1, "hit_to": positions, "qseq": "A" * positions, "hseq": "A" * positions,
           "align_len": positions, "identity": positions, "positive": positions, "gaps": 0,
           "bit_score": bits, "score": 95, "evalue": 1.234567890123456e-25,
           "unknown_native_measurement": {"retained": [0, 0.125]}}
    if translated:
        hsp["query_frame"] = -1 if reverse else 1
    return hsp


def synthetic_hit(number=1, **hsp_args):
    return {"num": number, "len": 100,
            "description": [{"id": f"gnl|CDD|{1000 + number}", "accession": f"cd{number:05d}.1",
                             "title": "synthetic representative, never a function assignment", "taxid": 562}],
            "hsps": [synthetic_hsp(**hsp_args)]}


def make_inputs(program="rpsblast", *, hits=None, archive=False, reverse=False,
                selected=None, query_length=None, full_length=None, native_returncode=0,
                producer_complete=True, missing_hits=False, report_changes=None,
                unbound_operand=False):
    translated = program == "rpstblastn"
    full_length = full_length or (300 if translated else 100)
    query_length = query_length or full_length
    if hits is None:
        hits = [synthetic_hit(translated=translated, reverse=reverse, start=151 if reverse else 1)]
    native_search = {"query_id": "q", "query_title": "q", "query_len": query_length}
    if not missing_hits:
        native_search["hits"] = deepcopy(hits)
    report = {"program": program, "version": program.upper() + " 2.17.0+",
              "search_target": {"db": "synthetic_profiles"}, "params": {"query_gencode": 11},
              "results": {"search": native_search}}
    report.update(report_changes or {})
    raw = json.dumps({"BlastOutput2": [{"report": report}]}, allow_nan=False).encode()
    operand = {"role": "query", "artifact_key": "synthetic_query", "record_ordinal": 0,
               "native_id": "q", "native_title": "q", "subject_ref": "synthetic_query",
               "molecule": "dna" if translated else "protein", "length": full_length,
               "selected_interval": selected, "identity": None}
    inv = {"execution_program": program, "scientific_mode": "database", "resource_kind": "hpc",
           "query_kind": "sequence", "reference_kind": "sequence" if program == "deltablast" else "profile",
           "request": {"synthetic_context": True}, "effective_options": {},
           "operands": [] if unbound_operand else [operand],
           "completion": {"native_returncode": native_returncode, "producer_complete": producer_complete}}
    artifact = {"artifact_key": "synthetic_report", "role": "primary_report", "format": "json15",
                "fields": None, "delimiter": None}
    if archive:
        container = io.BytesIO()
        with zipfile.ZipFile(container, "w") as archive_file:
            archive_file.writestr("manifest.json", json.dumps({"BlastJSON": [{"File": "one.json"}, {"File": "two.json"}]}))
            archive_file.writestr("one.json", raw)
            archive_file.writestr("two.json", raw)
        raw = container.getvalue()
        artifact["format"] = "json2_archive"
    collection = parse_blast_report_collection({artifact["artifact_key"]: raw}, artifacts=[artifact], invocation=inv)
    search = collection["searches"][0]
    key = search["search_key"]
    member = search["normalized"]["native"].get("archive_member") or {}
    profile_records, profile_bindings, functions = [], [], []
    for hit, mapping in zip(search["normalized"]["hits"], search["row_map"]):
        if not hit["descriptions"]:
            continue
        # The fixture supplies a deliberate model association. Never derive a
        # scientific mapping from a title in production code.
        description_index = next((i for i, d in enumerate(hit["descriptions"]) if d.get("accession")), None)
        if description_index is None:
            continue
        description = hit["descriptions"][description_index]
        number = int(description["accession"][2:7])
        record = model_record(number, program)
        if record not in profile_records:
            profile_records.append(record)
        profile_bindings.append({"search_key": deepcopy(key), "hit_ordinal": hit["hit_index"],
            "description_ordinal": mapping["description_ordinals"][description_index],
            "profile_key": record["profile_key"],
            "native_description": {name: description.get(name) for name in ("id", "accession", "title", "taxid")},
            "provenance": provenance(f"/bindings/{hit['hit_index']}")})
        functions.append({"profile_key": record["profile_key"], "function": {"namespace": "EC", "value": "1.2.3.4"},
                          "evidence_refs": [provenance("/evidence/0")], "provenance": provenance("/functions/0")})
    return {"search": search,
        "report_source": {"artifact_key": key["artifact_key"], "artifact_ref": "synthetic:retained-artifact",
                          "member_ordinal": key["member_ordinal"], "member_sha256": member.get("sha256")},
        "search_binding": {"search_key": deepcopy(key), "stage": "domain_database", "biological_round": None,
                           "database_identity": database(program), "input_pssm_key": None,
                           "provenance": provenance("/selected_job/domain_search")},
        "query_binding": {"operand": deepcopy(operand), "axis_kind": "sequence", "full_length": full_length,
                          "coordinate_unit": "nt" if translated else "aa",
                          "sequence_sha256": hashlib.sha256(("A" * full_length).encode()).hexdigest(),
                          "pssm_key": None, "master_mapping_ref": None},
        "profile_records": profile_records, "profile_bindings": profile_bindings,
        "function_bindings": functions, "model_relations": [], "target_context": {"unused": True}}


def test_population_retains_native_numerical_cells_unknown_metadata_and_exact_keys():
    inputs = make_inputs()
    expected = deepcopy(inputs)
    sheet = populate_blast_profile_sheet(**inputs)
    assert set(sheet) == set(inputs) | {"schema"}
    assert sheet["schema"] == "blast_profile_search_sheet_v1"
    assert {key: sheet[key] for key in inputs} == expected
    inputs["search"]["native"]["search"]["hits"][0]["hsps"][0]["bit_score"] = -999
    inputs["profile_records"][0]["native_record"]["unrecognized_supplied_field"][0] = "changed"
    assert {key: sheet[key] for key in expected} == expected
    assert sheet["search"]["normalized"]["hits"][0]["hsps"][0]["bit_score"] == 42
    assert json.loads(json.dumps(sheet, allow_nan=False)) == sheet


@pytest.mark.parametrize("field,value,error", [
    ("num_columns", 0, "record_invalid"), ("num_columns", True, "record_invalid"),
    ("specific_bits_threshold", True, "threshold_invalid"),
    ("specific_bits_threshold", float("nan"), "finite_json_required"),
    ("specific_bits_threshold", 10**400, "threshold_invalid"),
    ("native_record", {"x": (1, 2)}, "finite_json_required"),
])
def test_invalid_model_input_is_not_silently_repaired(field, value, error):
    inputs = make_inputs()
    inputs["profile_records"][0][field] = value
    with pytest.raises(ValueError, match=error):
        populate_blast_profile_sheet(**inputs)


def test_exact_typed_keys_and_duplicate_binding_rejected_but_plausible_alternatives_survive():
    inputs = make_inputs()
    inputs["profile_bindings"][0]["invented_identifier_mapping"] = "not a contract field"
    with pytest.raises(ValueError, match="binding_fields_invalid"):
        populate_blast_profile_sheet(**inputs)
    inputs = make_inputs()
    repeated = deepcopy(inputs["profile_bindings"][0])
    repeated["search_key"] = dict(reversed(list(repeated["search_key"].items())))
    inputs["profile_bindings"].append(repeated)
    with pytest.raises(ValueError, match="binding_duplicate"):
        populate_blast_profile_sheet(**inputs)
    repeated["profile_key"] = "different_plausible_model"
    assert len(populate_blast_profile_sheet(**inputs)["profile_bindings"]) == 2


def test_null_inputs_and_actual_zero_threshold_remain_different():
    inputs = make_inputs()
    inputs["query_binding"] = None
    inputs["search_binding"]["stage"] = None
    inputs["profile_records"][0].update(num_columns=None, specific_bits_threshold=None, reporting_bits_threshold=0)
    sheet = populate_blast_profile_sheet(**inputs)
    assert sheet["query_binding"] is None
    assert sheet["profile_records"][0]["specific_bits_threshold"] is None
    assert sheet["profile_records"][0]["reporting_bits_threshold"] == 0


@pytest.mark.parametrize("pointer", ["relative/pointer", "/bad~escape"])
def test_provenance_uses_rfc6901_pointer(pointer):
    inputs = make_inputs()
    inputs["profile_records"][0]["source"]["pointer"] = pointer
    with pytest.raises(ValueError, match="provenance_invalid"):
        populate_blast_profile_sheet(**inputs)


def test_duplicate_profile_record_key_rejected():
    inputs = make_inputs()
    inputs["profile_records"].append(deepcopy(inputs["profile_records"][0]))
    with pytest.raises(ValueError, match="record_key_invalid_or_duplicate"):
        populate_blast_profile_sheet(**inputs)
