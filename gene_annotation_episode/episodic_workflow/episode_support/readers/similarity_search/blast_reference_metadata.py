"""Deterministic source readers for BLAST's internal scoring sheet.

These functions parse supplied records only. They do not acquire sources, infer
functions from titles, choose references, or assign an overall reliability grade.
Native records are retained for recalculation and inspection.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import xml.etree.ElementTree as ET


def _object(content):
    value = json.loads(content) if isinstance(content, (bytes, str)) else deepcopy(content)
    if not isinstance(value, dict):
        raise ValueError("metadata_object_required")
    return value


def _text(value, code):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _taxid(value):
    return value if type(value) is int and value > 0 else None


def _number(value, *, minimum=0, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value < minimum
            or maximum is not None and value > maximum):
        return None
    return value


def read_uniprot_metadata(content, *, source: str) -> list[dict]:
    """Read exact EC assignments, evidence codes and full-sequence identity.

    Protein names and GO annotations remain separate source statements. Neither
    is silently converted into an EC assignment. A publication citation count
    is retained as a count, never interpreted as independent experiment count.
    UniProt's lineage *names* do not supply NCBI taxids or taxonomic ranks.
    """
    _text(source, "metadata_source_required")
    body = _object(content)
    entries = body.get("results", [body])
    if not isinstance(entries, list):
        raise ValueError("uniprot_entries_required")
    result = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("uniprot_entry_object_required")
        accession = _text(entry.get("primaryAccession"), "uniprot_primary_accession_required")
        organism = entry.get("organism") or {}
        description = entry.get("proteinDescription") or {}
        names = ([description["recommendedName"]] if description.get("recommendedName") else [])
        names += description.get("alternativeNames", []) + description.get("submissionNames", [])
        # Contains/includes describe component polypeptides, so keep their EC
        # assignments with their original scope, not whole-chain candidates.
        functions = []
        for name in names:
            for ec in name.get("ecNumbers", []):
                if not isinstance(ec, dict) or not isinstance(ec.get("value"), str):
                    continue
                evidence = [e["evidenceCode"] for e in ec.get("evidences", [])
                            if isinstance(e, dict) and isinstance(e.get("evidenceCode"), str)]
                functions.append({"function": "EC:" + ec["value"],
                    "label": name.get("fullName", {}).get("value", "EC " + ec["value"]),
                    "evidence": sorted(set(evidence)), "source": source,
                    "reported_evidence": deepcopy(ec.get("evidences", []))})
        sequence = entry.get("sequence", {}).get("value")
        group = ("sha256:" + hashlib.sha256(sequence.encode("ascii")).hexdigest()
                 if isinstance(sequence, str) and sequence and sequence.isascii() else None)
        result.append({"accession": accession, "taxid": _taxid(organism.get("taxonId")),
            "functions": functions, "lineage": [], "source": source,
            "origin": {"database": "UniProtKB", "entry_type": entry.get("entryType"),
                       "scientific_name": organism.get("scientificName")},
            "assembly": {}, "sequence_group": group, "study_groups": [],
            "reported_names": deepcopy(description),
            "reported_lineage_names": deepcopy(organism.get("lineage", [])),
            "reported_go_annotations": [deepcopy(x) for x in entry.get("uniProtKBCrossReferences", [])
                                        if x.get("database") == "GO"],
            "publication_citation_count": len(entry.get("references", [])),
            "sequence_length": len(sequence) if isinstance(sequence, str) else None,
            "native": deepcopy(entry)})
    return result


def read_ncbi_taxonomy(content: bytes | str, *, source: str) -> list[dict]:
    """Read NCBI Taxonomy XML's ordered lineage, including the actual leaf."""
    _text(source, "metadata_source_required")
    root = ET.fromstring(content)
    if root.tag != "TaxaSet":
        raise ValueError("ncbi_taxa_set_required")
    result = []
    for taxon in root.findall("Taxon"):
        def record(node):
            try:
                taxid = int(node.findtext("TaxId", ""))
            except ValueError as error:
                raise ValueError("taxonomy_taxid_required") from error
            if taxid <= 0:
                raise ValueError("taxonomy_positive_taxid_required")
            return {"taxid": taxid, "rank": node.findtext("Rank"),
                    "name": node.findtext("ScientificName")}
        leaf = record(taxon)
        lineage = [record(node) for node in taxon.findall("./LineageEx/Taxon")]
        if any(node["taxid"] == leaf["taxid"] for node in lineage):
            raise ValueError("taxonomy_leaf_repeated_in_lineage")
        result.append({"taxid": leaf["taxid"], "lineage": lineage + [leaf],
            "source": source, "native_xml": ET.tostring(taxon, encoding="unicode")})
    return result


