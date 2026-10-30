"""Save actual pure reader results from newly owned synthetic fixtures only."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from test_literature_binding_interaction_inputs import fixture, run
from gene_annotation_episode.literature_binding_interaction_calculations import populate_binding_interaction
from gene_annotation_episode.literature_binding_interaction_inputs import ROLES, binding_interaction_arguments_schema


OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]


def write(name, value):
    with (OUT / name).open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def main():
    protected = [ROOT / "gene_annotation_episode" / name for name in (
        "literature_binding_visual_inputs.py", "literature_binding_reader.py",
        "literature_binding_interaction_calculations.py", "literature_experimental_contracts.py",
        "literature_binding_interaction_inputs.py")]
    before = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    examples = []
    for case in ("complete", "partial_uncertainty", "partial_ci", "unknown_context", "ambiguous_rt", "unknown_unit", "unknown_common_kind"):
        args, sources, _, enum, literal, _ = fixture(extra="reported SD; reported CI; lower 4.1")
        if case == "partial_uncertainty":
            args["roles"][ROLES[0]]["uncertainty"] = None
            args["roles"][ROLES[1]]["uncertainty"]["statistic"] = enum("sd", "reported SD")
        elif case == "partial_ci":
            selected = args["roles"][ROLES[0]]["uncertainty"]
            selected["statistic"] = enum("confidence_interval", "reported CI")
            selected["interval"] = {"lower": literal("4.1"), "upper": None,
                "unit_relationship": enum("same_as_parameter", "reported CI"), "unit": None}
        elif case == "unknown_context":
            for role in ROLES[:2]:
                args["roles"][role]["definitions"]["state"] = {
                    "status": "unknown", "label": None, "witnesses": [], "canonical_witness": None}
        elif case == "ambiguous_rt":
            expression = args["roles"][ROLES[1]]["measurement"]["expression"]
            expression["status"] = "ambiguous"
            expression["candidates"].append({**deepcopy(expression["candidates"][0]), "quote": "46"})
        elif case == "unknown_unit":
            args["roles"][ROLES[0]]["measurement"]["unit"] = None
        elif case == "unknown_common_kind":
            args["parameter_kind"] = {"value": "unknown", "witnesses": []}
        result = run(args, sources)
        sheet = populate_binding_interaction(result["calculation_inputs"]) if result["calculation_inputs"] is not None else None
        write("EXAMPLE_003_" + case + ".json", {"synthetic_only": True, "reader_result": result,
            "pure_calculator_demonstration": sheet, "episode_or_live_model_execution": False})
        examples.append({"case": case, "calculation_input_status": result["calculation_input_status"],
            "roles": {role: {"measurement_status": row["measurement"]["parse_status"],
                "native": row["measurement"]["native_measurement"],
                "canonical": row["measurement"]["canonical_measurement"],
                "candidate_native": [candidate["native"] for candidate in row["measurement"]["candidate_measurements"]],
                "state_status": row["definitions"]["state"]["status"] if row["definitions"] else None,
                "uncertainty": row["uncertainty"]["canonical"]} for role, row in result["roles"].items()},
            "derived": {name: sheet["cells"][name] for name in (
                "reference_subject_ratio", "test_subject_ratio", "interaction_ratio", "log_interaction",
                "signed_profile_log_ratio")} if sheet else None})
    write("INPUT_SCHEMA_003.json", binding_interaction_arguments_schema())
    write("EXAMPLE_PROJECTIONS_003.json", examples)
    after = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
    assert before == after
    write("EXAMPLE_RECEIPT_003.json", {"synthetic_only": True, "actual_reader_calls": len(examples),
        "actual_pure_calculator_calls": sum(row["derived"] is not None for row in examples),
        "protected_code_hashes_unchanged": after, "source_paper_or_episode_or_model_execution": False,
        "controller_observations_created": 0, "annotation_credit_computed": False})
    print(json.dumps({"synthetic_examples": len(examples), "pure_calculator_calls": 6, "protected_code_unchanged": True}))


if __name__ == "__main__":
    main()
