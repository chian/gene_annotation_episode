"""Independent engineering review of an already reviewed case's schema delta."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent
PACKET = HERE.parent / "a105_summary_precision_components_248"
proposal_path = PACKET / "UNRESOLVED_KIND_SCHEMA_PROPOSAL_004.json"
proposal = json.loads(proposal_path.read_text())
expected = {
    "CALCULATION_INPUTS_SCHEMA_002.json": ["/properties/source_parameter_reason/anyOf/0/enum/-"],
    "EXTRACTION_SCHEMA_002.json": ["/properties/calculation_inputs/properties/source_parameter_reason/anyOf/0/enum/-"],
    "SHEET_SCHEMA_003.json": [
        "/properties/inputs/properties/source_parameter_reason/anyOf/0/enum/-",
        "/$defs/Cell/properties/unavailable_reason/anyOf/0/enum/-",
    ],
}
reasons = ["source_parameter_kind_unknown", "source_parameter_kind_conflicting"]
assert set(proposal["exact_delta"]) == set(expected)
reviewed = []
for original_name, paths in expected.items():
    change = proposal["exact_delta"][original_name]
    original = json.loads((PACKET / original_name).read_text())
    revised = json.loads((PACKET / change["revised_file"]).read_text())
    wanted_patch = [{"op": "add", "path": path, "value": reason}
                    for path in paths for reason in reasons]
    assert change["rfc6902_patch"] == wanted_patch
    applied = deepcopy(original)
    for patch in wanted_patch:
        node = applied
        tokens = patch["path"].split("/")[1:]
        for token in tokens[:-1]:
            node = node[int(token)] if isinstance(node, list) else node[token]
        assert tokens[-1] == "-" and isinstance(node, list)
        assert patch["value"] not in node
        node.append(patch["value"])
    assert applied == revised, "No changes beyond the eight reviewed enum appends"
    Draft202012Validator.check_schema(revised)
    for reason in reasons:
        # Check the exact changed leaf; unrelated invalid reasons remain invalid.
        if original_name == "EXTRACTION_SCHEMA_002.json":
            schema = revised["properties"]["calculation_inputs"]
        elif original_name == "SHEET_SCHEMA_003.json":
            schema = revised["properties"]["inputs"]
        else:
            schema = revised
        leaf = schema["properties"]["source_parameter_reason"]
        assert Draft202012Validator(leaf).is_valid(reason)
        assert not Draft202012Validator(leaf).is_valid("invented_source_reason")
    reviewed.append({"original": original_name, "revised": change["revised_file"],
                     "sha256": sha256((PACKET / change["revised_file"]).read_bytes()).hexdigest(),
                     "enum_appends": len(wanted_patch)})
result = {"status": "pass", "proposal_sha256": sha256(proposal_path.read_bytes()).hexdigest(),
          "reviewed": reviewed, "total_enum_appends": 8,
          "source_selection_or_existing_reader_changes": False,
          "production_implementation_tested": False,
          "semantics": "Preserve authenticated extraction/count partials; unsupported dimensions stay unavailable with exact kind reasons."}
(HERE / "ROOT_UNRESOLVED_KIND_DELTA_CHECK_005.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
