"""Read-only static packet check: no application imports, DB or execution."""
from pathlib import Path
import ast
import copy
import hashlib
import json
import tomllib
from jsonschema import Draft202012Validator

PACKET = Path(__file__).resolve().parent


def read(name):
    return json.loads((PACKET / name).read_bytes())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differences(before, after, path=""):
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(set(before) | set(after)):
            pointer = path + "/" + key
            if key not in before:
                result.append({"path": pointer, "kind": "added", "proposed": after[key]})
            elif key not in after:
                result.append({"path": pointer, "kind": "removed", "original": before[key]})
            else:
                result += differences(before[key], after[key], pointer)
        return result
    return [] if before == after else [{"path": path, "kind": "replaced", "original": before, "proposed": after}]


def constant(path, name):
    definitions = {target.id: item.value for item in ast.parse(path.read_bytes()).body
                   if isinstance(item, ast.Assign) for target in item.targets
                   if isinstance(target, ast.Name)}

    class Expand(ast.NodeTransformer):
        def visit_Name(self, node):
            return self.visit(copy.deepcopy(definitions[node.id]))

    return ast.literal_eval(Expand().visit(copy.deepcopy(definitions[name])))


def main():
    inputs = read("SOURCE_INPUTS008.json")
    source_root = Path(inputs["root"])
    source_files = sorted(p for package in ["gene_annotation_episode", "method_loop"]
                          for p in (source_root / package).rglob("*.py"))
    current = [{"path": str(p.relative_to(source_root)), "sha256": digest(p),
                "bytes": p.stat().st_size} for p in source_files]
    assert current == inputs["files"] and len(current) == 138
    pin = hashlib.sha256()
    for item in current:
        pin.update(item["path"].encode() + b"\0")
        pin.update(bytes.fromhex(item["sha256"]))
    assert pin.hexdigest() == inputs["runtime_pin"] == "6701ad996646c75e3d64d564cf6d79404e0d03a95a0bba463f145359bb254b30"
    old_root = Path("/home/chia/gene_annotation_episode_runs/configured_resource_investigation_001")
    for name in ["parameters.json", "config.toml", "focus.txt", "C_REQUEST001.json"]:
        assert (PACKET / "authority" / name).read_bytes() == (old_root / "caller-inputs" / name).read_bytes()
    before = read("authority/parameters.json")
    blueprint = read("PARAMETER_BLUEPRINT001.json")
    after = blueprint["template"]
    deltas = read("INPUT_DELTAS001.json")
    assert differences(before, after) == deltas["parameter_delta_including_actual_output_only_placeholders"]
    c_before, c_after = read("authority/C_REQUEST001.json"), read("C_REQUEST_PROPOSED001.json")
    assert differences(c_before, c_after) == deltas["C_request_delta"]
    assert len(deltas["C_request_delta"]) == 1 and deltas["C_request_delta"][0]["path"] == "/destination_workspace"
    assert len(c_after["initial_known_record_refs"]) == 198
    assert hashlib.sha256(canonical(c_after["initial_known_record_refs"])).hexdigest() == deltas["original198refs_canonical_sha256"]
    config_before = tomllib.loads((PACKET / "authority/config.toml").read_text())
    config_after = tomllib.loads((PACKET / "CONFIG_PROPOSED001.toml").read_text())
    assert differences(config_before, config_after) == deltas["config_parsed_delta"]
    assert len(deltas["config_parsed_delta"]) == 5
    normalized = copy.deepcopy(config_after)
    normalized["local_jobs"]["wall_seconds"] = None
    assert normalized == read("CONFIG_NORMALIZED_PROPOSED001.json")
    policies = [copy.deepcopy(value["policy"]) for value in [before, after]]
    for policy in policies:
        del policy["operational"]["registry_ref"]
        del policy["scientific_progress"]["initial_known_record_refs"]
    assert canonical(policies[0]) == canonical(policies[1])
    assert hashlib.sha256(canonical(policies[1])).hexdigest() == deltas["unchanged_policy_remainder_sha256"]
    assert after["services"]["version"] == constant(source_root / "gene_annotation_episode/api_planning_case_policy.py", "DIRECT_VERSION")
    assert after["services"]["ordinary_hmmer_timing"] == constant(source_root / "gene_annotation_episode/direct_hmmer_timing.py", "DIRECT_MODE")
    schema = read("PARAMETERS_PROFILE_SCHEMA001.json")
    Draft202012Validator.check_schema(schema)
    errors = sorted("/" + "/".join(map(str, error.absolute_path))
                    for error in Draft202012Validator(schema).iter_errors(after))
    assert errors == ["/policy/operational/registry_ref", "/policy/scientific_progress/initial_known_record_refs"]
    destination = Path(read("SCOPE001.json")["proposed_destination"])
    assert not destination.exists()
    assert not Path(after["services"]["api_timing"]["history_path"]).exists()
    assert not Path(after["services"]["api_timing"]["ledger_path"]).exists()
    library = Path(after["services"]["source_directory"])
    assert digest(library / "index.json") == deltas["library"]["index_sha256"]
    assert {item["slot"]: item["count"] for item in json.loads((library / "index.json").read_bytes())["slots"]} == {"annotation_distinction": 0, "thought_pattern": 19}
    print(json.dumps({"version": "configured_direct_timing_final_plan_check_v1", "status": "passed_static_only",
                      "runtime_count": len(current), "runtime_pin": pin.hexdigest(), "authority_copies_match": True,
                      "exact_C_config_parameter_deltas": True, "unchanged_policy_remainder": True,
                      "blueprint_schema_errors": errors, "destination_absent": True,
                      "source_preparation_launch_database_model_service_native_calls": 0,
                      "ready_to_launch": False}, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
