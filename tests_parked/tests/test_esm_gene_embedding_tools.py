"""ESM configuration and actual current-action admission controls.

Software declarations are explicitly nonexistent engineering metadata. These
tests execute no ESM inference and manufacture no producer, handle or Source
result. Positive model/publication proof requires selected physical material.
"""
import asyncio
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gene_annotation_episode import esm_gene_embedding_contracts as contracts
from gene_annotation_episode import esm_gene_embedding_tools as host
from gene_annotation_episode import esm_gene_embedding_publication as publication
from gene_annotation_episode.episodic_workflow.root.episode_return_records import EpisodeReturnRecords
from gene_annotation_episode.execution_contracts import digest
from gene_annotation_episode.episodic_workflow.root.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.molecular_measurement_tools import (
    MolecularOperationUnpublished, _publication_profile, _recorded_molecular_action_details,
)
from gene_annotation_episode.episodic_workflow.root.task_action_units import ActionFailure
from gene_annotation_episode.episodic_workflow.root.runtime import Workflow
from gene_annotation_episode.episodic_workflow.root.workflow_values import _compile_form
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.root.tool_registry import ToolRegistry
from test_esm_gene_embeddings import RAW, deployment, document, genes, parameters, selection, supplied
from tests.test_runtime import ScriptedProvider
from tests.test_vcf_result_workflow import _single_saved_result_controller, _tables, _zero


POLICY = dict(memory_bytes=20 * 1024 ** 3, scratch_bytes=4 * 1024 ** 3)
QUESTION = "Return selected literal ESM vectors for the supplied protein occurrences, preserving missing, filtered and failed populations."


def _forbidden(*args,**kwargs):
    raise AssertionError("engineering admission control attempted bytes, native work or inference")


def _environment(resource_id="ordinary"):
    return dict(operation=contracts.TOOL,resource_id=resource_id,deployment=deployment())


def _configuration(tmp_path,*,native=True,stored=True):
    resource = dict(kind="local",workspace=str(tmp_path/"workspace"),policy=deepcopy(POLICY))
    result = host.normalize_esm_gene_embedding_configuration({"ordinary":resource},
        [_environment()] if native else [],policy=POLICY)
    result["stored_reads"] = stored
    return result


def _arguments(reference,namespace="artifact"):
    return dict(mode="embed",input=dict(reference=reference,namespace=namespace),genes=genes(),
        model_name=contracts.MODEL,parameters=parameters(),selection=selection(selected=[],components=[]))


@contextmanager
def _owned(tmp_path,monkeypatch,*,namespace="artifact"):
    """Real Store/Factory/Workflow authority; no model or native response fake."""
    with Store(tmp_path/"store") as store:
        store.create_problem(raw_sequence="ACD",molecule="protein")
        supplied = store.register_material(data=RAW,name="explicit engineering protein FASTA",use="evidence")
        source = store.get(supplied["source_ref"])
        reference = source["id"] if namespace == "source" else source["artifact_ref"]
        workspace = tmp_path/"workspace";workspace.mkdir()
        factory = ExecutionServiceFactory({"ordinary":dict(kind="local",workspace=str(workspace),policy=deepcopy(POLICY))},
            {},2,.25,.5,esm_gene_embedding_environments=(_environment(),),esm_gene_embedding_stored_reads=True)
        registry = ToolRegistry(store,job_limits=deepcopy(POLICY))
        factory.configure_tool_registry(registry)
        application = factory(store,run_id="esm-admission-engineering",directory=tmp_path/"run",tool_registry=registry)
        flow = Workflow(store,registry,ScriptedProvider([]),tmp_path/"run","esm-admission-engineering",
            _single_saved_result_controller,_zero,project_child_credit=_zero,root_role="improvement",
            episode_binding_descriptors=application.episode_binding_descriptors,
            role_credit_bindings=application.role_credit_bindings,job_progress_provider=application.job_progress_provider,
            episode_record_receipts=True,initial_known_record_refs=[reference])
        caller = flow.build("improvement","caller",QUESTION,store.validate_scope())
        monkeypatch.setattr(registry.clients,"_http",_forbidden)
        monkeypatch.setattr(registry,"_sequence_worker_async",_forbidden)
        yield SimpleNamespace(store=store,registry=registry,flow=flow,caller=caller,reference=reference,
            source=source,input_ref=source["artifact_ref"],namespace=namespace,factory=factory)


def _dispatch(value,arguments,index):
    action = dict(kind="tool",tool=contracts.TOOL,arguments=deepcopy(arguments))
    asyncio.run(value.caller.source.execute(action,index))
    row = value.flow.journal.row("runtime_actions",value.caller.source.episode_id,index)
    assert json.loads(row["action"]) == action and row["result"] is not None
    return json.loads(row["result"])


@pytest.mark.parametrize("native,stored,expected",[(False,False,set()),(False,True,{"read_stored"}),
    (True,False,{"embed"}),(True,True,{"embed","read_stored"})])
