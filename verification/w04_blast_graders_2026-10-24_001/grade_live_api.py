"""Grade the saved live API result using explicitly acquired metadata files.

No network operations, retries or new jobs occur here. Re-running this script
rebuilds the example from retained inputs, without assigning annotation credit.
"""
from pathlib import Path
import json

from gene_annotation_episode.blast_graders import grade_blast_result
from gene_annotation_episode.blast_grading_inputs import parse_blast_json
from gene_annotation_episode.blast_reference_metadata import (
    attach_taxonomy, read_ncbi_taxonomy, read_uniprot_metadata,
)

HERE = Path(__file__).resolve().parent
api, metadata_dir = HERE / "live_api", HERE / "live_metadata"
job = json.loads((api / "job.json").read_text())
query = "".join((api / "query.faa").read_text().splitlines()[1:])
submission = json.loads((api / "request.json").read_text())
request = {"program": submission["program"], "database": submission["database"],
    "hitlist_size": submission["hitlist_size"], "query_length": len(query),
    "query_sequence": query, "query_material_source": "live_api/query.faa",
    "rid": job["rid"]}
raw = (api / "result.body").read_bytes()
normalized = parse_blast_json(raw, mode="database", resource="api", request=request)
references = [description for hit in normalized["hits"] for description in hit["descriptions"]]
accessions = sorted({d["accession"] for d in references if isinstance(d.get("accession"), str)})
taxids = sorted({d["taxid"] for d in references if type(d.get("taxid")) is int})
(api / "reported-reference-inputs.json").write_text(json.dumps({"accessions": accessions,
    "taxids": taxids}, indent=2) + "\n")

metadata = []
if (metadata_dir / "uniprot-hits.json").exists():
    metadata.extend(read_uniprot_metadata((metadata_dir / "uniprot-hits.json").read_bytes(),
        source="live_metadata/uniprot-hits.json"))

taxa = []
if (metadata_dir / "reference-taxonomy.xml").exists():
    taxa = read_ncbi_taxonomy((metadata_dir / "reference-taxonomy.xml").read_bytes(),
        source="live_metadata/reference-taxonomy.xml")
# Each native descriptor already binds this accession to this taxon. Attaching
# that taxon's exact lineage preserves the existing binding; it does not infer
# a taxon for any other accession or transfer a function across aliases.
for description in references:
    accession, taxid = description.get("accession"), description.get("taxid")
    if not accession or type(taxid) is not int:
        continue
    metadata.append({"accession": accession, "taxid": taxid, "functions": [],
        "lineage": [], "source": "live_api/result.body", "origin": {}, "assembly": {},
        "sequence_group": None, "study_groups": []})
metadata = attach_taxonomy(metadata, taxa)

target = {"taxid": 511145, "lineage": [], "source": "GOAL.md fixed public E. coli MG1655 case",
          "independent_of_search": True}
if (metadata_dir / "target-taxonomy.xml").exists():
    target_taxa = read_ncbi_taxonomy((metadata_dir / "target-taxonomy.xml").read_bytes(),
        source="live_metadata/target-taxonomy.xml")
    matches = [row for row in target_taxa if row["taxid"] == target["taxid"]]
    if len(matches) != 1:
        raise ValueError("exact_target_taxonomy_record_required")
    target["lineage"] = matches[0]["lineage"]
    target["taxonomy_source"] = "live_metadata/target-taxonomy.xml"

result = grade_blast_result(raw, mode="database", resource="api", output_format="json2",
    request=request, reference_metadata=metadata, target_context=target)
(api / "graded.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
sheet, probabilities = result["sheet"], result["probabilities"]
summary = {"rid": job["rid"], "synthetic": False,
    "query_length": len(query), "database": normalized["search"]["database"],
    "native_hit_count": len(normalized["hits"]),
    "native_hsp_count": sum(len(hit["hsps"]) for hit in normalized["hits"]),
    "reported_accession_count": len(accessions), "reported_taxon_count": len(taxids),
    "coverage": sheet["coverage"], "search_limits": sheet["search_limits"],
    "function_components": [{"function": row["function"], "sequence_group_count": row["sequence_group_count"],
                             "bit_score": row["bit_score"]} for row in sheet["functions"]],
    "taxonomy": sheet["taxonomy"]["ranks"],
    "unadjusted_probabilities": probabilities["unadjusted_probabilities"],
    "representation_adjusted_probabilities": probabilities["representation_adjusted_probabilities"],
    "representation_adjustment_unavailable_reasons": probabilities["representation_adjustment_unavailable_reasons"],
    "issues": sheet["issues"]}
(api / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
print(json.dumps(summary, indent=2))
