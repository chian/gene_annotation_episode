"""Run the staged format proof and retain its native documents and exact results.

Run with the repository .venv Python, from staging, and PYTHONPATH set to staging.
Filesystem reads/writes here are verification harness work, not parser behavior.
No native program, remote service, model or episode is executed by this harness.
"""
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import random
import sys
import unittest

from gene_annotation_episode import phylogeny_formats as formats
from gene_annotation_episode import phylogeny_format_contracts as contracts


HERE = Path(__file__).resolve().parent
STAGING = HERE.parent / "staging"
REPO = HERE.parents[2]
NATIVE = REPO / "verification/tool_graders_bvbrc_phylogeny_boundaries_2026-10-24"
GOAL = Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")
CONTRACT = HERE.parent / "PARSER_CONTRACT.md"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reference(data, name):
    # Harness identities are explicit test bindings, not production task custody.
    return {"raw_artifact_ref": "verification-artifact:" + name,
            "source_ref": "retained-example:" + name, "sha256": sha(data)}


def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def mutations():
    rng = random.Random(20261024)
    cases = [(formats.parse_newick, b"(A:0,(B:1,C:2)0:3);", {"dialect": "newick", "allow_multiple": True}),
        (formats.parse_aligned_fasta, b">A\nAcG-\n>B\nACGT\n", {"id_rule": "first_whitespace_token"}),
        (formats.parse_relaxed_phylip, b"2 4\nA AC\nB GT\n\nGT\nAC\n", {"layout": "interleaved", "continuation_ids": "absent"}),
        (formats.parse_raxml_partitions, b"DNA, p=1-3\nLGF,q=4-6\n", {"alignment_column_count": 6}),
        (formats.parse_phyloxml, b"<phyloxml><phylogeny><clade><name>A</name><branch_length>0</branch_length><confidence>0</confidence></clade></phylogeny></phyloxml>", {})]
    results = []
    for function, source, kwargs in cases:
        statuses = Counter()
        for _ in range(1200):
            data = bytearray(source)
            for _ in range(1 + rng.randrange(3)):
                position = rng.randrange(len(data) + 1)
                if rng.randrange(2) and position < len(data):
                    del data[position]
                else:
                    data[position:position] = bytes([rng.choice(b"<>:/,;'\"[]&() \n012AZ-")])
            data = bytes(data)
            result = function(data, artifact=reference(data, "synthetic-mutation"), **kwargs)
            json.dumps(result, allow_nan=False)
            statuses[result["status"]] += 1
        results.append({"reader": function.__name__, "mutations": 1200, "statuses": dict(statuses)})
    return {"seed": 20261024, "total_mutations": 6000, "uncaught_exceptions": 0,
            "meaning": "deterministic robustness checks, not a proof of semantic correctness for every malformed format",
            "readers": results}


