"""Engineering-only ESM metadata/occurrence/projection controls.

The literal320-component vectors below are supplied fixtures, not an ESM run,
checkpoint, received Artifact, Source publication or model-quality evidence.
Actual inference requires a separately selected pinned model/runtime resource.
"""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from gene_annotation_episode import esm_gene_embedding_contracts as contracts
from gene_annotation_episode import esm_gene_embedding_worker as worker


RAW = b">same header\r\nAC\r\n>same header\nD\n>long\nAAAAA\n>lower\nac\n>unrequested\nE\n"


def deployment():
    """Deliberately nonexistent paths; pure metadata is not deployed software."""
    pin = lambda path: dict(path=path, sha256="1"*64, size_bytes=1)
    return dict(version="esm_gene_embedding_deployment_v1", model_name=contracts.MODEL,
        layer_count=6, embedding_dimension=320, device="cpu",torch_threads=1,
        checkpoint=pin("/engineering/models/"+contracts.MODEL+".pt"),
        regression_checkpoint=pin("/engineering/models/"+contracts.MODEL+"-contact-regression.pt"),
        driver=dict(python_executable="/engineering/runtime/bin/python", python_sha256="0"*64,
            python_version="3.12.0", module_root="/engineering/source", implementation_files=[dict(
                module="gene_annotation_episode."+name, sha256="2"*64)
                for name in ("esm_gene_embedding_worker","esm_gene_embedding_contracts")], dependencies=[
                dict(distribution=name, version="engineering-only", package_root="/engineering/site/"+module,
                    files=[pin("/engineering/site/"+module+"/__init__.py")])
                for name,module in (("torch","torch"),("fair-esm","esm"))]))


def supplied(raw=RAW):
    sha = hashlib.sha256(raw).hexdigest()
    return contracts.read_esm_protein_fasta(raw, file=dict(artifact_ref="artifact_"+sha,
        sha256=sha, size_bytes=len(raw), format="fasta"), source_ref=None)


def parameters():
    return dict(layer=6, batch_size=2, max_sequence_length=4,
        protein_pooling=contracts.PROTEIN_POOLING, gene_pooling=contracts.GENE_POOLING)


def genes():
    iso = lambda record, label: dict(record_ordinal=record, protein_id="protein:"+str(record), isoform_id=label)
    return [dict(gene_id="same_gene", isoforms=[iso(0,"same_isoform"),iso(1,"same_isoform"),
        iso(2,"long"),iso(3,"lowercase"),iso(99,"missing")]),
        dict(gene_id="same_gene", isoforms=[iso(0,"repeat"),iso(0,"repeat")]),
        dict(gene_id="explicit_empty_gene", isoforms=[])]


def selection(*, selected=None, components=None):
    return dict(version=contracts.SELECTION_VERSION, **{kind:dict(row_ordinals=deepcopy(selected),
        component_indices=deepcopy(components), offset=0, limit=1000)
        for kind in ("residues","proteins","isoforms","genes")})


def document():
    """Independent supplied values: token means2,5; gene means3.5,2."""
    data = supplied()
    proteins = []
    for index,row in enumerate(data["records"]):
        status = ["available","available","length_filtered","invalid","unrequested"][index]
        matrices = [[[1.0]*320,[3.0]*320],[[5.0]*320]][index] if index < 2 else None
        vector = [[2.0]*320,[5.0]*320][index] if index < 2 else None
        issues = [[],[],["maximum_sequence_length_exceeded"],
            ["unsupported_model_token_preserved_without_normalization"],[]][index]
        proteins.append(dict(protein_ordinal=index, raw_header=row["raw_header"],sequence=row["sequence"],
            status=status,model_token_count=[2,1,None,None,None][index],residue_vectors=matrices,mean_vector=vector,issues=issues))
    isoforms = []
    for gene_ordinal,gene in enumerate(genes()):
        for within,assignment in enumerate(gene["isoforms"]):
            record = assignment["record_ordinal"]
            protein = proteins[record] if record < len(proteins) else None
            isoforms.append(dict(isoform_ordinal=len(isoforms),gene_ordinal=gene_ordinal,ordinal_within_gene=within,
                **assignment,status="available" if record in (0,1) else "unavailable",
                mean_vector=deepcopy(protein["mean_vector"]) if protein else None))
    return dict(version=contracts.DOCUMENT_VERSION,input=data,genes=genes(),parameters=parameters(),deployment=deployment(),
        observed_model=dict(model_name=contracts.MODEL,layer_count=6,embedding_dimension=320,torch_version="engineering-only",
            esm_version="engineering-only",parameter_dtype="torch.float32",device="cpu",torch_threads=1,
            alphabet_tokens=["<cls>","<pad>","<eos>","A","C","D","E"],
            prepend_bos=True,append_eos=True),proteins=proteins,isoforms=isoforms,gene_rows=[
            dict(gene_ordinal=0,gene_id="same_gene",isoform_ordinals=[0,1,2,3,4],successful_isoform_ordinals=[0,1],mean_vector=[3.5]*320,status="available"),
            dict(gene_ordinal=1,gene_id="same_gene",isoform_ordinals=[5,6],successful_isoform_ordinals=[5,6],mean_vector=[2.0]*320,status="available"),
            dict(gene_ordinal=2,gene_id="explicit_empty_gene",isoform_ordinals=[],successful_isoform_ordinals=[],mean_vector=None,status="unavailable")],
        execution=dict(state="partial",model_load="completed",attempts=1,model_forward_calls=1,runtime_verified=True,failure=None))


