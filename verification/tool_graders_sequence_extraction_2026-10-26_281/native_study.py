"""Actual local sequence-view outputs from explicit, tiny synthetic inputs."""
import json
from pathlib import Path
from importlib.metadata import version
from gene_annotation_episode.sequence_views import view_sequence

rows = []
for sequence, molecule, segments, orientation in [
    ("AcGtUrYsWkMbDhVn", "dna", None, "reverse_complement"),
    ("AcGtUrYsWkMbDhVn", "rna", None, "reverse_complement"),
    ("ACGTTGCAA", "dna", [{"start": 4, "end": 7}, {"start": 0, "end": 3},
                            {"start": 4, "end": 7}, {"start": 2, "end": 5}], "as_is"),
    ("ACGTTGCAA", "dna", [{"start": 4, "end": 7}, {"start": 0, "end": 3},
                            {"start": 4, "end": 7}, {"start": 2, "end": 5}], "reverse_complement"),
    ("MaG*?", "protein", None, "as_is"),
]:
    request = {"molecule": molecule, "segments": segments or [{"start": 0, "end": len(sequence)}],
               "orientation": orientation}
    rows.append({"input_sequence": sequence, "request": request,
                 "native": view_sequence(sequence, **request)})
body = {"fixture_identity": "actual_native_helper_outputs_on_synthetic_sequences",
        "biopython_version": version("biopython"), "examples": rows}
Path("native_outputs.json").write_text(json.dumps(body, indent=2) + "\n")
print(json.dumps(body, indent=2))
