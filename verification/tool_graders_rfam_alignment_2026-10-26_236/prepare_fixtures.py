"""Make explicitly labelled format-test operands, never production correlations.

Native report displays are copied by their actual Query block and model label.
Only their labels/indentation are adapted to the six-string Rfam display shape.
The fixture's artifact identity belongs to this derived JSON, not to an actual
Rfam JSON row. Every original line range, source hash and input source survives.
"""
from pathlib import Path
import hashlib
import json
import re


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "fixtures"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(path, *, name, family, accession, sequence, occurrence, input_source, label):
    lines = path.read_text().splitlines()
    queries = [(i, line.split()[1]) for i, line in enumerate(lines) if line.startswith("Query:")]
    starts = [i for i, query in queries if query == name]
    assert len(starts) == 1
    start = starts[0]
    end = next((i for i, _ in queries if i > start), len(lines))
    fields = {field: [] for field in ("nc", "ss", "hit_seq", "match", "user_seq", "pp")}
    retained = []
    query_starts, query_ends = [], []
    for i in range(start, end):
        match = re.fullmatch(r"\s+" + re.escape(family) + r"\s+(\d+) (.+?)\s+(\d+)\s*", lines[i])
        if match is None:
            continue
        left, body, right = match.groups()
        offset, width = match.start(2), len(body)
        qmatch = re.fullmatch(r"\s+" + re.escape(name) + r"\s+(\d+) (.+?)\s+(\d+)\s*", lines[i + 2])
        assert qmatch is not None and len(qmatch[2]) == width
        fields["hit_seq"].append(f"#CM {left} {body} {right}")
        fields["user_seq"].append(f"#SEQ {qmatch[1]} {qmatch[2]} {qmatch[3]}")
        query_starts.append(int(qmatch[1]))
        query_ends.append(int(qmatch[3]))
        for field, label_text, line in (("nc", "#NC", i - 2), ("ss", "#SS", i - 1),
                                        ("match", "#MATCH", i + 1), ("pp", "#PP", i + 3)):
            fields[field].append(label_text + " " + lines[line][offset:offset + width])
        retained.append({"first_line_1i": i - 1, "last_line_1i": i + 4,
                         "original_lines": lines[i - 2:i + 4]})
    assert retained
    artifact = "fixture:" + label
    value = {
        "fixture_kind": "derived_native_report_display",
        "qualification": "Native display bytes with labels/indentation adapted; not a native Rfam JSON response or production report binding.",
        "source": {"path": str(path.relative_to(ROOT)), "sha256": digest(path), "query_name": name,
                   "model_name": family, "blocks": retained},
        "input_source": input_source,
        "query_sequence": sequence,
        "hit_identity": {"artifact_ref": artifact, "hit_key": artifact + "/hits/" + family + "/0",
                         "query_occurrence_key": occurrence, "family_accession": accession},
        "native_start": query_starts[0], "native_end": query_ends[-1],
        "native_strand": "+" if query_starts[0] <= query_ends[-1] else "-",
        "alignment": {field: "\n".join(values) for field, values in fields.items()},
    }
    target = OUT / (label + ".json")
    target.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return {"path": str(target.relative_to(ROOT)), "sha256": digest(target),
            "fixture_kind": value["fixture_kind"], "source_sha256": value["source"]["sha256"]}


def main():
    OUT.mkdir(exist_ok=True)
    live = ROOT / "verification/tool_graders_rfam_transport_2026-10-26_234/live/multi"
    inputs = json.loads((live / "input-manifest.json").read_text())
    records = []
    for record in inputs["records"]:
        records.append(extract(live / "005-fetch-out/response.body", name=record["original_header"],
            family="5S_rRNA", accession="RF00001", sequence=record["submitted_sequence"],
            occurrence=record["query_occurrence_key"],
            input_source={"path": str((live / "input-manifest.json").relative_to(ROOT)),
                          "sha256": digest(live / "input-manifest.json"),
                          "original_record_ordinal": record["original_record_ordinal"]},
            label="native-" + record["original_header"]))
    tutorial = ROOT / "resources/software/infernal-1.1.5/tutorial"
    fasta = (tutorial / "metag-example.fa").read_text()
    selected = [record for record in fasta.split(">") if record.startswith("AAFY01022046.1 ")]
    assert len(selected) == 1
    sequence = "".join(selected[0].splitlines()[1:])
    records.append(extract(tutorial / "minifam-metag.out", name="AAFY01022046.1", family="Cobalamin",
        accession="RF00174", sequence=sequence, occurrence="upstream-tutorial-original-occurrence-1",
        input_source={"path": str((tutorial / "metag-example.fa").relative_to(ROOT)),
                      "sha256": digest(tutorial / "metag-example.fa"), "original_record_ordinal": 1},
        label="upstream-cobalamin-wrapped-local-end"))
    (OUT.parent / "fixture-manifest.json").write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"fixture_count": len(records), "manifest": str(OUT.parent / "fixture-manifest.json")}))


if __name__ == "__main__":
    main()