@pytest.mark.parametrize("kind",["Arguments","Selection","Input","Deployment","Request","WorkerResult","Document","Value","Return"])
def test_all_closed_schemas_are_valid_202012(kind):
    Draft202012Validator.check_schema(contracts.esm_gene_embedding_schema(kind))


def test_supplied_bytes_headers_case_duplicates_and_original_offsets_are_preserved():
    value = supplied()
    assert bytes.fromhex(value["raw_hex"]) == RAW
    assert value["source_ref"] is None and value["record_count"] == 5
    assert [r["record_ordinal"] for r in value["records"]] == [0,1,2,3,4]
    assert [r["raw_header"] for r in value["records"]][:2] == ["same header"]*2
    assert value["records"][3]["sequence"] == "ac"
    first = value["records"][0]
    assert RAW[first["header_byte_start"]:first["header_byte_end"]] == b">same header"
    segment = first["sequence_segments"][0]
    assert RAW[segment["byte_start"]:segment["byte_end"]] == b"AC"


@pytest.mark.parametrize("raw",[b"\xff",b">a\nA\xff"])
def test_invalid_utf8_does_not_manufacture_known_zero_protein_population(raw):
    value = supplied(raw)
    assert value["record_count"] is None and value["catalog_complete"] is False
    assert value["issues"] == ["invalid_utf8"]


def test_empty_and_malformed_supplied_records_remain_occurrences():
    value = supplied(b">\n>a\n>ok\nA\n")
    assert value["record_count"] == 3
    assert [r["status"] for r in value["records"]] == ["malformed","malformed","available"]
    assert value["records"][0]["issues"] == ["empty_header","empty_sequence"]


def test_literal_native_document_preserves_all_gene_isoform_and_filter_populations():
    result = contracts.validate_esm_embedding_document(document())
    assert [g["gene_id"] for g in result["gene_rows"]] == ["same_gene","same_gene","explicit_empty_gene"]
    assert len(result["isoforms"]) == 7
    assert result["gene_rows"][0]["successful_isoform_ordinals"] == [0,1]
    assert result["gene_rows"][1]["successful_isoform_ordinals"] == [5,6]
    assert [p["status"] for p in result["proteins"]] == ["available","available","length_filtered","invalid","unrequested"]
    assert result["gene_rows"][2]["mean_vector"] is None


def test_projection_copies_ordered_native_and_derived_values_without_inference(monkeypatch):
    monkeypatch.setattr(worker,"run_esm_gene_embedding_request",lambda *a,**k:pytest.fail("no native worker"))
    monkeypatch.setattr(worker,"_infer",lambda *a,**k:pytest.fail("no model inference"))
    selected = selection(components=[3,0])
    selected["genes"].update(row_ordinals=[1,0],offset=1,limit=1)
    value = contracts.select_esm_embedding_values(document(),selected)
    assert value["residues"]["population_count"] == 3
    assert value["proteins"]["population_count"] == 5
    assert value["isoforms"]["population_count"] == 7
    assert value["genes"]["selected_count"] == 2 and value["genes"]["returned_count"] == 1
    assert value["genes"]["rows"][0]["gene_ordinal"] == 0
    assert value["genes"]["rows"][0]["values"] == [3.5,3.5]
    assert value["context"]["unavailable_requested_protein_ordinals"] == [99]
    assert contracts.validate_esm_embedding_value(value) == value


def test_empty_views_keep_model_pooling_input_and_full_gene_population_qualifications():
    value = contracts.select_esm_embedding_values(document(),selection(selected=[],components=[]))
    assert all(value[k]["rows"] == [] for k in ("residues","proteins","isoforms","genes"))
    assert value["context"]["supplied_gene_occurrence_count"] == 3
    assert value["context"]["supplied_isoform_occurrence_count"] == 7
    assert value["context"]["gene_populations"][0]["successful_isoform_ordinals"] == [0,1]
    assert value["context"]["parameters"]["gene_pooling"] == contracts.GENE_POOLING
    assert value["context"]["biological_isoform_population_completeness"] == "unknown"
    assert "not_function_probability" in value["context"]["quantity_meaning"]