def test_only_explicitly_configured_modes_are_advertised(tmp_path,native,stored,expected):
    configuration = _configuration(tmp_path,native=native,stored=stored)
    before = deepcopy(configuration)
    info = host.esm_gene_embedding_tool_contract(configuration)
    assert configuration == before
    if not expected:assert info is None
    else:
        assert {b["properties"]["mode"]["const"] for b in info["input_schema"]["oneOf"]} == expected
        assert info["resources"] == "local" and info["invocation_route"] == {"kind":"direct"}


def test_public_argument_schema_contains_no_physical_runtime_or_checkpoint_paths(tmp_path):
    info = host.esm_gene_embedding_tool_contract(_configuration(tmp_path))
    def names(node):
        if isinstance(node,dict):
            yield from node.get("properties",{})
            for value in node.values():yield from names(value)
        elif isinstance(node,list):
            for value in node:yield from names(value)
    assert not set(names(info["input_schema"])) & {"path","checkpoint","regression_checkpoint","driver","python_executable","module_root","sha256"}
    assert "not function probabilities" in info["instructions"]


def test_configuration_and_worker_pins_are_metadata_only_exact_and_detached(tmp_path,monkeypatch):
    selected = _configuration(tmp_path)
    monkeypatch.setattr(Path,"open",_forbidden)
    assert host.validate_esm_gene_embedding_configuration(selected) == selected
    request = dict(version=contracts.REQUEST_VERSION,input=dict(path="/engineering/input.fa",
        file=dict(artifact_ref="artifact_"+"f"*64,sha256="f"*64,size_bytes=3,format="fasta"),source_ref=None),
        genes=genes(),parameters=parameters(),deployment=deployment())
    pins = host.esm_worker_implementation_files(request)
    assert any(p["path"].endswith("/esm_gene_embedding_worker.py") for p in pins)
    assert any(p["path"].endswith("/esm_gene_embedding_contracts.py") for p in pins)
    assert request["deployment"]["checkpoint"]["path"] in {p["path"] for p in pins}
    environment = host.esm_worker_environment(request,tmp_path/"owned")
    assert environment["PYTHONHOME"] == "/engineering/runtime"
    assert environment["PYTHONPATH"] == "/engineering/source:/engineering/site"
    assert environment["TORCH_HOME"] == str(tmp_path/"owned/cache/torch")
    assert environment["TMPDIR"] == str(tmp_path/"owned/temporary")


def test_contradictory_cross_distribution_pin_is_rejected_without_opening_it(tmp_path):
    request = dict(version=contracts.REQUEST_VERSION,input=dict(path="/engineering/input.fa",
        file=dict(artifact_ref="artifact_"+"f"*64,sha256="f"*64,size_bytes=3,format="fasta"),source_ref=None),
        genes=genes(),parameters=parameters(),deployment=deployment())
    pin = deepcopy(request["deployment"]["driver"]["dependencies"][0]["files"][0]);pin["sha256"]="a"*64
    request["deployment"]["driver"]["dependencies"][1]["files"].append(pin)
    with pytest.raises(Exception,match="selected_pin_conflict"):host.esm_worker_implementation_files(request)


def test_actual_runtime_fact_compiler_accepts_the_complete_controlled_return_source():
    source = contracts.esm_gene_embedding_fact_sources()[contracts.FACT_SOURCE]
    field = deepcopy(source["report_schema"]);field["x-source"] = contracts.FACT_SOURCE
    schema = dict(type="object",properties=dict(embeddings=field),required=["embeddings"],additionalProperties=False)
    assert source["type"] == "array"
    assert _compile_form(json.dumps(schema),contracts.esm_gene_embedding_fact_sources(),include_runtime_sources=False) == schema


def test_shared_producer_profile_names_only_the_actual_embed_producer():
    assert _publication_profile(contracts.TOOL) == (contracts.SOURCE_VERSION,publication.CONTROL_VERSION,
        ("embed",),"esm_gene_embedding_")


def test_real_factory_freezes_declared_selection_without_claiming_software_availability(tmp_path,monkeypatch):
    with _owned(tmp_path,monkeypatch) as value:
        record = value.factory.as_record()
        restored = ExecutionServiceFactory.from_record(record)
        assert restored.as_record() == record
        assert value.registry.catalog()[contracts.TOOL] == host.esm_gene_embedding_tool_contract(value.registry._esm_gene_embedding_configuration)
        assert value.registry._esm_gene_embedding_configuration["resources"][0]["deployment"] == deployment()


