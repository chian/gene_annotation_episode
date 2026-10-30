"""Reproducible retained-native extraction/recalculation audit; launches nothing."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

from gene_annotation_episode.infernal_preparation_emission import populate_cmemit_sheet
from gene_annotation_episode.infernal_preparation_emission_calculations import calculate_cmemit_components
from gene_annotation_episode.infernal_preparation_models import extract_infernal_models

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
PRIOR=ROOT/"verification/tool_graders_infernal_preparation_boundaries_2026-10-26_246/native"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def artifact(path, role, fmt):
    return {"role":role,"format":fmt,"artifact_ref":str(path.relative_to(ROOT)),"sha256":digest(path),
            "size_bytes":path.stat().st_size,"completeness":"complete"}


def operation(command):
    # Resolved defaults come from the inspected 1.1.5 cmemit.c option table.
    # This audit code has the original selected argv. Pure production readers
    # never discover defaults from a path or guess omitted supplied settings.
    settings={"-N":10,"--idx":1,"--seed":0,"--rna":True,"--dna":False,
              "--hmmonly":False,"--nohmmonly":False,"-l":False,"--iid":False,
              "--u5p":False,"--u3p":False}
    mode="sample_unaligned"
    args=iter(command[1:])
    for arg in args:
        if arg in {"-o","--tfile"}:
            next(args)
        elif arg in {"-N","--idx","--seed","-e","--a5p","--a3p"}:
            settings[arg]=int(next(args))
        elif arg=="--exp": settings[arg]=float(next(args))
        elif arg=="--outformat": settings[arg]=next(args)
        elif arg=="--dna": settings.update({"--dna":True,"--rna":False})
        elif arg=="--rna": settings.update({"--dna":False,"--rna":True})
        elif arg in settings: settings[arg]=True
        elif arg=="-a": mode="sample_aligned"
        elif arg=="-c": mode="consensus"
    if mode=="sample_aligned": settings.setdefault("--outformat","Stockholm")
    return {"program":"cmemit","mode":mode,"engine_version":"1.1.5","settings":settings}


def main():
    results=[]
    examples=BASE/"examples"
    examples.mkdir(exist_ok=True)
    folders=[*sorted(PRIOR.glob("cmemit_*")),*sorted((BASE/"native").iterdir())]
    for folder in folders:
        if not folder.is_dir(): continue
        request=json.loads((folder/"request.json").read_text())
        receipt=json.loads((folder/"receipt.json").read_text())
        op=operation(request["command"])
        fmt=op["settings"].get("--outformat","fasta").lower()
        ma=artifact(folder/"model.cm","models","infernal_cm_ascii")
        output_path=folder/"emitted.out"
        oa=artifact(output_path,"generated_alignment" if op["mode"]=="sample_aligned" else "generated_sequences",fmt)
        models=extract_infernal_models((folder/"model.cm").read_bytes(),artifact=ma,format=ma["format"],engine_version="1.1.5")
        retained=[ma,oa]
        tp=None
        if (folder/"traces.txt").exists():
            ta=artifact(folder/"traces.txt","trace","infernal_trace")
            retained.append(ta)
            tp={"artifact":ta,"content":(folder/"traces.txt").read_bytes()}
        sheet=populate_cmemit_sheet(operation=op,artifacts=retained,models=models,
            output={"artifact":oa,"content":output_path.read_bytes()},trace=tp)
        calculations=calculate_cmemit_components(sheet,parameters={})
        restored=json.loads(json.dumps(sheet,allow_nan=False))
        assert calculate_cmemit_components(restored,parameters={})==calculations
        prefix=("prior_" if folder.parent==PRIOR else "new_")+folder.name
        for suffix,data in (("sheet",sheet),("calculations",calculations)):
            (examples/(prefix+"."+suffix+".json")).write_text(json.dumps(data,indent=2,allow_nan=False)+"\n")
        source_digests={f["path"]:f["sha256"] for f in receipt["files"]}
        for filename in ("model.cm","emitted.out"):
            assert digest(folder/filename)==source_digests[filename]
        seqs=[r for r in sheet["output_records"] if r["kind"]=="generated_sequence"]
        results.append({"native_directory":str(folder.relative_to(ROOT)),"native_returncode":receipt["returncode"],
            "mode":op["mode"],"format":fmt,"models":len(models["records"]),"sequences":len(seqs),
            "alignments":sum(r["kind"]=="generated_alignment" for r in sheet["output_records"]),
            "trace_headers":len(sheet["native_rows"]),"sequence_lengths":[r["values"]["residue_count"]["value"] for r in seqs],
            "gc_counts":[r["values"]["gc_count"]["value"] for r in seqs],
            "sheet_issues":sheet["issues"],"calculation_issues":calculations["issues"],
            "saved_recalculation_equal":True,"artifact_hashes_verified_against_native_receipt":True,
            "receipt_sha256":digest(folder/"receipt.json")})
    source_paths=["gene_annotation_episode/infernal_preparation_emission.py",
        "gene_annotation_episode/infernal_preparation_emission_calculations.py",
        "gene_annotation_episode/infernal_preparation_models.py","gene_annotation_episode/infernal_preparation_schema.py",
        "gene_annotation_episode/hmmalign_inputs.py","resources/software/infernal-1.1.5/src/cmemit.c",
        "resources/software/infernal-1.1.5/easel/esl_msafile_a2m.c",
        "resources/software/infernal-1.1.5/easel/esl_msafile_phylip.c",
        "resources/software/infernal-1.1.5-install/bin/cmemit",
        "tests/test_infernal_preparation_emission.py","tests/test_infernal_preparation_emission_calculations.py"]
    summary={"created_at":datetime.now(timezone.utc).isoformat(),"cases":results,
        "case_count":len(results),"new_native_command_count":sum(r["native_directory"].startswith(str(BASE.relative_to(ROOT))) for r in results),
        "source_sha256":{p:digest(ROOT/p) for p in source_paths},"production_episode_integration_verified":False,
        "scope":"pure generated-data parser/calculator plus retained native executions through local_jobs",
        "correction":"Earlier visual estimate38 of embedded length was wrong; all retained -e40 examples contain40 residues. No native bytes changed."}
    (BASE/"VERIFICATION_001.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"cases":len(results),"new_native_commands":summary["new_native_command_count"],
        "native_failures_retained":[r["native_directory"] for r in results if r["native_returncode"]!=0],
        "saved_recalculations_equal":len(results),"receipt_hashes_verified":len(results)},indent=2))


if __name__=="__main__": main()