@pytest.mark.parametrize("change",["raw_bytes","file_id","catalog","header","sequence","protein_id","dimension",
    "isoform_order","gene_members","gene_id","successful_members","missing_vector","token_count","zero_filter","omitted_header"])
def test_contradictory_raw_membership_shape_and_population_joins_rejected(change):
    value = document()
    if change=="raw_bytes": value["input"]["raw_hex"]="00"
    elif change=="file_id": value["input"]["file"]["artifact_ref"]="artifact_"+"0"*64
    elif change=="catalog": value["input"]["catalog_complete"]=False;value["input"]["record_count"]=None
    elif change=="header": value["input"]["records"][0]["raw_header"]="changed"
    elif change=="sequence": value["proteins"][0]["sequence"]="CA"
    elif change=="protein_id": value["isoforms"][0]["protein_id"]="other"
    elif change=="dimension": value["proteins"][0]["mean_vector"].pop()
    elif change=="isoform_order": value["isoforms"][0],value["isoforms"][1]=value["isoforms"][1],value["isoforms"][0]
    elif change=="gene_members": value["gene_rows"][0]["isoform_ordinals"]=[0,1]
    elif change=="gene_id": value["gene_rows"][1]["gene_id"]="deduplicated"
    elif change=="successful_members": value["gene_rows"][0]["successful_isoform_ordinals"]=[1,0]
    elif change=="missing_vector": value["proteins"][0]["mean_vector"]=None
    elif change=="token_count": value["proteins"][0]["model_token_count"]=3
    elif change=="omitted_header":
        value["input"]["records"].pop();value["input"]["record_count"]-=1;value["proteins"].pop()
    else: value["proteins"][0].update(status="length_filtered",model_token_count=None,residue_vectors=None,mean_vector=None)
    with pytest.raises(Exception): contracts.validate_esm_embedding_document(value)


@pytest.mark.parametrize("change",["layer","device","model","pooling","bool_batch","float_batch","missing_runtime_dependency","relative_checkpoint"])
def test_only_explicit_selected_cpu_profile_and_pooling_are_admitted(change):
    value=dict(version=contracts.REQUEST_VERSION,input=dict(path="/engineering/input.fa",file=supplied()["file"],source_ref=None),
        genes=genes(),parameters=parameters(),deployment=deployment())
    if change=="layer":value["parameters"]["layer"]=5
    elif change=="device":value["deployment"]["device"]="cuda:0"
    elif change=="model":value["deployment"]["model_name"]="esm2_t33_650M_UR50D"
    elif change=="pooling":value["parameters"]["gene_pooling"]="all_isoforms_including_failures"
    elif change=="bool_batch":value["parameters"]["batch_size"]=True
    elif change=="float_batch":value["parameters"]["batch_size"]=2.0
    elif change=="missing_runtime_dependency":value["deployment"]["driver"]["dependencies"].pop()
    else:value["deployment"]["checkpoint"]["path"]="models/model.pt"
    with pytest.raises(Exception):contracts.validate_esm_worker_request(value)


def test_nonfinite_native_cells_stay_literals_and_are_never_zero_coerced():
    value=document();p=value["proteins"][0];p["residue_vectors"][0][0]="NaN";p["mean_vector"][0]="NaN";p["status"]="nonfinite"
    for i in (0,5,6):value["isoforms"][i].update(status="nonfinite",mean_vector=deepcopy(p["mean_vector"]))
    for i in (0,1):value["gene_rows"][i]["mean_vector"][0]="NaN";value["gene_rows"][i]["status"]="nonfinite"
    output=contracts.select_esm_embedding_values(value,selection(components=[0]))
    assert output["proteins"]["rows"][0]["values"] == ["NaN"]
    assert output["genes"]["rows"][0]["values"] == ["NaN"]
    assert contracts.validate_esm_embedding_value(output)==output


def test_only_outer_return_source_is_a_semantic_reference():
    schema=contracts.esm_gene_embedding_schema("Return")
    def refs(node,path=()):
        if isinstance(node,dict):
            if node.get("format")=="reference":yield path
            for k,v in node.items():yield from refs(v,path+(k,))
        elif isinstance(node,list):
            for i,v in enumerate(node):yield from refs(v,path+(i,))
    assert list(refs(schema)) == [("properties","source_ref")]
    # Syntax-only reference fixture: this creates no Store record or custody.
    returned=contracts.project_esm_embedding_return(document(),selection(selected=[]),"source_"+"a"*24)
    assert contracts.validate_esm_embedding_return(returned)==returned


