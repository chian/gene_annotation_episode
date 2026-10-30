"""Recalculate these saved B001 examples without native work or acquisition."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from gene_annotation_episode.biopython_pairwise_grader import calculate_biopython_pairwise_scores
from gene_annotation_episode.blast_database_grader import calculate_database_probabilities
from gene_annotation_episode.prodigal_grader import calculate_prodigal_scores
from gene_annotation_episode.sequence_composition_grader import calculate_sequence_composition_scores


def main():
    directory = Path(__file__).resolve().parent
    checked = 0
    recalculated = 0
    thresholds = None
    for path in sorted(directory.glob("*.json")):
        example = json.loads(path.read_text())
        if not isinstance(example, dict) or example.get("representation") != "b001_integration_verification_example_v1":
            continue
        checked += 1
        for source in example["sources"]:
            native = directory / source["stored_native_file"]
            assert hashlib.sha256(native.read_bytes()).hexdigest() == source["stored_native_sha256"]
            gradings = ([row["grading"] for row in source["grading_rows"]]
                        if "grading_rows" in source else source["gradings"])
            for grading in gradings:
                before = deepcopy(grading)
                operation = example["operation"]
                if operation in {"sequence.align", "reads.align"}:
                    assert calculate_biopython_pairwise_scores(grading["sheet"]) == grading["scores"]
                elif operation == "genes.predict":
                    assert calculate_prodigal_scores(grading["sheet"]) == grading["scores"]
                elif operation == "internal.api_service.ncbi_blast.result":
                    assert calculate_database_probabilities(grading["sheet"]) == grading["probabilities"]
                else:
                    assert operation in {"sequence.inspect", "reads.inspect"}
                    assert calculate_sequence_composition_scores(grading["sheet"]) == grading["scores"]
                    if path.stem == "read_quality_full_member" and grading["scores"]["mean_phred"] > 0:
                        changed = calculate_sequence_composition_scores(grading["sheet"], quality_thresholds=(0, 40, 41))
                        thresholds = changed["quality_thresholds"]
                        assert [row["count_at_or_above"] for row in thresholds] == [16000, 15999, 0]
                assert grading == before
                recalculated += 1
    assert checked == 9 and recalculated == 12
    print(json.dumps({"saved_examples_checked": checked, "grading_results_recalculated": recalculated,
                      "changed_quality_thresholds": thresholds}, indent=2))


if __name__ == "__main__":
    main()
