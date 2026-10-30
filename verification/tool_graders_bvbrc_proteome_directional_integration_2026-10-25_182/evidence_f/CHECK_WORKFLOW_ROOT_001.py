"""Read-only root receipt check on the completed controlled Workflow database."""
from pathlib import Path
import json
import sqlite3
import sys

database = Path(sys.argv[1]).resolve()
with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
    connection.row_factory = sqlite3.Row
    attempts = [dict(row) for row in connection.execute(
        "SELECT * FROM runtime_report_attempts WHERE run_id=?", ("directional-shared-workflow",))]
    roots = {row["parent_episode_id"] for row in attempts} - {row["child_episode_id"] for row in attempts}
    assert len(roots) == 1, roots
    root, = roots
    received, = [row for row in attempts if row["parent_episode_id"] == root]
    assert received["decision_index"] == 0 and received["failure"] is None
    row = connection.execute("SELECT form FROM runtime_forms WHERE run_id=? AND episode_id=?",
        ("directional-shared-workflow", received["child_episode_id"])).fetchone()
    actual, expected = json.loads(received["form"]), json.loads(row["form"])
    assert actual == expected
    schema = json.loads(received["contract"])["measurements"]["schema"]
    sources = {node["x-source"] for node in schema["properties"].values()}
    assert len(sources) == len(actual) == 14 and all(len(rows) == 1 for rows in actual.values())
    assert all(name.startswith("bvbrc_proteome_directional_") for name in sources)
    assert actual["fact4"][0]["value"]["cell"]["value"] == dict(sign=0, digits=[2], exponent=-66)
    assert actual["fact1"][0]["value"]["pair_population"]["unresolved_pairs"] == 61
    result = dict(scope="posthoc root admission from completed controlled shared Workflow",
        database=str(database), root_episode_id=root, scientific_child_episode_id=received["child_episode_id"],
        decision_index=0, exact_form_equality=True, source_families=sorted(sources),
        source_family_count=len(sources), native_expectation=actual["fact4"][0]["value"]["cell"]["value"],
        caveat="Retained native bytes, controlled transport and choices; no live BV-BRC service or input-roster linkage claim")
    print(json.dumps(result, indent=2))