def test_unreceived_actual_file_is_denied_before_body_or_worker(tmp_path,monkeypatch):
    with _owned(tmp_path,monkeypatch) as value:
        unreceived = value.store.artifact(b">different unreceived\nACD\n","text/plain")
        assert unreceived not in value.flow.receipts.known(value.caller.source.episode_id)
        monkeypatch.setattr(Store,"get_artifact",_forbidden)
        with pytest.raises(ActionFailure):_dispatch(value,_arguments(unreceived),0)
        row = value.flow.journal.row("runtime_actions",value.caller.source.episode_id,0)
        assert json.loads(row["result"])["record_refs"] == []
        context=EpisodeReturnRecords(value.store,value.flow.run_id,failure_prefix="esm_engineering_").context(value.caller.source.episode_id)
        details=_recorded_molecular_action_details(value.registry,context,_arguments(unreceived),
            f"{value.flow.run_id}:{context.episode_id}:0",contracts.TOOL)
        runtime=json.loads(row["result"])
        assert set(runtime)==set(details["outcome"])|{"pending_work_after_action"}
        from gene_annotation_episode.episodic_workflow.root.wait_events import validate_pending
        pending=runtime["pending_work_after_action"]
        assert validate_pending(pending)==pending and pending["items"]==[]
        assert details["outcome"]=={key:item for key,item in runtime.items() if key!="pending_work_after_action"}
        assert row["credit"] is None


def test_actual_supplied_material_source_cannot_impersonate_an_esm_producer(tmp_path,monkeypatch):
    with _owned(tmp_path,monkeypatch) as value:
        monkeypatch.setattr(Store,"get_artifact",_forbidden)
        with pytest.raises(Exception,match="producer_required"):
            publication._metadata(value.registry,value.source["id"])


@pytest.mark.parametrize("namespace",["artifact","source"])
def test_real_admission_precedes_the_sealed_pending_worker_without_native_execution(tmp_path,monkeypatch,namespace):
    with _owned(tmp_path,monkeypatch,namespace=namespace) as value:
        arguments = _arguments(value.reference,namespace)
        seen=[]
        async def stop(operation,body,*,directory,owned_directory):
            assert operation == host.OPERATION and directory == owned_directory
            seen.append(deepcopy(body["request"]))
            raise MolecularOperationUnpublished("engineering_before_worker")
        monkeypatch.setattr(value.registry,"_sequence_worker_async",stop)
        with pytest.raises(MolecularOperationUnpublished,match="engineering_before_worker"):_dispatch(value,arguments,0)
        assert len(seen)==1 and seen[0]["input"]["file"]["artifact_ref"]==value.input_ref
        assert seen[0]["input"]["source_ref"] == (value.reference if namespace=="source" else None)
        context=EpisodeReturnRecords(value.store,value.flow.run_id,failure_prefix="esm_engineering_").context(value.caller.source.episode_id)
        actual=host._input_decision(value.registry,context,arguments["input"],0)
        key=f"{value.flow.run_id}:{context.episode_id}:0"
        intent=json.loads((value.store.path/"cache/molecular-measurements"/digest(key)/"esm-gene-embedding-intent.json").read_bytes())
        assert intent["input_decision_admission"]==actual
        assert value.store.db.execute("SELECT count(*) FROM tool_operations WHERE name=?",(contracts.TOOL,)).fetchone()[0]==0


@pytest.mark.parametrize("change",["input_file","native_genes","selected_checkpoint"])
def test_pending_intent_substitution_is_denied_without_original_body_or_new_worker(tmp_path,monkeypatch,change):
    with _owned(tmp_path,monkeypatch) as value:
        arguments=_arguments(value.reference)
        async def stop(*args,**kwargs):raise MolecularOperationUnpublished("engineering_before_worker")
        monkeypatch.setattr(value.registry,"_sequence_worker_async",stop)
        with pytest.raises(MolecularOperationUnpublished):_dispatch(value,arguments,0)
        key=f"{value.flow.run_id}:{value.caller.source.episode_id}:0"
        path=value.store.path/"cache/molecular-measurements"/digest(key)/"esm-gene-embedding-intent.json"
        intent=json.loads(path.read_bytes())
        if change=="native_genes":intent["request"]["genes"][0]["gene_id"]="substituted"
        elif change=="selected_checkpoint":
            intent["selected_resource"]["deployment"]["checkpoint"]["sha256"]="d"*64
            intent["request"]["deployment"]=deepcopy(intent["selected_resource"]["deployment"])
        else:
            intent["input"]["file"]["artifact_ref"]="artifact_"+"e"*64
            intent["input"]["file"]["sha256"]="e"*64
            intent["request"]["input"]=deepcopy(intent["input"])
        mode=path.stat().st_mode&0o777;path.chmod(mode|0o200)
        try:path.write_text(json.dumps(intent))
        finally:path.chmod(mode)
        before=_tables(value.store)
        monkeypatch.setattr(Store,"get_artifact",_forbidden)
        monkeypatch.setattr(value.registry,"_sequence_worker_async",_forbidden)
        with pytest.raises(MolecularOperationUnpublished,match="original_action_unpublished"):_dispatch(value,arguments,0)
        after=_tables(value.store)
        changed_tables=[name for name in before if before[name]!=after[name]]
        assert set(before)==set(after) and changed_tables==["runtime_actions"]
        assert len(before["runtime_actions"])==len(after["runtime_actions"])==1
        columns=[row[1] for row in value.store.db.execute("PRAGMA table_info(runtime_actions)")]
        old=dict(zip(columns,before["runtime_actions"][0]));new=dict(zip(columns,after["runtime_actions"][0]))
        changed_columns=[name for name in columns if old[name]!=new[name]]
        assert changed_columns==["timing"]
        assert new["run_id"]==value.flow.run_id and new["episode_id"]==value.caller.source.episode_id
        assert new["decision_index"]==0 and new["result"] is new["credit"] is None
        old_timing,new_timing=json.loads(old["timing"]),json.loads(new["timing"])
        assert set(old_timing)==set(new_timing)=={"version","intervals","measured_elapsed_seconds","unmeasured_ended_intervals"}
        assert old_timing["version"]==new_timing["version"]=="measured_episode_execution_intervals_v1"
        assert old_timing["unmeasured_ended_intervals"]==new_timing["unmeasured_ended_intervals"]==0
        assert len(old_timing["intervals"])==1 and new_timing["intervals"][:-1]==old_timing["intervals"]
        assert len(new_timing["intervals"])==2
        span=new_timing["intervals"][-1]
        assert set(span)=={"state","owner","started_at","started_monotonic_ns","ended_at","elapsed_seconds","exception_type"}
        assert span["state"]=="raised" and span["exception_type"]=="MolecularOperationUnpublished"
        assert span["owner"]==old_timing["intervals"][0]["owner"]
        assert type(span["started_monotonic_ns"]) is int and span["started_monotonic_ns"]>old_timing["intervals"][0]["started_monotonic_ns"]
        from datetime import datetime
        assert all(datetime.fromisoformat(span[name]).tzinfo is not None for name in ("started_at","ended_at"))
        assert span["elapsed_seconds"]>=0
        assert new_timing["measured_elapsed_seconds"]==old_timing["measured_elapsed_seconds"]+span["elapsed_seconds"]
        assert not list(path.parent.rglob("native-handle.json"))
        (tmp_path/"pending_retry_changes.json").write_text(json.dumps(dict(change=change,
            changed_tables=changed_tables,changed_columns=changed_columns,
            before_timing=old_timing,after_timing=new_timing),indent=2)+"\n")


