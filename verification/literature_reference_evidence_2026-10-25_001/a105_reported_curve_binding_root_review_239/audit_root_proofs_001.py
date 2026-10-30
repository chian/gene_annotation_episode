"""Independently inspect root-created controlled returns and cold-state evidence."""
from pathlib import Path
import hashlib
import json
import sqlite3
from xml.etree import ElementTree as ET

from jsonschema import Draft202012Validator

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
OWNER = OUT.parent / "a105_reported_curve_binding_231"


def load(path):
    return json.loads(path.read_text())


def state_hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob("*")) if p.is_file()}


def main():
    result = load(OUT / "ROOT_RESULT_001.json")
    assert result["exit_code"] == 0 and result["all_imports_inside_pin"]
    junit = ET.parse(OUT / "ROOT_JUNIT_001.xml").getroot()
    cases = [(c.get("classname"), c.get("name")) for c in junit.iter("testcase")]
    assert len(cases) == 32 and len(set(cases)) == 32
    assert not list(junit.iter("failure")) and not list(junit.iter("error"))
    manifest = load(OWNER / "PIN_003.json")
    current = {}
    for name in [*manifest["production_overlays"], "tests/test_literature_reported_curve_binding_231.py"]:
        observed = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        assert observed == manifest["hashes"][name], name
        current[name] = observed

    proofs = []
    combinations = set()
    for proof_path in sorted((OUT / "test_state_001").rglob("COLD_PROOF_231.json")):
        proof = load(proof_path)
        assert proof["first_readonly_composer"]
        assert proof["scientific_source_parser_fit_model_receive_attestation_blocked"]
        assert proof["changed_rows"] == 0 and proof["selected_population_operations"] == 1
        assert proof["actual_model_execution"] is False and proof["A105_adequacy_claim"] is False
        directory = proof_path.parent
        state = directory / "state"
        assert state_hashes(state) == proof["state_files"]
        form = load(directory / "ORIGINAL_FORM_231.json")
        schema = load(directory / "ORIGINAL_SCHEMA_231.json")
        sheet = load(directory / "ORIGINAL_SHEET_231.json")
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(form)
        rows = form["numbers"]
        assert len(rows) == (1 if proof["nested"] else 3)
        assert rows[0]["selector"] == {"scope": "point", "component": "cv", "concentration_cell": "Q196"}
        assert len(rows[0]["coordinate_context"]) == 1
        assert rows[0]["coordinate_context"][0]["exact_value"] == {"numerator": "10", "denominator": "1"}
        assert rows[0]["reporting_counts"]["selected_reporting_entries"] == 3
        for row in rows:
            assert row["scientific_scope"]["physical_preparation_count"] is None
            assert row["scientific_scope"]["published_estimate_covariance"] is None
            assert row["scientific_scope"]["endpoint_relationship"] == "conflicting"
            assert row["scientific_scope"]["concentration_basis"] == "fixed_reported_concentrations_when_fitted"
        if proof["nondetection"]:
            assert rows[0]["status"] == "unavailable" and rows[0]["value"] is None
        else:
            assert abs(rows[0]["value"] - 0.03488479236954927) < 1e-14
            if len(rows) == 3:
                assert rows[2]["value"] is None
                assert abs(rows[2]["conditional_value"] - 0.0033927323393825364) < 1e-14
        assert sheet["sheet"]["extraction"] == sheet["extraction"]
        # These are completed, checkpointed, closed test fixtures. Unlike the
        # live configured run, immutable mode is appropriate and avoids creating
        # SQLite WAL/SHM sidecars during an independent count-only audit.
        db = sqlite3.connect((state / "state.sqlite3").resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
        try:
            actions = db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0]
            observations = db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0]
            operations = db.execute("SELECT count(*) FROM literature_rate_observation_operations").fetchone()[0]
            assert actions == observations == (5 if proof["nested"] else 3)
            assert operations == 1 and db.total_changes == 0
        finally:
            db.close()
        assert state_hashes(state) == proof["state_files"]
        key = (proof["profile"], proof["alias"], proof["nondetection"], proof["nested"])
        assert key not in combinations
        combinations.add(key)
        proofs.append({"path": str(proof_path.relative_to(OUT)), "profile": proof["profile"],
                       "alias": proof["alias"], "nondetection": proof["nondetection"],
                       "nested": proof["nested"], "original_admitted_rows": len(rows),
                       "actions": actions, "observations": observations,
                       "state_files_unchanged": len(proof["state_files"])})
    assert len(proofs) == 9
    expected = {(p, alias, nd, False) for p in (None, "operation_contract_information_v1")
                for alias in (False, True) for nd in (False, True)} | {(None, True, False, True)}
    assert combinations == expected
    audit = {"status": "passed", "independent_test_identities": len(cases),
             "controlled_original_closed_proofs": proofs, "current_production_and_test_hashes": current,
             "traced_pinned_imports": len(result["traced_imports"]),
             "actual_model_execution": False, "new_assay_specific_graders": 0,
             "complete_scientific_A105_assessment": False, "goal_complete": False}
    with (OUT / "ROOT_CLOSED_PROOF_AUDIT_001.json").open("x") as handle:
        json.dump(audit, handle, indent=2)
        handle.write("\n")
    print(json.dumps({key: value for key, value in audit.items()
                      if key not in ("controlled_original_closed_proofs", "current_production_and_test_hashes")}))


if __name__ == "__main__":
    main()