def main():
    assert Path.cwd().resolve() == STAGING
    assert Path(sys.executable) == REPO / ".venv/bin/python"
    imports = {m.__name__: str(Path(m.__file__).resolve()) for m in (formats, contracts)}
    assert all(Path(path).is_relative_to(STAGING) for path in imports.values())
    assert sha(GOAL.read_bytes()) == "11e35ba1f0faea89c183af307a4b4bd2dd9a6b1a8fbd63af8bac42d06e7a17f7"
    assert sha(CONTRACT.read_bytes()) == "cedd264ad0db30176782ba35692c1889e4d4b612d34cd50fc9c3a8612ca925cb"
    output = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(STAGING / "tests"), pattern="test_phylogeny_formats.py")
    tests = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    (HERE / "TEST_RESULTS.txt").write_text(output.getvalue())
    assert tests.wasSuccessful(), output.getvalue()

    documents, files = [], []
    codon = NATIVE / "official_example/test9_genome_dir"
    operands = [(next(codon.glob("*.phy")), formats.parse_relaxed_phylip, {"layout": "interleaved", "continuation_ids": "absent"}),
                (next(codon.glob("*.partitions")), formats.parse_raxml_partitions, {"alignment_column_count": 15300})]
    for prefix, dialect, multiple in [("RAxML_bestTree.", "newick", False), ("RAxML_bipartitions.", "newick", False),
                                     ("RAxML_bipartitionsBranchLabels.", "raxml_branch_labels", False), ("RAxML_bootstrap.", "newick", True)]:
        operands.append((next(codon.glob(prefix + "*")), formats.parse_newick, {"dialect": dialect, "allow_multiple": multiple}))
    for path in sorted((NATIVE / "additional_sources/bvbrc_gene_tree/tests").glob("*.xml")):
        operands.append((path, formats.parse_phyloxml, {}))
    for path, function, kwargs in operands:
        data = path.read_bytes()
        name = str(path.relative_to(NATIVE))
        result = function(data, artifact=reference(data, name), **kwargs)
        assert result["status"] == "ok", result["diagnostics"]
        documents.append({"source_path": str(path), "reader": function.__name__, "parameters": kwargs, "result": result})
        files.append({"path": str(path), "sha256": sha(data), "bytes": len(data)})
    save("NATIVE_DOCUMENTS.json", documents)
    # Round-trip actual saved JSON documents; validators perform no acquisition.
    restored = json.loads((HERE / "NATIVE_DOCUMENTS.json").read_text())
    for row in restored:
        doc = row["result"]["value"]
        if doc["format"] in ("aligned_fasta", "relaxed_phylip"):
            assert contracts.validate_alignment_document(doc) == doc
        elif doc["format"] in ("newick", "phyloxml"):
            for tree in doc["trees"]:
                record = tree["tree"] if doc["format"] == "phyloxml" else tree
                assert contracts.validate_tree_record(record) == record
    alignment = documents[0]["result"]["value"]
    partitions = documents[1]["result"]["value"]
    xml_facts = []
    for row in documents:
        doc = row["result"]["value"]
        if doc["format"] != "phyloxml":
            continue
        tree = doc["trees"][0]
        confidence = [c for a in tree["annotations"] for c in a["confidences"]]
        xml_facts.append({"source_path": row["source_path"], "tips": sum(not n["child_indices"] for n in tree["tree"]["nodes"]),
            "nodes": len(tree["tree"]["nodes"]), "generic_support_observations": len(confidence),
            "explicit_support_zeros": sum(c["value"] == 0 for c in confidence),
            "properties": sum(len(a["properties"]) for a in tree["annotations"]),
            "explicit_branch_lengths": sum(n["branch_length"] is not None for n in tree["tree"]["nodes"]),
            "support_method": "unknown"})
    facts = {"alignment_rows": len(alignment["rows"]), "alignment_columns": alignment["observed_column_count"],
             "literal_gap_cells": sum(row["sequence"].count("-") for row in alignment["rows"]),
             "all_cells": sum(len(row["sequence"]) for row in alignment["rows"]),
             "partition_sites": [len(row["columns_0based"]) for row in partitions["partitions"]],
             "bootstrap_trees": len(documents[5]["result"]["value"]["trees"]), "phyloxml": xml_facts}
    source_files = [STAGING / "gene_annotation_episode/phylogeny_formats.py",
                    STAGING / "gene_annotation_episode/phylogeny_format_contracts.py", STAGING / "tests/test_phylogeny_formats.py"]
    verification = {"scope": "staged parser/validator verification only", "python": sys.executable,
        "cwd": str(Path.cwd()), "import_paths": imports, "tests_run": tests.testsRun,
        "test_failures": len(tests.failures), "test_errors": len(tests.errors), "native_files": files,
        "code_sha256": {str(path): sha(path.read_bytes()) for path in source_files},
        "goal_sha256": sha(GOAL.read_bytes()), "contract_sha256": sha(CONTRACT.read_bytes()),
        "facts": facts, "mutation_checks": mutations(), "saved_document_validation": "passed",
        "live_service_execution": "not performed", "episode_path_integration": "not verified"}
    save("VERIFICATION.json", verification)
    print(json.dumps({"tests_run": tests.testsRun, "status": "passed", "facts": facts,
                      "import_paths": imports, "mutation_count": 6000}, indent=2))


if __name__ == "__main__":
    main()
