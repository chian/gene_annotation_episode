"""Static literal/ref-closure evidence only; never import production modules."""
from copy import deepcopy
from pathlib import Path
import ast
import hashlib
import json
import sys

PACKET = Path(sys.argv[1]).resolve()
REPO = PACKET.parents[1]
OUT = Path.cwd()


def pin(path):
    content = path.read_bytes()
    return {"path": str(path), "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content)}


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def references(value):
    if isinstance(value, dict):
        if "$ref" in value:
            assert value["$ref"].startswith("#/$defs/")
            yield value["$ref"].rsplit("/", 1)[1]
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


paths = [REPO / "gene_annotation_episode" / name for name in (
    "chromatin_interaction_contracts.py", "chromatin_interaction_return_views.py",
    "communication.py", "chromatin_interaction_returns.py", "execution_contracts.py")]
before = [pin(path) for path in paths]
module = ast.parse(paths[0].read_bytes())
literal = next(node.value.args[0] for node in module.body
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name)
        and t.id == "_DEFINITIONS" for t in node.targets))
definitions = json.loads(ast.literal_eval(literal))
sources = {
    "chromatin_interaction_projection": "RequestedProjection",
    "chromatin_interaction_saved_sheets": "SavedSheetBundle",
    "chromatin_interaction_failures": "Failure",
}
result = {}
for source, kind in sources.items():
    reachable, pending = set(), [kind]
    while pending:
        current = pending.pop()
        if current not in reachable:
            reachable.add(current)
            pending.extend(references(definitions[current]))
    selected = {name: deepcopy(definitions[name]) for name in sorted(reachable)}
    edges = {name: sorted(set(references(definitions[name]))) for name in sorted(reachable)}
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$defs": selected,
              "type": "array", "items": {"$ref": "#/$defs/" + kind}, "x-source": source}
    if source == "chromatin_interaction_saved_sheets":
        identity = selected["NativeFileIdentity"]
        identity["properties"]["artifact_ref"].update(
            format="reference", **{"x-reference-namespace": "artifact"})
        sheet_identity = deepcopy(identity)
        sheet_identity["properties"]["format"] = {"const": "chromatin_interaction_sheet_v1"}
        selected["ChromatinSavedSheetIdentity"] = sheet_identity
        selected[kind]["properties"]["sheet"] = {"$ref": "#/$defs/ChromatinSavedSheetIdentity"}
        identity["properties"]["format"] = {"enum": ["chromatin_contact_tables_v1:" + role
            for role in ("bins", "contacts", "weights", "cell_states", "dense_values")]}
    schema["$id"] = "urn:gene-annotation:chromatin:return:" + hashlib.sha256(
        canonical(schema).encode("utf-8")).hexdigest()
    write(source + ".static_schema.json", schema)
    result[source] = {"record": kind, "reachable_definitions": sorted(reachable),
        "source_edges": edges, "exported_definitions": sorted(selected),
        "mechanically_derived_id": schema["$id"],
        "canonical_complete_schema_sha256": hashlib.sha256(canonical(schema).encode()).hexdigest(),
        "affected_by_proposed_definition_changes": sorted(reachable & {
            "NativeMetadata", "PopulationReadEvidence", "Locator", "Failure", "SoftwareBinding"})}
after = [pin(path) for path in paths]
assert before == after
write("SCHEMA_REACHABILITY.json", {"evidence": "static_literal_and_source_algorithm_only",
    "production_imported": False, "production_schema_callable_executed": False,
    "legacy_runtime_acceptance_failure_reproduced": False,
    "source_pins_before": before, "source_pins_after": after,
    "source_pins_unchanged": before == after, "sources": result})
print(json.dumps(result, indent=2))