def test_bad_input_bytes_fail_before_runtime_or_model_and_attempt_never_restarts(tmp_path,monkeypatch):
    path=tmp_path/"input.fa";path.write_bytes(b"substituted bytes")
    request=dict(version=contracts.REQUEST_VERSION,input=dict(path=str(path),file=supplied()["file"],source_ref=None),
        genes=genes(),parameters=parameters(),deployment=deployment())
    monkeypatch.setattr(worker,"verify_driver_runtime",lambda *a:pytest.fail("no runtime/model before byte binding"))
    with pytest.raises(ValueError,match="file_bytes_conflict"):
        worker.run_esm_gene_embedding_request(request,output_directory=tmp_path)
    assert (tmp_path/"esm-gene-embeddings/request.json").is_file()
    with pytest.raises(FileExistsError):worker.run_esm_gene_embedding_request(request,output_directory=tmp_path)


def test_unavailable_runtime_retains_all_occurrences_without_model_or_fake_vector_artifact(tmp_path,monkeypatch):
    path=tmp_path/"input.fa";path.write_bytes(RAW)
    request=dict(version=contracts.REQUEST_VERSION,input=dict(path=str(path),file=supplied()["file"],source_ref=None),
        genes=genes(),parameters=parameters(),deployment=deployment())
    def unavailable(*args):raise ValueError("engineering_missing_runtime")
    monkeypatch.setattr(worker,"verify_driver_runtime",unavailable)
    monkeypatch.setattr(worker,"_infer",lambda *a:pytest.fail("no model for unavailable runtime"))
    result=worker.run_esm_gene_embedding_request(request,output_directory=tmp_path)
    data=json.loads((tmp_path/result["result_document_file"]["path"]).read_text())
    assert result["vector_file"] is None
    assert data["observed_model"] is None and data["execution"]["model_forward_calls"]==0
    assert data["execution"]["state"]=="failed" and data["execution"]["runtime_verified"] is False
    assert len(data["proteins"])==5 and len(data["isoforms"])==7 and len(data["gene_rows"])==3
    assert all(r["mean_vector"] is None for r in data["gene_rows"])
    assert contracts.validate_esm_worker_result(result,request=request,document=data)==result


def test_oom_conversion_failure_has_no_single_sequence_retry_or_fabricated_outputs():
    data=document();calls=[];progress=[]
    for p in data["proteins"][:2]:p.update(status="failed",model_token_count=None,residue_vectors=None,mean_vector=None,issues=["model_unavailable"])
    data["execution"].update(model_forward_calls=0,failure=None)
    def converter(batch):calls.append(batch);raise RuntimeError("out of memory engineering control")
    alphabet=SimpleNamespace(standard_toks=list("ACDE"),get_batch_converter=lambda:converter)
    worker._infer(data,None,alphabet,None,{},lambda ordinals:progress.append(ordinals))
    assert len(calls)==1 and len(progress)==1
    assert data["execution"]["model_forward_calls"]==0
    assert all(p["status"]=="failed" and p["mean_vector"] is None for p in data["proteins"][:2])
    assert data["execution"]["failure"]==dict(code="native_batch_failed",exception_type="RuntimeError")


@pytest.mark.parametrize("arguments",[[],["relative","relative"],["/one/request.json","/two/result.json"]])
def test_worker_cli_rejects_wrong_ports_before_file_or_model_access(arguments,monkeypatch):
    monkeypatch.setattr(worker,"run_esm_gene_embedding_request",lambda *a,**k:pytest.fail("invalid CLI must not dispatch"))
    with pytest.raises(ValueError):worker.main(arguments)


def test_worker_cli_envelope_delegates_exact_selected_request_without_native_claim(tmp_path,monkeypatch):
    request=tmp_path/"worker-request.json";output=tmp_path/"worker-result.json"
    supplied_request={"engineering":"CLI delegation only; no inference"}
    request.write_text(json.dumps(dict(operation="esm_gene_embedding",arguments=dict(request=supplied_request))))
    calls=[]
    def dispatch(value,*,output_directory):
        calls.append((value,output_directory));return {"engineering_result":"not a native ESM result"}
    monkeypatch.setattr(worker,"run_esm_gene_embedding_request",dispatch)
    assert worker.main([str(request),str(output)])==0
    assert calls==[(supplied_request,tmp_path)]
    assert json.loads(output.read_text())=={"engineering_result":"not a native ESM result"}
