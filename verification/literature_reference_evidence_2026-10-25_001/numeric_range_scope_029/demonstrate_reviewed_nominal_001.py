"""Controlled selected-operation demo; no model, new interpretation or acquisition.

The scientific assignments and exact witnesses are reviewed028 inputs. Ordinary
shared-loop mechanics are exercised by the controlled provider used in the new
integration check. Never rerun this script against an existing demonstration.
"""
from pathlib import Path
import hashlib
import json
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_literature_amount_range_scope_integration import (
    test_controlled_nominal_selected_action_returns_once_in_ordinary_episode_loop,
)
from gene_annotation_episode.literature_amount_inputs import LEXICAL_DEPENDENCY
from gene_annotation_episode.literature_amount_storage import LiteratureAmountRepository
from gene_annotation_episode.state import Store


def main():
    generation = sys.argv[1] if len(sys.argv) > 1 else "001"
    if generation not in ("001", "002", "003", "004"):
        raise RuntimeError("unknown_demonstration_identity")
    target = OUT / ("controlled_original_nominal_" + generation)
    if target.exists():
        raise RuntimeError("preserve_existing_demo_choose_a_new_identity")
    original = OUT.parent / "amount_components_027"
    preserved = {name: hashlib.sha256((original / name).read_bytes()).hexdigest() for name in (
        "CASE025_POPULATED_001.json", "NOMINAL_GUARD_DIAGNOSTIC_001.json", "replay_case025_witnesses_001.py")}
    test_controlled_nominal_selected_action_returns_once_in_ordinary_episode_loop(target)
    with Store(target / "state") as store:
        operation = store.db.execute("SELECT * FROM literature_amount_operations").fetchone()
        outcome = json.loads(operation["outcome"])
        saved = LiteratureAmountRepository(store, operation["run_id"]).read(outcome["result"]["sheet_ref"])
        received = [dict(row) for row in store.db.execute("SELECT * FROM literature_amount_received")]
        for row in received:
            row["cells"] = json.loads(row["cells"])
        report = {"version": "numeric_scope029_controlled_original_nominal_v1",
            "model_inference": False, "new_scientific_interpretation": False, "source_acquisition": False,
            "scientific_assignments": "reviewed028 nominal concentrations and respective-flask relationship",
            "lexical_dependency": LEXICAL_DEPENDENCY, "selection": saved["selection"],
            "outcome": outcome, "saved": saved, "received": received,
            "runtime_observations": [dict(row) for row in store.db.execute("SELECT * FROM runtime_observations")],
            "runtime_forms": [dict(row) for row in store.db.execute("SELECT * FROM runtime_forms")],
            "runtime_actions": [dict(row) for row in store.db.execute("SELECT * FROM runtime_actions")],
            "preserved_original027_sha256": preserved,
            "limits": ["controlled_provider_and_fixture_controllers", "actual_model_amount_extraction_unverified",
                "supplement_uninspected", "volume_wording_unrepaired", "nominal_not_active_concentration",
                "no_amount_response_correction", "covariance_unreported", "no_W05_aggregation",
                "full_literature_goal_remains_active"]}
    assert preserved == {name: hashlib.sha256((original / name).read_bytes()).hexdigest() for name in preserved}
    path = OUT / ("CONTROLLED_NOMINAL_DEMO_" + generation + ".json")
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"report": str(path), "observations": len(report["runtime_observations"]),
        "received_cells": len(report["received"][0]["cells"]),
        "nominal_cells": {name: cell["value"] for name, cell in saved["sheet"]["cells"].items()}}, indent=2))


if __name__ == "__main__":
    main()
