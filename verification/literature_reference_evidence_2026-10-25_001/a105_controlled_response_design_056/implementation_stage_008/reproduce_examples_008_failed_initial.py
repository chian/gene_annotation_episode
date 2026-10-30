"""Invented fixture bytes through pinned reader, then separate frozen calculator."""
from pathlib import Path
from copy import deepcopy
import errno
import hashlib
import inspect
import json
import runpy
import sys

HERE = Path(__file__).resolve().parent
PIN = HERE / "execution_pin_008"
sys.path.insert(0, str(PIN))
fixtures = runpy.run_path(str(PIN / "tests/test_literature_controlled_response_inputs.py"))
reader = fixtures["reader"]
populate = fixtures["populate_controlled_response"]


def main():
    cases = {}
    for name in ("ordinary", "shared_control", "unavailable_defined_unit", "exact_alias_conflict", "invalid_full_source_covariance"):
        f = fixtures["defined_unit_fixture"]() if name == "unavailable_defined_unit" else fixtures["Fixture"](shared=name in ("shared_control", "exact_alias_conflict"))
        callback = f.source
        if name == "unavailable_defined_unit":
            missing = fixtures["identity"]("source", "invented_missing_defined_unit_witness")
            f.args["arms"]["protein_condition1"]["measurement"]["unit"]["witness"] = {
                "source_ref": missing, "representation": "original", "start": 0, "end": 4, "quote": "U/mg"}
            def callback(ref, rep):
                if ref == missing:
                    raise FileNotFoundError(errno.ENOENT, "invented missing unit")
                return f.source(ref, rep)
        elif name == "exact_alias_conflict":
            first, second = "0.10000000000000000001", "0.10000000000000000002"
            line = f.args["arms"]["empty_condition1"]["measurement"]["literal"]["candidates"][0]["witness"]["quote"]
            f.replace_line(line, line.replace(", 2 ", ", " + first + " "))
            fixtures["set_measurement"](f, "empty_condition0", "A second rendering of actual E1: " + second + " nmol/min/mg.", second)
        elif name == "invalid_full_source_covariance":
            f.doc["matrix"][0][0] = -1
            f.covariance()
        extraction = reader.read_controlled_response_inputs(f.args, read_source=callback)
        assert reader.validate_controlled_response_extraction(f.args, extraction) == extraction
        sheet = populate(extraction["calculation_inputs"])
        cases[name] = {"synthetic_only": True,
            "actual_fixture_sources": {ref:{"utf8": value.decode(), "sha256": hashlib.sha256(value).hexdigest()} for ref,value in f.data.items()},
            "selection": deepcopy(f.args), "extraction": extraction, "separate_calculator_sheet": sheet}
    source = (PIN / "gene_annotation_episode/literature_controlled_response_inputs.py").read_bytes()
    ordinary = cases["ordinary"]["extraction"]
    proof = {"reader_source_sha256": hashlib.sha256(source).hexdigest(),
        "four_function_signatures": {name:str(inspect.signature(getattr(reader, name))) for name in [
            "controlled_response_arguments_schema", "validate_controlled_response_selection", "read_controlled_response_inputs", "validate_controlled_response_extraction"]},
        "selection_schema_exact007": reader.controlled_response_arguments_schema() == json.loads((fixtures["PIN"] / "SELECTION_SCHEMA_007.json").read_text()),
        "result_root_fields": list(ordinary), "result_contract": reader.VERSION,
        "closed_record_fields": {k:list(v) for k,v in reader._RESULT_FIELDS.items()},
        "reader_does_not_import_populate": "populate_controlled_response" not in vars(reader),
        "saved_validation_callback_parameter": False,
        "reader_import_path": reader.__file__,
        "interpretation": "Saved consistency is conditional on original runtime authorization and request/source/operation/outcome custody; it does not independently authenticate saved quotes/hashes."}
    for filename, value in [("SYNTHETIC_EXAMPLES_008.json", cases), ("API_PROOF_008.json", proof)]:
        with (HERE / filename).open("x") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
    rows = []
    for name, value in cases.items():
        cells = value["separate_calculator_sheet"]["cells"]
        rows.append({"case": name, "e_canonical": cells["controlled_response_difference"]["value"],
            "V_canonical_squared": cells["contrast_variance"]["value"],
            "local_d1": cells["condition1_controlled_response"]["value"],
            "local_d0": cells["condition0_controlled_response"]["value"],
            "effective_model": value["extraction"]["effective_model"],
            "diagnostic_codes": sorted({d["code"] for d in value["extraction"]["diagnostics"]})})
    with (HERE / "NUMERICAL_TABLE_008.json").open("x") as stream:
        json.dump(rows, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"synthetic_cases": len(cases), "schema_exact007": proof["selection_schema_exact007"], "reader_source_sha256": proof["reader_source_sha256"]}))


if __name__ == "__main__":
    main()
