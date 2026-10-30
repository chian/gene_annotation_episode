"""Read-only research arithmetic; not a production reader, grader, or test suite.

Only supplied official example bytes are inspected. No network or native analysis
is invoked. Synthetic examples are reported separately from official examples.
"""
from collections import Counter, defaultdict
from hashlib import sha256
from io import StringIO
from math import log2, sqrt
from pathlib import Path
import json
import re
import xml.etree.ElementTree as ET

import Bio
from Bio import AlignIO, Phylo


ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / "official_example/test9_genome_dir"
NS = {"p": "http://www.phyloxml.org"}


def splits(tree):
    names = frozenset(t.name for t in tree.get_terminals())
    rows = {}
    for node in tree.find_clades():
        group = frozenset(t.name for t in node.get_terminals())
        other = names - group
        if min(len(group), len(other)) < 2:
            continue
        side = min((tuple(sorted(group)), tuple(sorted(other))), key=lambda x: (len(x), x))
        rows[side] = node
    return rows


alignment_file = next(EXAMPLE.glob("*.phy"))
alignment = AlignIO.read(alignment_file, "phylip-relaxed")
sequences = {row.id: str(row.seq) for row in alignment}
length = alignment.get_alignment_length()
partition_file = next(EXAMPLE.glob("*.partitions"))
partitions = []
for line in partition_file.read_text().splitlines():
    model, name, start, end, step = re.fullmatch(
        r"(\S+), (\S+) = (\d+)-(\d+)(?:\\(\d+))?", line).groups()
    columns = list(range(int(start)-1, int(end), int(step or 1)))
    counts = Counter(sequences[member][col] for member in sequences for col in columns)
    canonical = set("ACGT") if model == "DNA" else set("ACDEFGHIKLMNPQRSTVWY")
    partitions.append({"name": name, "model": model, "start_1based": int(start),
        "end_1based_inclusive": int(end), "step": int(step or 1), "site_count": len(columns),
        "member_count": len(alignment), "cell_count": len(columns)*len(alignment),
        "symbol_counts": dict(sorted(counts.items())), "gap_cells": counts["-"],
        "noncanonical_nongap_cells": sum(v for k,v in counts.items() if k not in canonical | {"-"})})
trees = {role: Phylo.read(next(EXAMPLE.glob(prefix+".*")), "newick") for role,prefix in
    {"best": "RAxML_bestTree", "supported": "RAxML_bipartitions"}.items()}
bootstrap_trees = list(Phylo.parse(next(EXAMPLE.glob("RAxML_bootstrap.*")), "newick"))
supported_splits = splits(trees["supported"])
support_rows = []
for side, node in sorted(supported_splits.items()):
    matches = sum(side in splits(tree) for tree in bootstrap_trees)
    support_rows.append({"split_side": list(side), "native_internal_label": node.confidence,
        "matching_replicates": matches, "replicate_count": len(bootstrap_trees),
        "derived_bootstrap_fraction": matches/len(bootstrap_trees)})
membership_file = next(EXAMPLE.glob("*.pgfamsAndGenesIncludedInAlignment.txt"))
membership = []
for line in membership_file.read_text().splitlines():
    if not line:
        continue
    fields = line.split("\t")
    family, kind = fields[:2]
    members = [v for v in fields[2:] if v]
    membership.append({"family_id": family, "kind": kind, "member_count": len(members),
        "feature_ids": members})
log = next(EXAMPLE.glob("RAxML_info.*")).read_text()
native = {"evidence_kind": "official_repository_example_not_service_execution",
    "biopython_inspection_version": Bio.__version__,
    "alignment": {"file": str(alignment_file.relative_to(ROOT)), "format": "phylip-relaxed-interleaved",
        "member_count": len(alignment), "site_count": length, "member_ids": list(sequences),
        "cell_count": len(alignment)*length, "gap_cells": sum(s.count('-') for s in sequences.values()),
        "identical_sequence_groups": [ids for seq,ids in
            ((s,[k for k,v in sequences.items() if v==s]) for s in sorted(set(sequences.values()))) if len(ids)>1]},
    "partitions": partitions,
    "raxml_version": re.search(r"RAxML version (\S+)", log).group(1),
    "native_final_ml_optimization_log_likelihood": float(re.search(r"Final ML Optimization Likelihood: (\S+)",log).group(1)),
    "native_distinct_alignment_patterns": int(re.search(r"Alignment has (\d+) distinct",log).group(1)),
    "native_gap_and_undetermined_percent_rounded": float(re.search(r"characters in this alignment: (\S+)%",log).group(1)),
    "native_branch_optimization": "joint", "bootstrap_tree_count": len(bootstrap_trees),
    "tree_tip_count": len(trees['supported'].get_terminals()),
    "tree_branch_length_sum": sum(t.branch_length for t in trees['supported'].find_clades() if t.branch_length is not None),
    "unrooted_split_difference_best_vs_supported": len(set(splits(trees['best'])) ^ set(supported_splits)),
    "support_rows": support_rows, "family_membership_rows": membership,
    "qualifications": ["Filename says 8taxa but actual header and both trees have 9 members.",
        "Archive is an older native example; its mixed PHYLIP is not proof current service uploads PHYLIP in mixed mode.",
        "No source-to-run or original task custody exists for this repository example.",
        "Per-family block membership cannot be mapped from filename or independently sorted family lists."]}
