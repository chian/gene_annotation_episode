"""Write labeled supplied-byte/parser examples, never a native-service claim."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_bvbrc_phylogeny_bundle_adapter import consume, numerical_fields, codon_hand_fixture, codon_fields
from test_bvbrc_phylogeny_bundle_resolution import fixture, slot
from test_bvbrc_phylogeny_returns import projection, content
from gene_annotation_episode.bvbrc_phylogeny_bundle_contracts import requested_form_schema
from gene_annotation_episode.bvbrc_phylogeny_returns import FACT_SOURCES, project_phylogeny_facts


def example(f, fields, provider):
    result = consume(f, fields, provider)
    body, _ = projection()
    selector = body["publication_inputs"]["selector"]
    selector.update(adapter={"adapter_id": result["adapter_id"], "adapter_version": "1", "parameters": f[3]},
                    requested_schema=requested_form_schema(fields))
    body["publication_inputs"]["adapter"] = deepcopy(selector["adapter"])
    saved = {key: deepcopy(value) for key, value in result.items() if key not in {"sheet", "components"}}
    saved.update(sheet_content=content(result["sheet"], "example-sheet"),
                 components_content=content(result["components"], "example-components"))
    body["publication"]["adapter_result"] = saved
    return {"adapter_id": result["adapter_id"], "adapter_status": result["status"],
        "scope": "Synthetic supplied bytes with actual installed parsers/providers/calculators; controlled publication envelope; no live service or Workflow claim.",
        "original_requested_facts": result["facts"],
        "read_only_return_projection": project_phylogeny_facts(body, requested_sources=FACT_SOURCES, sheet_set=result["sheet"])}


fields = numerical_fields()
fields.update(branches={"metric": "branch_rows", "analysis_id": "a", "population_id": "leaves",
    "tree": slot("tree", tree=True), "node_indices": [1, 5]},
    sites={"metric": "site_rows", "analysis_id": "a", "population_id": "matrix", "columns_0based": [0, 2, 3]},
    qualifications={"metric": "qualifications", "analysis_id": "a", "slot_id": None})
value = {"gene_tree": example(fixture(), fields, "gene_tree"),
         "codon_tree_family_membership": example(codon_hand_fixture(), codon_fields(), "codon_tree")}
(Path(__file__).parent / "FILLED_RETURNS_001.json").write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({key: {"adapter_status": row["adapter_status"], "scalar_values": {
    item["field"]: item["value"] for item in row["read_only_return_projection"][FACT_SOURCES[0]]}}
    for key, row in value.items()}, indent=2))
