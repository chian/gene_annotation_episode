"""Rebuild numerical artifacts from retained native bytes, without execution."""
from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.hmmalign_inputs import parse_hmmalign_stockholm, build_hmmalign_sheet
from gene_annotation_episode.hmmalign_grader import calculate_hmmalign_scores

HERE = Path(__file__).resolve().parent
NATIVE = HERE/"native"


def fasta_metadata(path):
    result = []
    for entry in path.read_text().split(">")[1:]:
        name, *lines = entry.splitlines()
        sequence = "".join(lines)
        result.append({"name": name, "occurrence": 0, "sequence": sequence, "length": len(sequence), "origin": "new"})
    return result


def profile_metadata(path):
    """The retained HMMER3/f amino fixtures use 20 emissions plus native MAP."""
    metadata, mapping = {}, []
    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0] in {"NAME", "ACC", "LENG", "ALPH", "CKSUM"}:
            key = {"NAME": "name", "ACC": "accession", "LENG": "length", "ALPH": "alphabet", "CKSUM": "checksum"}[parts[0]]
            metadata[key] = int(parts[1]) if key in {"length", "checksum"} else parts[1]
        elif parts[0].isdigit() and len(parts) == 26:
            mapping.append(int(parts[21]))
    assert metadata["alphabet"] == "amino" and len(mapping) == metadata["length"]
    return {**metadata, "map": mapping}


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+"\n")


examples = []
for mode in ("ordinary", "trim", "mapali", "fragment_mapali", "fragment_mapali_trim"):
    fragment = mode.startswith("fragment_")
    inputs = {"profile": profile_metadata(NATIVE/("fragment_profile.hmm" if fragment else "profile.hmm")),
        "sequences": fasta_metadata(NATIVE/("fragment_sequences.fa" if fragment else "sequences.fa")),
        "trim": mode in {"trim", "fragment_mapali_trim"}, "acquisition": {"output_complete": True},
        "native_parameters": {"program": "hmmalign", "trim": mode in {"trim", "fragment_mapali_trim"}, "mapali": "mapali" in mode}}
    if "mapali" in mode:
        seed = "fragment_seed.sto" if fragment else "seed.sto"
        inputs["mapali"] = {"artifact_ref": "fixture:"+seed, "stockholm": (NATIVE/seed).read_text()}
    native = parse_hmmalign_stockholm((NATIVE/mode/"stdout.txt").read_text(),
                                    artifact_ref=f"fixture:{mode}/stdout.txt", engine_version="3.4")
    sheet = build_hmmalign_sheet(native, inputs=inputs)
    scores = calculate_hmmalign_scores(sheet)
    assert not scores["issues"], (mode, scores["issues"])
    destination = HERE/"saved"/mode
    destination.mkdir(parents=True, exist_ok=True)
    write(destination/"inputs.json", inputs)
    write(destination/"sheet.json", sheet)
    write(destination/"scores.json", scores)
    keys = ("name", "origin", "fragment", "original_length", "model_length", "match_state_residues", "deleted_model_positions",
            "missing_model_positions", "insert_state_residues", "model_occupancy", "sequence_match_coverage", "retained_residues",
            "terminal_unaligned_residues", "trimmed_residues", "posterior_lower_mean", "posterior_upper_mean",
            "posterior_bounded_residue_count", "posterior_unavailable_residue_count")
    examples.append({"mode": mode, "native_sha256": hashlib.sha256((NATIVE/mode/"stdout.txt").read_bytes()).hexdigest(),
        "sheet": f"saved/{mode}/sheet.json", "scores": f"saved/{mode}/scores.json",
        "mapali_status": sheet["mapali"]["status"], "mapali_computed_checksum": sheet["mapali"]["computed_checksum"],
        "summary": scores["summary"],
        "sequences": [{**{key: row[key] for key in keys}, "original_interval": row["mapping"]["original_interval"]}
                      for row in scores["sequences"]]})
write(HERE/"EXAMPLES.json", examples)
print("Rebuilt five saved native sheets and calculations; no native execution or network access.")
