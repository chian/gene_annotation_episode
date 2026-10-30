"""Independent arithmetic on the paper's supplied sequences, not a search run."""
import json
from pathlib import Path
import re


def main():
    directory = Path(__file__).resolve().parent
    source_dir = directory.parent / "a101_quefl_native_009"
    text = (source_dir / "supporting_information.txt").read_text()
    section = text.split("List of QueF-like and QueF sequences used for alignment", 1)[1]
    section = section.split("3. Supplemental data 2", 1)[0]
    records = {}
    accession = None
    for raw_line in section.splitlines():
        line = raw_line.replace("\f", "").strip()
        if line.startswith(">"):
            accession = re.search(r"ref\|([^|]+)\|", line).group(1)
            assert accession not in records
            records[accession] = ""
        elif accession and re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY]+", line):
            records[accession] += line
    assert len(records) == 21
    query = records["YP_001055124.1"]
    reference = records["NP_389258.1"]
    assert len(query) == 109
    assert len(reference) == 165
    published_coordinates = [55, 62, 70, 97]
    sequence_coordinates = [56, 63, 71, 98]
    query_coordinates = [21, 28, 36, 63]
    expected_residues = ["C", "D", "Y", "E"]
    rows = []
    for printed, ref_pos, query_pos, aa in zip(
        published_coordinates, sequence_coordinates, query_coordinates, expected_residues
    ):
        assert reference[ref_pos - 1] == query[query_pos - 1] == aa
        rows.append({
            "printed_reference_position": printed,
            "reference_sequence_position": ref_pos,
            "query_sequence_position": query_pos,
            "residue": aa,
            "exact_match": 1,
        })
    motif = re.compile(r"(?=(E[SL]K[SA].K[LY][YFW]))")
    quefl_accessions = list(records)[:8]
    motif_rows = [{
        "record": key,
        "sequence_length": len(records[key]),
        "relaxed_pattern_hits": [m.start() + 1 for m in motif.finditer(records[key])],
    } for key in quefl_accessions]
    assert all(row["relaxed_pattern_hits"] == [] for row in motif_rows)
    exact_reference_starts = [m.start() + 1 for m in re.finditer("ESKSLKLY", reference)]
    assert exact_reference_starts == [79]

    result = {
        "source_doi": "10.1021/cb200361w",
        "kind": "independent_parent_source_arithmetic",
        "source_sequence_record_count": len(records),
        "query_length": len(query),
        "reference_length": len(reference),
        "site_mapping": rows,
        "named_site_match_count": sum(row["exact_match"] for row in rows),
        "named_site_observed_count": len(rows),
        "named_site_match_fraction": sum(row["exact_match"] for row in rows) / len(rows),
        "coordinate_offset_cause": None,
        "relaxed_pattern": "E[SL]K[SA].K[LY][YFW]",
        "relaxed_pattern_note": "Zero with unrestricted h entails zero for a hydrophobic subset; positive relaxed hits would need a specified alphabet.",
        "quefl_motif_rows": motif_rows,
        "signature_bearing_records": 0,
        "signature_bearing_record_fraction": 0 / 8,
        "reference_exact_signature_starts": exact_reference_starts,
        "reported_group_identity_percent_range": [16, 22],
        "fractional_representation_of_same_range": [.16, .22],
        "range_meaning": "reported between-comparison range, neither confidence interval nor pair-specific point",
        "identity_count": None,
        "identity_denominator": None,
        "query_alignment_coverage": None,
        "raw_alignment_score": None,
        "A101_coordinate": None,
        "limits": [
            "Four selected sites are not whole-sequence identity or four independent experiments.",
            "The complete motif's absence does not prove zero cofactor binding or zero function.",
            "Supplied sequence completeness is not independent verification of the expressed construct.",
            "No new alignment, homology search, model inference or scientific episode ran.",
        ],
    }
    output = directory / "quefl_parent_arithmetic_002.json"
    if output.exists():
        assert json.loads(output.read_text()) == result
    else:
        output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": "passed", "query_length": len(query), "site_matches": "4/4", "motif_bearing_records": "0/8", "result_file": str(output)}, indent=2))


if __name__ == "__main__":
    main()
