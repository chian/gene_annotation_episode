"""Filled F1 sheets from workload259; reads retained artifacts, runs no native tool."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tests"))
from test_hmmer_fm_data import ABI, NATIVE, build_sheet, exact_sheet
from gene_annotation_episode.hmmer_fm_calculations import calculate_hmmer_fm_components


def main():
    destination = Path.cwd()/"examples"
    destination.mkdir()
    summary = []
    cases = [("makehmmerdb_"+case,build_sheet(case)) for case in ("dna","fwd","rna","protein","ambiguous")]
    cases += [("hmmerfm_exactmatch_"+case,exact_sheet(case)) for case in
              ("forward","counts_forward","locations","counts","reverse","forward_index","ambiguous","ambiguous_counts","zero","default_output")]
    native_paths = set()
    for name,sheet in cases:
        parameters = {"alphabet_normalization":"rna_to_dna" if name=="makehmmerdb_rna" else "none",
                      "coordinate_policy":"native_one_based","exhaustive_literal_check":name.startswith("hmmerfm_")}
        components = calculate_hmmer_fm_components(sheet,parameters=parameters)
        for suffix,document in (("sheet",sheet),("components",components)):
            (destination/(name+"_"+suffix+".json")).write_text(json.dumps(document,indent=2)+"\n")
        for occurrence in sheet["artifact_occurrences"]:
            native_paths.add(ROOT/occurrence["artifact_ref"].removeprefix("retained:"))
        for directory in (NATIVE/"native"/name,):
            native_paths.update(directory/filename for filename in ("receipt.json","intent.json"))
        summary.append({"case":name,"components":{r["kind"]:{key:value["value"] for key,value in r["components"].items()}
                        for r in components["rows"] if r["kind"].endswith("summary")},
                        "failed_checks":[{"name":c["name"],"record_key":c["record_key"]} for c in components["checks"] if c["state"]=="fail"]})
    source_paths = [ROOT/"resources/software/infernal-1.1.5/hmmer/src"/name for name in
                    ("makehmmerdb.c","hmmerfm-exactmatch.c","fm_alphabet.c","fm_general.c","fm_sse.c","hmmer.h")]
    source_paths += [ROOT/"gene_annotation_episode/hmmer_fm_data.py",ROOT/"gene_annotation_episode/hmmer_fm_calculations.py"]
    hashes = {str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(native_paths|set(source_paths))}
    manifest = {"generated_at":datetime.now(timezone.utc).isoformat(),"producer_contract":ABI,"sha256":hashes,
                "native_execution":"none in workload264; original workload259 receipts retained and hashed",
                "verification":"pure parser/calculator with supplied retained bytes; no production result-path or episode communication verification"}
    (destination/"provenance.json").write_text(json.dumps(manifest,indent=2)+"\n")
    (destination/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
