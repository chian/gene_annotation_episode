"""Direct synthetic preview of an owned proposed function; no shared edit."""
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

import gene_annotation_episode.literature_experimental_prompt as prompt
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository
from test_literature_kinetic_storage import setup, project
from test_literature_kinetic_count_inputs import bind_count


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    proposal = json.loads((OUT / "PROPOSED_RENDERER_DELTA_009.json").read_bytes())
    source = ROOT / proposal["target"]
    assert digest(source) == proposal["baseline_sha256"]
    stage = json.loads((OUT / "STAGE_008_MANIFEST.json").read_bytes())
    for name, row in stage["owned_files"].items():
        assert digest(ROOT / name) == row["sha256"]
    tree = ast.parse((OUT / "renderer_proposal_009/proposed.py").read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_kinetic_received")
    namespace = dict(vars(prompt))
    exec(compile(ast.Module(body=[function], type_ignores=[]), "owned_proposed_kinetic_renderer", "exec"), namespace)
    render = namespace["_kinetic_received"]
    text = "Synthetic count at least three independent experiments"
    store, child, args = setup(OUT / "renderer_proposal_probe_009", extra=text)
    with store:
        artifact = store.get(args["source_ref"])["artifact_ref"]
        bind_count(args, store.get_artifact(artifact).decode(), text, "three")
        repo = LiteratureKineticRepository(store, child.run_id)
        outcome = repo.populate(child, args, "synthetic-proposed-renderer")
        raw, = project(repo, outcome, ["numerator_parameter"])
        ratio, = project(repo, outcome, ["parameter_ratio"])
        records = {row["id"]: row for row in store.list("reference")}
        result = {}
        for name, row in (("raw_parameter_requested", raw), ("derived_only", ratio)):
            parts = []
            render(parts, [row], records)
            shown = "\n".join(parts)
            assert all(field in shown for field in proposal["five_added_fields"])
            assert "qualified" in shown and "exact_count_qualified" in shown and "english_cardinal" in shown
            assert "| count_relation | ge |" in shown
            assert "three" not in shown
            if name == "raw_parameter_requested":
                assert "| count_reported_value | 3 |" in shown
            else:
                assert "count_reported_value" not in shown
            result[name] = {"five_count_meanings_visible": True,
                "qualified_relation_visible": True,
                "source_word_hidden_from_labels": True,
                "reported_numeral_displayed": name == "raw_parameter_requested"}
        assert not store.list("observation")
    for name, row in stage["owned_files"].items():
        assert digest(ROOT / name) == row["sha256"]
    assert digest(source) == proposal["baseline_sha256"]
    receipt = {"passed": True, "scope": "direct synthetic mechanical function preview; not actual Episode/provider/admission verification",
        "cases": result, "shared_file_unchanged": True, "six_frozen008_live_files_unchanged": True,
        "episode_or_model_execution": False, "synthetic_observations": 0}
    with (OUT / "RENDERER_PREVIEW_RECEIPT_009.json").open("x") as stream:
        json.dump(receipt, stream, indent=2)
        stream.write("\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