def _fact_schema():
    field=contracts.esm_gene_embedding_fact_sources()[contracts.FACT_SOURCE]["report_schema"]
    return dict(type="object",properties=dict(embeddings=field),required=["embeddings"],additionalProperties=False)


def test_default_factory_record_and_registry_catalog_keep_unconfigured_esm_absent(tmp_path):
    with Store(tmp_path/"store") as store:
        factory=ExecutionServiceFactory({"local":dict(kind="local",workspace=str(tmp_path/"workspace"))},{},2,.25,.5)
        record=factory.as_record()
        assert set(record)=={"version","resources","initial_information","handoff_unit","acquired_record_unit",
            "monitoring_information_unit","log_window_bytes","log_roles","monitor_outcome_page_size"}
        registry=ToolRegistry(store,job_limits=deepcopy(POLICY))
        factory.configure_tool_registry(registry)
        assert registry._esm_gene_embedding_configuration is None and contracts.TOOL not in registry.catalog()
        assert ExecutionServiceFactory.from_record(record).as_record()==record


def test_registered_typed_form_resolves_only_outer_source_and_preserves_literal_identifiers(monkeypatch):
    """DTO-only supplied vectors and reference syntax, not publication custody."""
    from gene_annotation_episode.episodic_workflow.root.communication import validate_form
    from gene_annotation_episode.molecular_result_facts import requested_molecular_fact_fields
    data=document();nested="source_"+"b"*24
    data["input"]["source_ref"]=nested
    data["genes"][0]["gene_id"]=nested;data["gene_rows"][0]["gene_id"]=nested
    public=contracts.project_esm_embedding_return(data,selection(components=[3,0]),"source_"+"a"*24)
    calls=[]
    monkeypatch.setattr(host,"execute_esm_gene_embedding_tool",_forbidden)
    assert requested_molecular_fact_fields(_fact_schema(),fact_source=contracts.FACT_SOURCE)==["embeddings"]
    returned=validate_form({"embeddings":[public]},_fact_schema(),
        lambda reference,namespace:calls.append((reference,namespace)) or reference==public["source_ref"])
    assert returned=={"embeddings":[public]} and calls==[(public["source_ref"],"source")]
    assert returned["embeddings"][0]["context"]["input_source_ref"]==nested
    assert returned["embeddings"][0]["genes"]["rows"][0]["gene_id"]==nested


def test_fact_groups_deduplicate_full_source_selection_and_reject_changed_frozen_values():
    from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError
    from gene_annotation_episode.molecular_result_facts import merge_molecular_facts,validate_frozen_molecular_return
    reference="source_"+"a"*24
    first=contracts.project_esm_embedding_return(document(),selection(components=[0]),reference)
    second=contracts.project_esm_embedding_return(document(),selection(selected=[],components=[]),reference)
    assert merge_molecular_facts([first,second],[deepcopy(first)],fact_source=contracts.FACT_SOURCE)==[first,second]
    changed=deepcopy(first);changed["genes"]["rows"][0]["values"][0]=9.0
    contracts.validate_esm_embedding_return(changed)
    with pytest.raises(Exception,match="facts_source_conflict"):
        merge_molecular_facts([first],[changed],fact_source=contracts.FACT_SOURCE)
    validate_frozen_molecular_return({"embeddings":[first,second]},_fact_schema(),[first,second],fact_source=contracts.FACT_SOURCE)
    with pytest.raises(ReportBoundaryError,match="Return differs"):
        validate_frozen_molecular_return({"embeddings":[second,first]},_fact_schema(),[first,second],fact_source=contracts.FACT_SOURCE)