def attach_taxonomy(reference_metadata: list[dict], taxonomy: list[dict]) -> list[dict]:
    """Join only an exact taxid; contradictory source lineages are not resolved."""
    rows = deepcopy(reference_metadata)
    for row in rows:
        taxid = _taxid(row.get("taxid"))
        matches = [item for item in taxonomy if taxid is not None and item.get("taxid") == taxid]
        row["taxonomy_records"] = deepcopy(matches)
        distinct = {json.dumps(item["lineage"], sort_keys=True) for item in matches}
        if len(distinct) == 1:
            candidate = deepcopy(matches[0]["lineage"])
            if row.get("lineage") and row["lineage"] != candidate:
                row.setdefault("issues", []).append({"code": "conflicting_taxonomy_lineages"})
                row["lineage"] = []
            else:
                row["lineage"] = candidate
        elif len(distinct) > 1:
            row["lineage"] = []
            row.setdefault("issues", []).append({"code": "conflicting_taxonomy_lineages"})
    return rows


def read_ncbi_assembly_metadata(content, *, reference_accession: str,
                               assembly_accession: str, linkage_source: str,
                               source: str) -> dict:
    """Populate reference quality from one explicitly linked assembly report.

    The caller supplies a recorded protein-to-assembly link. Sharing a taxon is
    insufficient: this reader never selects a genome from the organism name.
    CheckM percentages become ratios by division by 100. Contamination can
    exceed one; it is a marker-based ratio, not a probability.
    """
    for value in (reference_accession, assembly_accession, linkage_source, source):
        _text(value, "assembly_record_and_link_sources_required")
    report = _object(content)
    if report.get("accession") != assembly_accession:
        raise ValueError("assembly_accession_link_conflict")
    info, stats, checkm = (report.get(name) or {} for name in
                          ("assemblyInfo", "assemblyStats", "checkmInfo"))
    issues = []
    def numeric(container, name, *, maximum=None):
        value = _number(container.get(name), maximum=maximum)
        if name in container and container[name] is not None and value is None:
            issues.append({"code": "invalid_assembly_measurement", "field": name})
        return value
    completeness = numeric(checkm, "completeness", maximum=100)
    contamination = numeric(checkm, "contamination")
    # Integer-valued assembly sizes are serialized as strings by some Datasets
    # clients. Accept only exact unsigned decimal integers, not arbitrary text.
    def size(name):
        value = stats.get(name)
        if isinstance(value, str) and value.isascii() and value.isdigit():
            return int(value)
        if type(value) is int and value >= 0:
            return value
        if value is not None:
            issues.append({"code": "invalid_assembly_measurement", "field": name})
        return None
    assembly = {"accession": assembly_accession, "assembly_level": info.get("assemblyLevel"),
        "completeness_fraction": completeness / 100 if completeness is not None else None,
        "contamination_fraction": contamination / 100 if contamination is not None else None,
        "quality_method": "CheckM" if checkm else None, "quality_version": checkm.get("checkmVersion"),
        "quality_marker_set": checkm.get("checkmMarkerSet"),
        "quality_marker_taxid": checkm.get("checkmSpeciesTaxId"),
        "completeness_percent": completeness, "contamination_percent": contamination,
        "contig_count": size("numberOfContigs"), "contig_n50": size("contigN50"),
        "total_sequence_length": size("totalSequenceLength"),
        "measurement_methods": {
            "completeness_fraction": "CheckM" if checkm else None,
            "contamination_fraction": "CheckM" if checkm else None,
            "contig_count": "NCBI assemblyStats",
            "contig_n50": "NCBI assemblyStats",
            "total_sequence_length": "NCBI assemblyStats"},
        "source": source, "linkage_source": linkage_source}
    biosample = info.get("biosample") or {}
    return {"accession": reference_accession,
        "taxid": _taxid((report.get("organism") or {}).get("taxId")),
        "functions": [], "lineage": [], "source": source,
        "origin": {"database": report.get("sourceDatabase"),
            "biosample_accession": biosample.get("accession"),
            "biosample_attributes": deepcopy(biosample.get("attributes", [])),
            "genome_notes": deepcopy(info.get("genomeNotes", [])),
            "assembly_type": info.get("assemblyType"),
            "bioproject_accession": info.get("bioprojectAccession")},
        "assembly": assembly, "sequence_group": None, "study_groups": [],
        "issues": issues, "native": report}


__all__ = ["read_uniprot_metadata", "read_ncbi_taxonomy", "attach_taxonomy",
           "read_ncbi_assembly_metadata"]
