"""Reproducible, explicitly synthetic database arithmetic and native pair sheet."""
from pathlib import Path
import json

from gene_annotation_episode.blast_graders import grade_blast_result
from gene_annotation_episode.blast_database_grader import calculate_database_probabilities
from gene_annotation_episode.blast_reference_metadata import read_ncbi_assembly_metadata

HERE = Path(__file__).resolve().parent
out = HERE / "synthetic_database"
out.mkdir(exist_ok=True)


def save(name, value):
    (out / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


query = "MACDEFGHIK"
hits, metadata = [], []
for i, (accession, function, score, taxid, superkingdom, completeness, contamination) in enumerate([
        ("SYN_A", "EC:1.1.1.1", 10, 562, 2, 98., 1.),
        ("SYN_B", "EC:2.2.2.2", 9, 243232, 2157, 96., 2.),
        ("SYN_C", "EC:1.1.1.1", 10, 562, 2, 90., 7.)]):
    subject = "MACDAFGHIK" if i == 1 else query
    hits.append({"num": i + 1, "len": 20,
        "description": [{"accession": accession, "taxid": taxid, "title": "SYNTHETIC reference"}],
        "hsps": [{"bit_score": score, "score": score * 2, "evalue": .01,
            "query_from": 1, "query_to": 10, "hit_from": 1, "hit_to": 10,
            "qseq": query, "hseq": subject, "identity": 9 if i == 1 else 10,
            "gaps": 0, "align_len": 10}]})
    metadata.append({"accession": accession, "taxid": taxid,
        "functions": [{"function": function, "label": "Synthetic function " + function,
            "evidence": ["synthetic-assignment"], "source": "synthetic-function-record:" + accession}],
        "source": "synthetic-function-record:" + accession,
        "lineage": [{"taxid": superkingdom, "rank": "superkingdom", "name": "Synthetic lineage"},
                    {"taxid": taxid, "rank": "species", "name": "Synthetic species label"}],
        "origin": {"source_type": "metagenome" if i == 2 else "cultured_isolate"},
        "assembly": {}, "sequence_group": None, "study_groups": []})
    assembly = {"accession": "GCA_" + accession, "organism": {"taxId": taxid},
        "assemblyInfo": {"assemblyLevel": "Contig" if i == 2 else "Complete Genome"},
        "assemblyStats": {"numberOfContigs": 10 if i == 2 else 1, "totalSequenceLength": "3000000"},
        "checkmInfo": {"completeness": completeness, "contamination": contamination, "checkmVersion": "synthetic"}}
    metadata.append(read_ncbi_assembly_metadata(assembly, reference_accession=accession,
        assembly_accession=assembly["accession"], linkage_source="synthetic-explicit-link:" + accession,
        source="synthetic-assembly-record:" + accession))
native = {"BlastOutput2": [{"report": {"program": "blastp", "version": "SYNTHETIC_BLAST",
    "search_target": {"db": "synthetic_db"}, "params": {"expect": 10},
    "results": {"search": {"query_id": "synthetic_query", "query_len": 10, "hits": hits,
        "stat": {"db_num": 1000, "db_len": 20000, "eff_space": 200000}}}}}]}
request = {"program": "blastp", "database": "synthetic_db", "query_length": 10,
    "query_sequence": query, "hitlist_size": 3, "database_release": "synthetic-release-1"}
target = {"taxid": 562, "source": "synthetic-supplied-target-context", "independent_of_search": True,
    "lineage": [{"taxid": 2, "rank": "superkingdom", "name": "Bacteria"},
                {"taxid": 562, "rank": "species", "name": "Escherichia coli"}]}
profile = {"database": "synthetic_db", "release": "synthetic-release-1",
    "source": "synthetic-whole-database-census", "scope": "searched_database",
    "count_unit": "unique_sequences", "total_count": 1000,
    "function_counts": {"EC:1.1.1.1": 200, "EC:2.2.2.2": 50}}
for name, value in (("api.native.json", native), ("request.json", request),
                    ("reference_metadata.json", metadata), ("target_context.json", target),
                    ("database_profile.json", profile)):
    save(name, value)
fields = ["qseqid", "sacc", "qlen", "slen", "qstart", "qend", "sstart", "send", "qseq", "sseq",
          "bitscore", "score", "evalue", "length", "nident", "gaps", "staxids"]
lines = ["# BLASTP SYNTHETIC", "# Query: synthetic_query", "# Database: synthetic_db"]
for hit in hits:
    hsp = hit["hsps"][0]
    values = ["synthetic_query", hit["description"][0]["accession"], 10, 20, 1, 10, 1, 10,
        query, hsp["hseq"], hsp["bit_score"], hsp["score"], .01, 10, hsp["identity"], 0,
        hit["description"][0]["taxid"]]
    lines.append("\t".join(map(str, values)))
lines += ["# 3 hits found", "# BLAST processed 1 queries"]
(out / "hpc.native.tsv").write_text("\n".join(lines) + "\n")
save("hpc.fields.json", fields)
for resource, fmt, name in (("api", "json2", "api.native.json"), ("hpc", "tabular", "hpc.native.tsv")):
    graded = grade_blast_result((out / name).read_bytes(), mode="database", resource=resource,
        output_format=fmt, request=request, fields=fields if fmt == "tabular" else None,
        reference_metadata=metadata, target_context=target, database_profile=profile)
    save(resource + ".graded.json", graded)
loaded = json.loads((out / "api.graded.json").read_text())
recalculated = calculate_database_probabilities(loaded["sheet"], model={"temperature_bits": 2.0})
save("recalculated-temperature-2.json", recalculated)
pair = HERE / "native_pair"
if (pair / "result.json").exists():
    result = grade_blast_result((pair / "result.json").read_bytes(), mode="pairwise", resource="local", output_format="json2")
    (pair / "graded.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
summary = {"synthetic": True,
    "unadjusted": loaded["probabilities"]["unadjusted_probabilities"],
    "representation_adjusted": loaded["probabilities"]["representation_adjusted_probabilities"],
    "recalculated_temperature_2": recalculated["representation_adjusted_probabilities"],
    "metadata_coverage": loaded["sheet"]["coverage"],
    "taxonomy": loaded["sheet"]["taxonomy"]["ranks"],
    "source_quality": loaded["sheet"]["source_quality"]["numerical_summaries"]}
save("summary.json", summary)
print(json.dumps(summary, indent=2))
