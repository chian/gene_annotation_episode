"""Pure reader validation of unchanged public selections; never episode admission.

No provider records are accessed. Scientific candidate results are retained for
later review, not printed or treated as original child returns. This script
does not establish scientific operand meanings, source possession, completion
or observation credit.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sqlite3
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pin", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("Never overwrite a retained probe")
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.pin.resolve()))
    from gene_annotation_episode.literature_partner_native_inputs import read_partner_native_inputs
    from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
    from gene_annotation_episode.state import Store

    store = Store.__new__(Store)
    store.path, store._savepoint = args.state.resolve(), 0
    store.db = sqlite3.connect((store.path / "state.sqlite3").as_uri() + "?mode=ro",
        uri=True, isolation_level=None)
    store.db.row_factory = sqlite3.Row
    before = store.db.total_changes
    sources = {}
    def source(reference, representation):
        metadata = store.get(reference)
        artifact = metadata["artifact_ref"] if representation == "original" else metadata.get("text_ref")
        if artifact is None:
            raise RuntimeError("Selected source representation is unavailable")
        raw = store.get_artifact(artifact)
        assert artifact == "artifact_" + hashlib.sha256(raw).hexdigest()
        sources[reference + ":" + representation] = artifact
        return {"artifact_ref": artifact, "content": raw}

    results = []
    for row in store.db.execute("SELECT episode_id,decision_index,action,result FROM runtime_actions "
            "WHERE episode_id=? AND decision_index<=31 ORDER BY decision_index",
            ("episode_51dbd703f63e6019afbf8737b90087141cdfc8a424f70145b2a136ca689d3428",)):
        selected = json.loads(row["action"])
        if selected.get("tool") != "literature.partner.source.populate":
            continue
        original = json.loads(row["result"]) if row["result"] else {}
        feedback = original.get("feedback") or {}
        result = {"episode_id": row["episode_id"], "decision_index": row["decision_index"],
            "original_status": original.get("status"), "original_failure_code": feedback.get("code"),
            "unchanged_arguments_sha256": hashlib.sha256(json.dumps(selected["arguments"],
                sort_keys=True, separators=(",", ":")).encode()).hexdigest()}
        try:
            candidate = read_partner_native_inputs(selected["arguments"], read_source=source)
            result.update(prospective_validation="completed", failure_code=None, failure_field=None,
                unreviewed_candidate=candidate)
        except ExperimentalContractError as error:
            result.update(prospective_validation="rejected", failure_code=error.code,
                failure_field=error.field)
        results.append(result)
    assert store.db.total_changes == before == 0
    store.db.close()
    payload = {"scope": "Pure reader validation of unchanged original public selections. Candidate calculations are unreviewed prospective dry results, not original selected outcomes, admitted typed returns or new scientific evidence. No write to live state, no model call or controller observation.",
        "pin": str(args.pin.resolve()), "source_artifacts": sources, "database_changes": 0,
        "results": results}
    args.output.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"output": str(args.output), "database_changes": 0,
        "results": [{key: value for key, value in row.items() if key != "unreviewed_candidate"}
                    for row in results]}, indent=2))


if __name__ == "__main__":
    main()
