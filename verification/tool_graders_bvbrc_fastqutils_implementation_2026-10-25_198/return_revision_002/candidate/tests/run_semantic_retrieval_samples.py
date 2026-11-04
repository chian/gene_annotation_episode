"""Operator-invoked FAST retrieval samples; no Episode, gene, job or science run."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gene_annotation_episode.providers import ModelConnection, load_config
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.scientific_tool_retrieval import ScientificToolRetriever, VERSION, SEMANTIC
from gene_annotation_episode.state import Store
from gene_annotation_episode.tool_configuration import build_tools
from method_loop.durable import canonical, content_digest


SAMPLES = [
    ("homology", "Investigate whether a candidate protein is related to a characterized protein "
        "family: find sequence homologs, obtain the actual reference sequences and source annotations, "
        "and inspect aligned residue correspondence and coverage. Preserve the distinction between "
        "sequence similarity and demonstrated biochemical activity."),
    ("neighborhood", "Inspect the genomic neighborhood around an explicitly selected reference gene "
        "in its actual GenBank genome record. Obtain the relevant nucleotide record if needed, inspect "
        "nearby feature identities, orientation and incomplete boundaries, and retain the original "
        "source labels. The requested work is genomic context, not a publication-search investigation."),
    ("structure", "Investigate whether two proteins share a structural fold and corresponding "
        "three-dimensional catalytic-residue geometry. The desired result requires structural "
        "correspondence; sequence alignment alone does not measure it. Select only actual operations "
        "useful for this question, and preserve the absence of a specialized structural comparison "
        "operation when the actual map does not contain one."),
]


async def run(directory):
    directory.mkdir(parents=True, exist_ok=False)
    config = load_config()
    if config["FAST"] != {"model": "gpt-6-luna", "reasoning_effort": "none"}:
        raise ValueError("verification_requires_original_configured_FAST")
    selection = {"version": VERSION, "mode": SEMANTIC, "model": config["FAST"]}
    metadata = {"purpose": "standalone_actual_FAST_retrieval_verification",
        "configured_model_scientific_investigation": False, "configuration": selection,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "samples": [{"name": name, "investigation": question} for name, question in SAMPLES]}
    (directory / "verification-request.json").write_text(canonical(metadata) + "\n")
    with Store(directory / "isolated-state") as store:
        actual = build_tools(store)
        library = ScientificToolLibrary.freeze(directory / "actual-tool-map", catalog=actual.catalog())
        (directory / "actual-map-record.json").write_text(canonical(library.as_record()) + "\n")
        results = []
        async with ModelConnection(config, directory / "providers", directory) as provider:
            retriever = ScientificToolRetriever(store, run_id="semantic-retrieval-verification-001",
                provider=provider, library=library, configuration=selection)
            for name, investigation in SAMPLES:
                outcome = await retriever.retrieve(investigation,
                    episode_id="standalone_verification_harness", operation_key="sample:" + name,
                    available_catalog=actual.catalog())
                row = store.db.execute("SELECT * FROM runtime_tool_retrievals WHERE operation_key=?",
                    ("sample:" + name,)).fetchone()
                result = {"sample": name, "investigation": investigation,
                    "request_sha256": row["request_sha256"],
                    "cache_key": {key: row[key] for key in ("run_id", "episode_id", "operation_key")},
                    "outcome": outcome}
                results.append(result)
                (directory / (name + "-result.json")).write_text(canonical(result) + "\n")
                # Public operation fields only; private provider event logs are
                # retained by ModelConnection and are not read by this script.
                print(json.dumps({"sample": name, "status": outcome["status"],
                    "tools": (outcome.get("result") or {}).get("tools"),
                    "feedback": outcome["feedback"]}), flush=True)
            assert not provider.workers and not provider.sessions
        # Reopen a fresh retriever and prove these completed operations use the
        # original cache without opening another configured model connection.
        class NoDispatch:
            async def complete(self, *args, **kwargs):
                raise AssertionError("completed retrieval must not dispatch")
        restored = ScientificToolRetriever(store, run_id="semantic-retrieval-verification-001",
            provider=NoDispatch(), library=library, configuration=selection)
        for result in results:
            replay = await restored.retrieve(result["investigation"],
                episode_id="standalone_verification_harness",
                operation_key=result["cache_key"]["operation_key"], available_catalog=actual.catalog())
            assert replay == result["outcome"]
        tables = {row[0] for row in store.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert not {"runtime_episodes", "runtime_actions", "runtime_observations", "runtime_model_calls"} & tables
        assert store.db.execute("SELECT count(*) FROM tool_operations").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM records").fetchone()[0] == 0
        assert store.db.execute("SELECT count(*) FROM problem").fetchone()[0] == 0
        summary = {"version": "semantic_retrieval_verification_v1", "configuration": selection,
            "actual_map": library.as_record(), "actual_tool_count": len(library.catalog()),
            "actual_configured_FAST_calls": len(results), "provider_workers_released": True,
            "completed_cache_replay_without_provider": True, "scientific_records": 0,
            "episodes": 0, "selected_scientific_operations": 0, "samples": results}
        (directory / "verification-results.json").write_text(canonical(summary) + "\n")
    manifest = {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.rglob("*")) if path.is_file()}
    (directory / "FILES_SHA256.json").write_text(canonical(manifest) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args().output.resolve()))
