"""A103 private parser for received GenBank source coordinates and annotations."""
from __future__ import annotations

import io
from typing import Any


def parse_genbank(content: bytes) -> list[dict[str, Any]]:
    """Preserve the fetched record's feature coordinates and source semantics.

    Integer boundaries are Biopython's nominal values in the FETCHED record,
    not automatically coordinates in a full accession fetched as a subsequence.
    Fuzzy position classes/text, part order and remote references are retained.
    Partial markers describe the source location, not inferred sequence damage.
    """
    from Bio import SeqIO
    from Bio.Seq import UndefinedSequenceError

    def position(value):
        try:
            number = int(value)
        except TypeError:
            number = None
        kind = type(value).__name__
        return number, kind, str(value)

    def boundary_partial(kind):
        if kind == "ExactPosition":
            return False
        if kind in {"BeforePosition", "AfterPosition"}:
            return True
        return None

    records = []
    for record_index, record in enumerate(SeqIO.parse(io.StringIO(content.decode("utf-8")), "genbank")):
        features, unlocated = [], []
        for feature_index, feature in enumerate(record.features):
            if feature.location is None:
                unlocated.append({"source_feature_index": feature_index,
                    "kind": feature.type, "qualifiers": dict(feature.qualifiers),
                    "location_text": None})
                continue
            segments = []
            for part in feature.location.parts:
                start, start_kind, start_text = position(part.start)
                end, end_kind, end_text = position(part.end)
                segments.append({"start": start, "end": end,
                    "strand": "+" if part.strand == 1 else "-" if part.strand == -1 else "unknown",
                    "start_kind": start_kind, "end_kind": end_kind,
                    "start_text": start_text, "end_text": end_text,
                    "partial_start": boundary_partial(start_kind),
                    "partial_end": boundary_partial(end_kind),
                    "ref": part.ref, "ref_db": part.ref_db})
            _, start_kind, _ = position(feature.location.start)
            _, end_kind, _ = position(feature.location.end)
            features.append({"kind": feature.type, "segments": segments,
                "source_feature_index": feature_index,
                "location_text": str(feature.location),
                "operator": getattr(feature.location, "operator", None),
                "strand": "+" if feature.location.strand == 1 else "-" if feature.location.strand == -1 else "unknown",
                "partial_start": boundary_partial(start_kind),
                "partial_end": boundary_partial(end_kind),
                "partialness_basis": "source_location_markers_not_inferred_sequence_damage",
                "qualifiers": dict(feature.qualifiers)})
        annotations = {key: value for key, value in record.annotations.items() if key != "references"}
        annotations["references"] = [{"title": item.title, "authors": item.authors,
                                       "journal": item.journal, "pubmed_id": item.pubmed_id}
                                      for item in record.annotations.get("references", [])]
        try:
            sequence = str(record.seq)
        except UndefinedSequenceError:
            sequence = None
        records.append({"accession": record.id, "sequence": sequence,
                        "source_record_index": record_index, "name": record.name,
                        "length": len(record.seq), "sequence_available": sequence is not None,
                        "topology": record.annotations.get("topology"),
                        "accessions": list(record.annotations.get("accessions", [])),
                        "sequence_version": record.annotations.get("sequence_version"),
                        "dbxrefs": list(record.dbxrefs),
                        "description": record.description, "annotations": annotations,
                        "features": features, "unlocated_features": unlocated,
                        "coordinate_system": "zero_based_half_open",
                        "interpretation": "external_features_not_target_annotations"})
    return records

