"""Verify exact old optical receipt representation, without editing old runs."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))
from gene_annotation_episode.domain import canonical, identity
from gene_annotation_episode.literature_optical_storage import LiteratureOpticalRepository
from test_literature_optical_storage import setup
from test_literature_rate_episode_integration import service_binding


def main():
    destination = HERE / "pre044_optical_format_store_005"
    if destination.exists():
        raise RuntimeError("Preserve existing proof; use a new destination")
    store, context, args = setup(destination)
    try:
        repo = LiteratureOpticalRepository(store, context.run_id)
        outcome = repo.populate(context, args, "original-selected-optical")
        sheet = outcome["result"]["sheet_ref"]
        cells = repo.project_cells([sheet], permitted_record_refs=outcome["record_refs"], components=["net_rate"])
        parent = replace(context, episode_id="old-optical-receiver", received_record_refs=tuple(
            [*context.received_record_refs, *outcome["record_refs"]]))
        # These are exactly004's old table columns and old digest calculation.
        # No new base receive method is called to manufacture this fixture.
        digest = identity("optical_admitted_cells", cells)
        store.db.execute("INSERT INTO literature_optical_received VALUES(?,?,?,?)",
            (context.run_id, parent.episode_id, "old-trusted-manual", canonical(cells)))
        store.db.execute("INSERT INTO literature_optical_delivery_bindings VALUES(?,?,?,?)",
            (context.run_id, parent.episode_id, "old-trusted-manual", digest))
        _, binding = service_binding(store, parent)
        for *_, factory in binding._population_routes():
            factory()
        before = list(store.db.iterdump())
        original_get = store.get_artifact
        forbidden_artifacts = {store.get(ref)["artifact_ref"] for ref in context.received_record_refs}
        def saved_only(ref):
            assert ref not in forbidden_artifacts
            return original_get(ref)
        def forbidden(*_args, **_kwargs):
            raise AssertionError("Old receipt forwarding must not parse or recalculate")
        store.db.execute("PRAGMA query_only=ON")
        with patch.object(store, "get_artifact", saved_only), patch(
            "gene_annotation_episode.literature_optical_storage.read_optical_rate_operands", forbidden), patch(
            "gene_annotation_episode.literature_optical_storage.calculate_nadh_optical_rate", forbidden):
            assert repo.received_cells(parent) == cells
            assert binding.facts(parent, {"committed_record_refs": [sheet]})["literature_optical_cells"] == cells
        assert list(store.db.iterdump()) == before
        result = {"status": "passed", "synthetic_only": True, "model_calls": 0,
            "actual_historical_run_opened": False, "representation": "exact004 manual receipt columns and optical_admitted_cells digest",
            "new_base_receive_used_to_create_fixture": False, "source_artifacts_forbidden": True,
            "parsers_calculators_forbidden": True, "SQL_query_only": True, "all_SQL_unchanged": True,
            "full_sheet_cells": 2, "admitted_and_forwarded_cells": 1,
            "optical_source_sha256": hashlib.sha256((ROOT / "gene_annotation_episode/literature_optical_storage.py").read_bytes()).hexdigest()}
        (HERE / "PRE044_OPTICAL_FORMAT_RECEIPT_005.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
    finally:
        store.close()


if __name__ == "__main__":
    main()
