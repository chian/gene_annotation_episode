"""Produce inspectable examples from saved inputs only; no scientific execution."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import scipy
from gene_annotation_episode.bvbrc_minhash_grader import (
    calculate_minhash_components,
    parse_minhash_result,
)


def forbidden(*args, **kwargs):
    raise AssertionError("offline recalculation cannot acquire or execute work")


socket.create_connection = forbidden
socket.socket.connect = forbidden
subprocess.Popen = forbidden

DESTINATION = Path(__file__).resolve().parent
SOURCE = ROOT / "verification/tool_graders_bvbrc_native_rpc_contract_2026-10-24/sources/Mash/test/ref/genomes.dist"


def request(mode):
    return {"version": "1.1", "method": f"Minhash.compute_genome_distance_for_{mode}2",
            "params": ["synthetic.query" if mode == "genome" else "/owner/workspace/input.fa",
                       1.0, 1.0, 10, 1, 1, 1, 0], "id": "synthetic-example"}


def metadata(index, genome, k=1):
    return {"row_index": index, "genome_id": genome, "kmer_length": k,
            "query_length": 2, "reference_length": 2, "alphabet_size": 2,
            "provenance": {"kind": "explicit_synthetic_example", "is_actual_biological_measurement": False}}


def example(name, native, *, mode="genome", pair_metadata=None, provenance=None):
    selected = request(mode)
    envelope = {"version": "1.1", "id": selected["id"], "result": [deepcopy(native)]}
    provenance = provenance or {"kind": "synthetic_native_shape", "live_bvbrc_output": False}
    parsed = parse_minhash_result(envelope["result"][0], mode=mode, request=selected, provenance=provenance)
    saved = json.loads(json.dumps(parsed["sheet"], allow_nan=False))
    before = deepcopy(saved)
    calculated = calculate_minhash_components(saved, pair_metadata=pair_metadata)
    assert saved == before == parsed["sheet"]
    return {"name": name, "qualification": "synthetic_BV_BRC_envelope_not_live_service_output",
            "request": selected, "synthetic_rpc_envelope": envelope,
            "parse_result": parsed, "pair_metadata": pair_metadata, "components": calculated}


def main():
    lines = [line.split("\t") for line in SOURCE.read_text().splitlines()]
    upstream = [[f"synthetic.reference.{index}", *fields[2:]] for index, fields in enumerate(lines)]
    upstream_provenance = {
        "kind": "upstream_native_Mash_values_in_synthetic_BV_BRC_wrapper",
        "source": str(SOURCE.relative_to(ROOT)),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "live_bvbrc_output": False, "original_mash_rows": lines,
        "genome_id_mapping": "invented_synthetic_identifiers_not_inferred_biological_joins",
    }
    examples = [example(f"upstream_Mash_values_{mode}", upstream, mode=mode,
                        provenance=upstream_provenance) for mode in ("genome", "fasta")]
    for item in examples:
        first = item["components"]["rows"][0]
        assert first["shared_hash_fraction"] == 0.041
        assert first["recomputed_distance"] is None
        assert first["recomputed_pvalue"] is None
    small_native = [["synthetic.reference", "0.223144", "0.259259", "2/3"]]
    small = example("small_exact_binomial", small_native,
                    pair_metadata=[metadata(0, "synthetic.reference")])
    first = small["components"]["rows"][0]
    exact = 3 * Fraction(1, 3)**2 * Fraction(2, 3) + Fraction(1, 3)**3
    assert exact == Fraction(7, 27)
    assert math.isclose(first["recomputed_pvalue"], float(exact), rel_tol=1e-14)
    assert math.isclose(first["recomputed_distance"], math.log(5/4), rel_tol=1e-14)
    saved_sheet = json.loads(json.dumps(small["parse_result"]["sheet"]))
    changed_metadata = [metadata(0, "synthetic.reference", k=2)]
    recalculated = calculate_minhash_components(saved_sheet, pair_metadata=changed_metadata)
    second = recalculated["rows"][0]
    assert math.isclose(second["recomputed_pvalue"], float(Fraction(13, 125)), rel_tol=1e-14)
    assert math.isclose(second["recomputed_distance"], math.log(5/4)/2, rel_tol=1e-14)
    assert second["reported_distance"] == first["reported_distance"]
    assert second["reported_pvalue"] == first["reported_pvalue"]
    small["saved_sheet_recalculation"] = {"changed_pair_metadata": changed_metadata,
                                          "components": recalculated,
                                          "independent_exact_tail": "13/125"}
    small["independent_exact_tail"] = "7/27"
    examples.append(small)
    boundary_rows = [["duplicate", 1, 1, "0/3"], ["duplicate", 0, 0.037037, "3/3"],
                     ["zero.denominator", 0, 1, "0/0"], ["malformed", None, "bad", "4/3"],
                     None, ["missing", "0.1"]]
    examples.append(example("partial_duplicates_and_boundaries", boundary_rows, mode="fasta",
                            pair_metadata=[metadata(index, native[0]) for index, native in enumerate(boundary_rows[:3])]))
    examples.append(example("empty_completeness_unknown", []))
    document = {"schema": "bvbrc_minhash_filled_examples_v1", "examples": examples}
    (DESTINATION / "FILLED_EXAMPLES.json").write_text(json.dumps(document, indent=2, allow_nan=False) + "\n")
    summary = {
        "schema": "bvbrc_minhash_offline_verification_v1",
        "scipy_version": scipy.__version__, "example_count": len(examples),
        "upstream_native_fraction": 0.041,
        "small_example": {"distance": first["recomputed_distance"], "pvalue": first["recomputed_pvalue"],
                          "exact_pvalue": "7/27"},
        "saved_sheet_changed_k_example": {"distance": second["recomputed_distance"],
                                          "pvalue": second["recomputed_pvalue"], "exact_pvalue": "13/125"},
        "saved_sheet_unchanged": saved_sheet == small["parse_result"]["sheet"],
        "pure_parser_calculator_verified": True, "network_calls": 0, "jobs_submitted": 0,
        "model_calls": 0, "credentials_inspected": False,
        "live_BV_BRC_output_verified": False, "complete_episode_integration_verified": False,
        "retained_native_evidence": "upstream Mash fixture values wrapped synthetically; no BV-BRC live response",
        "remaining_work": ["C4 selected API-child invocation and receipt custody",
                           "C4 requested typed-return integration verification",
                           "live service availability/authentication and deployed source/metadata verification"],
    }
    (DESTINATION / "OFFLINE_VERIFICATION.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