@pytest.mark.parametrize("change",["schema","missing_source","bool_count","float_count"])
def test_actual_typed_boundary_denies_changed_schema_missing_grant_and_scalar_substitution(change):
    from gene_annotation_episode.episodic_workflow.root.communication import ReportBoundaryError,validate_form
    schema=_fact_schema()
    value=contracts.project_esm_embedding_return(document(),selection(selected=[]),"source_"+"a"*24)
    resolver=lambda *_:True
    if change=="schema":schema["properties"]["embeddings"]["items"]["properties"]["context"]["properties"]["model_name"]={"const":"other_model"}
    elif change=="missing_source":resolver=lambda *_:False
    elif change=="bool_count":value["context"]["supplied_gene_occurrence_count"]=True
    else:value["context"]["supplied_gene_occurrence_count"]=3.0
    with pytest.raises(ReportBoundaryError):validate_form({"embeddings":[value]},schema,resolver)


@pytest.mark.parametrize("empty",[False,True])
def test_complete_lookup_preserves_literal_headers_and_global_qualifiers_but_hides_declared_custody(empty,monkeypatch):
    from gene_annotation_episode import scientific_process_prompt as prompt
    from gene_annotation_episode import esm_gene_embedding_worker as worker
    data=document();literal="artifact_"+"e"*64+" /supplied/header slot evidence entries library"
    data["input"]=supplied(RAW.replace(b">same header",(">"+literal).encode(),1))
    for row,original in zip(data["proteins"],data["input"]["records"]):row["raw_header"]=original["raw_header"]
    data["input"]["source_ref"]="source_"+"b"*24
    # A caller label that resembles tracking data remains a scientific label.
    data["genes"][0]["gene_id"]=literal;data["gene_rows"][0]["gene_id"]=literal
    public=contracts.project_esm_embedding_return(data,selection(selected=[] if empty else None,components=[3,0]),"source_"+"a"*24)
    monkeypatch.setattr(worker,"_infer",_forbidden)
    monkeypatch.setattr(Path,"open",_forbidden)
    assert prompt._information(public)==public
    from types import MappingProxyType
    def freeze(value):
        if isinstance(value,dict):return MappingProxyType({key:freeze(child) for key,child in value.items()})
        if isinstance(value,list):return tuple(freeze(child) for child in value)
        return value
    assert prompt._selected_molecular_packet(freeze(public))==public
    wire=prompt._lookup(dict(status="completed",result=public,record_refs=[public["source_ref"]],changed_record_refs=[]))
    for token in (public["source_ref"],literal,"successful_isoform_occurrences_only_equal_weight",
            "actual_model_tokens_excluding_bos_eos_padding","biological_isoform_population_completeness","unknown"):
        assert token in wire
    for private in (data["input"]["file"]["artifact_ref"],data["input"]["source_ref"],
            data["deployment"]["checkpoint"]["sha256"],data["deployment"]["checkpoint"]["path"]):
        assert private not in wire
    assert "returned_count" in wire and "input_file_metadata" in wire