xml_rows = []
for file in sorted((ROOT / "additional_sources/bvbrc_gene_tree/tests").glob("*.xml")):
    xml = ET.parse(file).getroot()
    clades = xml.findall(".//p:clade",NS)
    tips = [clade for clade in clades if clade.find("p:clade",NS) is None]
    products = Counter()
    for tip in tips:
        for prop in tip.findall("p:property",NS):
            if prop.attrib.get("ref") in {"BVBRC:product","product"}:
                products[prop.text] += 1
    xml_rows.append({"file": str(file.relative_to(ROOT)), "tip_count": len(tips),
        "confidence_count": len(xml.findall(".//p:confidence",NS)),
        "confidence_types": sorted({n.attrib.get('type') for n in xml.findall('.//p:confidence',NS)}),
        "exact_product_property_counts": dict(products),
        "support_method": None,
        "qualification": "Generic support label and filename do not establish bootstrap/RELL, model, or runtime version."})
native["gene_tree_xml_examples"] = xml_rows
(ROOT/"NATIVE_EXAMPLE_INSPECTION.json").write_text(json.dumps(native,indent=2)+"\n")

synthetic_rows = ["A-CX","ATCX","ATGX","AT-X"]
counts = [Counter(row[i] for row in synthetic_rows) for i in range(4)]
sums = [sum((v/4)**2 for k,v in c.items() if k != '-') for c in counts]
perseq = [sum(log2(counts[i][row[i]]/4) for i in range(4))/4 for row in synthetic_rows]
synthetic = {"evidence_kind": "synthetic_arithmetic_not_native_output",
    "protein_alignment_rows": synthetic_rows,
    "gap_count": 2, "gap_denominator": 16, "gap_fraction": 2/16,
    "ambiguous_X_count": 4, "ambiguous_denominator":16,"ambiguous_fraction":4/16,
    "canonical_cell_count":10,"canonical_cell_denominator":16,
    "literal_nongap_squared_frequency_by_site": sums,
    "codontree_literal_sum_squared_frequency":sum(sums),
    "codontree_literal_mean_squared_frequency":sum(sums)/4,
    "codontree_alignment_ranking_score":sum(sums)/sqrt(4),
    "codontree_per_sequence_mean_log2_frequency":perseq,
    "canonical_majority_fraction_by_site":[1.0,1.0,2/3,None],
    "canonical_shannon_bits_by_site":[0.0,0.0,-2/3*log2(2/3)-1/3*log2(1/3),None],
    "bootstrap_example":{"matching_replicates":3,"total_replicates":4,"fraction":3/4},
    "composition_example":{"selected_tip_count":4,"function_A_count":2,"function_B_count":1,
        "unassigned_count":1,"function_A_fraction_all_tips":2/4,"function_A_fraction_assigned_tips":2/3}}
(ROOT/"SYNTHETIC_NUMERICAL_EXAMPLES.json").write_text(json.dumps(synthetic,indent=2)+"\n")
assert len(alignment)==9 and length==15300
assert [r['site_count'] for r in partitions]==[3825]*4
assert len(bootstrap_trees)==100 and len(support_rows)==6
assert all(r['matching_replicates']==100 and r['native_internal_label']==100 for r in support_rows)
assert sum(sums)==2.875 and sum(sums)/sqrt(4)==1.4375
print(json.dumps({"native_members":len(alignment),"native_sites":length,
    "partition_sites":[r['site_count'] for r in partitions],
    "gap_cells":native['alignment']['gap_cells'],"cells":len(alignment)*length,
    "native_log_likelihood":native['native_final_ml_optimization_log_likelihood'],
    "bootstrap_replicates":len(bootstrap_trees),"internal_supported_splits":len(support_rows),
    "xml_examples":xml_rows,"synthetic_sum_squared_frequency":sum(sums),
    "synthetic_alignment_score":sum(sums)/sqrt(4)},indent=2))
