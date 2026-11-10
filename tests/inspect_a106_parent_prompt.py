"""Render a retained model request read-only; never start a model or workflow.

Run this CLI through tools/one_workflow.sh. Output goes to its run directory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

from gene_annotation_episode.journal_metadata import restore_request


def load_request(run, episode, call):
    class ReadOnlyArtifacts:
        def __init__(self, db):
            self.db = db

        def get_artifact(self, reference):
            digest = reference.removeprefix("artifact_")
            assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
            raw = (run / "state/artifacts" / digest[:2] / digest).read_bytes()
            assert hashlib.sha256(raw).hexdigest() == digest
            return raw

    with sqlite3.connect((run.resolve() / "state/state.sqlite3").as_uri() + "?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT request FROM runtime_model_calls WHERE episode_id=? AND call_index=?",
                         (episode, call)).fetchone()
        if row is None:
            raise ValueError("requested_model_call_missing")
        return json.loads(restore_request(ReadOnlyArtifacts(db), row["request"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("episode")
    parser.add_argument("call", type=int)
    args = parser.parse_args()
    from gene_annotation_episode import literature_experimental_prompt as experimental
    from gene_annotation_episode import literature_reference_parent_prompt as parent
    from gene_annotation_episode.workflow_budget import active_budget
    request = load_request(args.run, args.episode, args.call)
    state = request["context"]
    from gene_annotation_episode.literature_a106_render import split_reports
    reports = state.get("child_reports", [])
    ordinary, results = split_reports(reports)
    for result in results:
        assert any(report.get(result['return_field']) == result['rows'] for report in reports)
    sections = []
    original = experimental._section

    def measured_section(parts, title, content):
        sections.append({"title": title, "characters": len(content or "")})
        return original(parts, title, content)

    experimental._section = parent._section = measured_section
    try:
        prompt = experimental.render_literature_experimental_prompt(state, "")
    finally:
        experimental._section = parent._section = original
    run = Path(active_budget()["run_directory"])
    (run / "prompt.txt").write_text(prompt)
    summary = {"source_run": str(args.run), "episode": args.episode, "call": args.call,
        "rendered_characters": len(prompt), "instructions": "empty diagnostic instructions",
        "saved_result_fields": len(results), "ordinary_return_fields": len(ordinary),
        "returned_numerical_rows_preserved": True,
        "sections": sorted(sections, key=lambda s: s["characters"], reverse=True)}
    (run / "prompt-size.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