def test_owned_worker_selects_declared_runtime_and_pins_before_any_prepare_or_execution(tmp_path,monkeypatch):
    """Engineering pin files exercise dispatch metadata, never an interpreter."""
    import hashlib
    from gene_annotation_episode import molecular_measurement_tools as common
    from gene_annotation_episode import native_lifecycle
    from gene_annotation_episode.local_jobs import LocalJobPolicy
    selected=deployment();driver=selected["driver"]
    def pin(path):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b"engineering pin only; never execute or load\n")
        return dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),size_bytes=path.stat().st_size)
    python=pin(tmp_path/"runtime/bin/python")
    driver.update(python_executable=python["path"],python_sha256=python["sha256"],module_root=str(tmp_path/"source"))
    for item in driver["implementation_files"]:
        item["sha256"]=pin(tmp_path/"source"/(item["module"].replace(".","/")+".py"))["sha256"]
    for item in driver["dependencies"]:
        root=tmp_path/"site"/Path(item["package_root"]).name
        item.update(package_root=str(root),files=[pin(root/"__init__.py")])
    for key in ("checkpoint","regression_checkpoint"):
        selected[key]=pin(tmp_path/"models"/Path(selected[key]["path"]).name)
    original=tmp_path/"input.fa";original.write_bytes(RAW)
    request=dict(version=contracts.REQUEST_VERSION,input=dict(path=str(original),file=supplied()["file"],source_ref=None),
        genes=genes(),parameters=parameters(),deployment=selected)
    owned=tmp_path/"owned";owned.mkdir();calls=[]
    class BeforePrepare(Exception):pass
    def stop(command,**kwargs):
        calls.append((command,kwargs));raise BeforePrepare()
    monkeypatch.setattr(native_lifecycle,"prepare_job",stop)
    monkeypatch.setattr(native_lifecycle,"resume_start",_forbidden)
    monkeypatch.setattr(native_lifecycle,"status",_forbidden)
    monkeypatch.setattr(common,"_molecular_implementation_files",_forbidden)
    with pytest.raises(BeforePrepare):
        common.run_owned_molecular_worker(host.OPERATION,dict(request=request),directory=owned,
            owned_directory=owned,policy=LocalJobPolicy(**POLICY),cancel_event=None)
    frozen=json.loads((owned/"execution-selection.json").read_bytes())
    assert len(calls)==1 and calls[0][0]==frozen["command"]
    assert frozen["python"]=={key:python[key] for key in ("path","sha256")}
    assert frozen["command"]==[python["path"],"-m","gene_annotation_episode.esm_gene_embedding_worker",
        str(owned/"worker-request.json"),str(owned/"worker-result.json")]
    assert frozen["environment"]==host.esm_worker_environment(request,owned)
    assert frozen["implementation_files"]==host.esm_worker_implementation_files(request)
    assert json.loads((owned/"worker-request.json").read_bytes())==dict(operation=host.OPERATION,arguments=dict(request=request))
    assert not (owned/"native-handle.json").exists() and not (owned/"worker-result.json").exists()


def _esm_material_pin(path):
    import hashlib
    path=Path(path);sha=hashlib.sha256()
    with path.open("rb") as stream:
        while block:=stream.read(1024*1024):sha.update(block)
    return dict(path=str(path),sha256=sha.hexdigest(),size_bytes=path.stat().st_size)


def _esm_material_get(client,attempt,directory,label,url,limit,proof,checkpoint):
    """One selected GET; preserve actual native bytes/failure before checks."""
    from gene_annotation_episode.acquisition import AcquisitionError
    from gene_annotation_episode.local_jobs import LocalJobPolicy,check_scratch_budget
    selected=dict(label=label,url=url,method="GET",max_bytes=limit,timeout_seconds=client.timeout,
        automatic_redirects=False,retries=0)
    proof["transfers"].append(dict(selected=selected,state="selected",snapshot=None,failure=None))
    row=proof["transfers"][-1];checkpoint()
    check_scratch_budget(attempt,LocalJobPolicy(**POLICY),additional_bytes=limit)
    snapshot,error=None,None
    try:
        snapshot=client._http("esm-material",url,{},"application/octet-stream",accept="*/*",
            max_bytes=limit,timeout_seconds=client.timeout,follow_redirects=False)
    except AcquisitionError as caught:
        snapshot,error=caught.snapshot,caught
        row["failure"]=dict(code=caught.code,phase=caught.phase,diagnostic=caught.diagnostic)
    except Exception as caught:
        error=caught;row["failure"]=dict(exception_type=type(caught).__name__,message=str(caught))
    if snapshot is not None:
        path=directory/(label+".bin");path.write_bytes(snapshot.content)
        row["snapshot"]=dict(service=snapshot.service,url=snapshot.url,request=snapshot.request,
            retrieved_at=snapshot.retrieved_at,media_type=snapshot.media_type,transport=snapshot.transport,
            body=_esm_material_pin(path))
    row["state"]="captured_failure" if error is not None else "captured_response";checkpoint()
    if error is not None:raise error
    assert snapshot is not None and snapshot.transport["status"]==200
    assert snapshot.transport["body_complete"] is True and snapshot.transport["response_byte_limit"]==limit
    assert snapshot.transport["request"]["url"]==snapshot.transport["effective_url"]==url
    assert snapshot.transport["request_policy"]==dict(timeout_seconds=client.timeout,automatic_redirects=False)
    assert snapshot.transport["retained_body_bytes"]==snapshot.transport["observed_body_bytes"]==len(snapshot.content)
    return path


def _esm_material_command(command,environment,directory,label,proof,checkpoint):
    import subprocess
    from datetime import datetime,timezone
    stdout,stderr=directory/(label+".stdout"),directory/(label+".stderr")
    row=dict(label=label,command=command,started_at=datetime.now(timezone.utc).isoformat(),returncode=None)
    proof["commands"].append(row);checkpoint()
    with stdout.open("wb") as out,stderr.open("wb") as err:
        result=subprocess.run(command,env=environment,cwd=directory,stdout=out,stderr=err,check=False)
    row.update(returncode=result.returncode,finished_at=datetime.now(timezone.utc).isoformat(),
        stdout=_esm_material_pin(stdout),stderr=_esm_material_pin(stderr));checkpoint()
    assert result.returncode==0,(label,result.returncode)


def _esm_material_freeze(root):
    """Close only this new run's acquired software and model material."""
    for path in root.rglob("*"):
        if path.is_file():path.chmod(0o555 if path.stat().st_mode&0o111 else 0o444)
    for path in sorted((p for p in root.rglob("*") if p.is_dir()),key=lambda p:len(p.parts),reverse=True):path.chmod(0o555)
    root.chmod(0o555)


def _esm_material_runtime_preflight(arguments):
    """Executed only in the newly copied selected interpreter, with no model."""
    import hashlib,importlib,importlib.metadata,inspect,json,os,platform,socket,sys
    from pathlib import Path
    def pin(path):
        path=Path(path);sha=hashlib.sha256()
        with path.open("rb") as stream:
            while block:=stream.read(1024*1024):sha.update(block)
        return dict(path=str(path),sha256=sha.hexdigest(),size_bytes=path.stat().st_size)
    def forbidden(*args,**kwargs):raise AssertionError("material preflight forbids network, checkpoint load and inference")
    socket.socket.connect=forbidden;socket.create_connection=forbidden
    socket.getaddrinfo=forbidden;socket.gethostbyname=forbidden;socket.gethostbyaddr=forbidden
    arguments=json.loads(Path(arguments).read_text());source=Path(arguments["source"])
    overlay,base=Path(arguments["overlay"]),Path(arguments["base"])
    output=Path(arguments["output"])
    result=dict(state="started",model_constructed=False,checkpoint_loaded=False,model_forward_calls=0,
        protected_write_attempts=[],coverage_rounds=[])
    output.write_text(json.dumps(result,indent=2)+"\n")
    def checkpoint():output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    if arguments.get("protected_root"):
        import builtins,io
        protected=Path(arguments["protected_root"]).resolve(strict=True)
        def deny_write(value,operation):
            if isinstance(value,int):value=Path("/proc/self/fd")/str(value)
            path=Path(os.fsdecode(value)).resolve()
            if path.is_relative_to(protected):
                result["protected_write_attempts"].append(dict(operation=operation,path=str(path)))
                raise AssertionError("retained material write forbidden: "+operation+" "+str(path))
        def wrap_open(original):
            def opened(file,*args,**kwargs):
                mode=kwargs.get("mode",args[0] if args else "r")
                if any(character in mode for character in "wax+"):deny_write(file,"open")
                return original(file,*args,**kwargs)
            return opened
        builtins.open=wrap_open(builtins.open);io.open=wrap_open(io.open)
        original_open=os.open
        def os_open(path,flags,*args,**kwargs):
            if flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):deny_write(path,"os.open")
            return original_open(path,flags,*args,**kwargs)
        os.open=os_open
        def wrap_mutation(original,name,count):
            def mutated(*args,**kwargs):
                for value in args[:count]:deny_write(value,name)
                return original(*args,**kwargs)
            return mutated
        for name in ("chmod","chown","unlink","remove","mkdir","rmdir","truncate","utime"):
            setattr(os,name,wrap_mutation(getattr(os,name),name,1))
        for name in ("rename","replace","link","symlink"):
            setattr(os,name,wrap_mutation(getattr(os,name),name,2))
    try:
        import torch,esm
        import gene_annotation_episode.esm_gene_embedding_worker
        from gene_annotation_episode.native_atac_differential_software import _source_closure,_PACKAGES,_OPTIONAL
        from gene_annotation_episode.native_atac_differential_contracts import validate_driver_runtime
        from gene_annotation_episode.native_atac_differential_driver import verify_driver_runtime
        assert torch.__version__=="2.6.0+cpu" and esm.__version__=="2.0.0" and torch.version.cuda is None
        assert "weights_only" in inspect.signature(torch.load).parameters
        assert list(inspect.signature(esm.pretrained.load_model_and_alphabet_core).parameters)==[
            "model_name","model_data","regression_data"]
        torch.load=forbidden;torch.hub.load_state_dict_from_url=forbidden
        esm.pretrained.load_model_and_alphabet_core=forbidden
        esm.model.esm2.ESM2.__init__=forbidden
        torch.set_num_threads(1)
        assert torch.get_num_threads()==1
        aliases={"fair-esm":"esm","attrs":"attr","rpds-py":"rpds",
            "jsonschema-specifications":"jsonschema_specifications","python-dateutil":"dateutil"}
        selected={**_PACKAGES,**{name:aliases.get(name,name.replace("-","_")) for name in arguments["distributions"]}}
        if "numpy" in sys.modules:selected["numpy"]="numpy"
        for module in selected.values():importlib.import_module(module)
        selected.update({name:module for name,module in _OPTIONAL.items() if module in sys.modules})
        def binding(name,module_name,distribution=None,loaded_paths=()):
            module=importlib.import_module(module_name)
            distribution=importlib.metadata.distribution(name) if distribution is None else distribution
            root=Path(distribution.locate_file(".")).resolve(strict=True);files=[]
            assert root in (overlay,base)
            for entry in distribution.files or ():
                path=Path(distribution.locate_file(entry))
                if not path.resolve().is_relative_to(root):continue
                if (entry.suffix in (".pyc",".pyo") or "__pycache__" in entry.parts) and str(path.resolve()) not in loaded_paths:continue
                path=path.resolve(strict=True);assert path.is_file();files.append(pin(path))
            assert files and str(Path(module.__file__).resolve()) in {row["path"] for row in files}
            return dict(distribution=name,version=distribution.version,
                package_root=str(Path(module.__file__).resolve().parent),files=sorted(files,key=lambda row:row["path"]))
        dependencies=[binding(name,module_name) for name,module_name in sorted(selected.items())]
        modules=_source_closure(source,["gene_annotation_episode.esm_gene_embedding_worker",
            "gene_annotation_episode.esm_gene_embedding_contracts"])
        driver=validate_driver_runtime(dict(python_executable=sys.executable,python_sha256=pin(sys.executable)["sha256"],
            python_version=platform.python_version(),module_root=str(source),implementation_files=[
                dict(module=name,sha256=pin(path)["sha256"]) for name,path in sorted(modules.items())],dependencies=dependencies),
            required_modules=("gene_annotation_episode.esm_gene_embedding_worker","gene_annotation_episode.esm_gene_embedding_contracts"),
            required_dependencies=("torch","fair-esm"))
        result["initial_driver"]=json.loads(json.dumps(driver));checkpoint()
        installed=list(importlib.metadata.distributions(path=[str(overlay),str(base)]));owners={}
        for distribution in installed:
            root=Path(distribution.locate_file(".")).resolve(strict=True)
            for entry in distribution.files or ():
                path=Path(distribution.locate_file(entry)).resolve()
                if path.is_relative_to(root):owners.setdefault(str(path),{})[str(distribution._path)]=distribution
        for ordinal in range(len(installed)+1):
            dependencies.sort(key=lambda row:(not Path(row["package_root"]).is_relative_to(overlay),row["distribution"]))
            driver["dependencies"]=dependencies;validate_driver_runtime(driver)
            result["candidate_driver"]=json.loads(json.dumps(driver));checkpoint()
            verify_driver_runtime(driver)
            pinned={row["path"] for item in dependencies for row in item["files"]};loaded={}
            for name,module in list(sys.modules.items()):
                filename=getattr(module,"__file__",None)
                if filename and any(Path(filename).resolve().is_relative_to(root) for root in (base,overlay)):
                    loaded[name]=pin(Path(filename).resolve(strict=True))
            missing=[dict(name=name,**row) for name,row in loaded.items() if row["path"] not in pinned]
            coverage=dict(round=ordinal,loaded_files=loaded,missing=missing,ownership=[])
            result["coverage_rounds"].append(coverage);checkpoint()
            if not missing:break
            additions={}
            for item in missing:
                candidates=list(owners.get(item["path"],{}).values())
                declarations=[dict(name=d.metadata["Name"],version=d.version,
                    record=pin(Path(d._path)/"RECORD")) for d in candidates]
                coverage["ownership"].append(dict(module=item["name"],path=item["path"],owners=declarations));checkpoint()
                if len(candidates)!=1:raise ValueError("retained_loaded_file_owner_missing_or_ambiguous")
                owner=candidates[0];name=owner.metadata["Name"].lower().replace("_","-")
                if name in {row["distribution"] for row in dependencies}:
                    raise ValueError("retained_loaded_distribution_shadow_or_record_conflict")
                additions[name]=owner
            for name,owner in sorted(additions.items()):
                dependencies.append(binding(name,aliases.get(name,name.replace("-","_")),owner,
                    {row["path"] for row in loaded.values()}))
        else:raise ValueError("retained_loaded_distribution_closure_not_reached")
        mapped={}
        for line in Path("/proc/self/maps").read_text().splitlines():
            fields=line.split(None,5)
            if len(fields)==6 and fields[5].startswith("/"):
                path=Path(fields[5]).resolve(strict=True)
                if path.is_file():mapped[str(path)]=pin(path)
        inspected=[pin(Path(esm.__file__).parent/relative) for relative in ("pretrained.py","data.py","model/esm2.py")]
        result.update(state="completed",driver=driver,torch_version=torch.__version__,esm_version=esm.__version__,
            device="cpu",torch_threads=torch.get_num_threads(),loaded_distribution_files=loaded,
            mapped_native_files=list(mapped.values()),inspected_api_sources=inspected)
    except BaseException as error:
        result.update(state="failed",failure=dict(exception_type=type(error).__name__,message=str(error)))
        raise
    finally:checkpoint()




def _esm_material_inventory(root):
    import stat
    rows=[]
    for path in [root,*sorted(root.rglob("*"))]:
        mode=path.lstat().st_mode;row=dict(path=str(path.relative_to(root)),mode=mode&0o777)
        if stat.S_ISLNK(mode):row.update(kind="symlink",target=str(path.readlink()))
        elif stat.S_ISDIR(mode):row.update(kind="directory")
        else:
            assert stat.S_ISREG(mode)
            row.update(kind="file",**{key:value for key,value in _esm_material_pin(path).items() if key!="path"})
        rows.append(row)
    return rows


