"""Five explicit information/commission contracts; deployment is not inferred."""
from copy import deepcopy
import json

from jsonschema import Draft202012Validator
import pytest

from gene_annotation_episode import native_blast_standard_database_contracts as c
from gene_annotation_episode.native_blast_standard_database_tool_info import standard_blast_database_tool_contracts
from gene_annotation_episode.scientific_tool_library import ScientificToolLibrary
from gene_annotation_episode.api_blast import NCBIBlastService
from gene_annotation_episode.native_blast_tool_info import native_blast_tool_contracts
from gene_annotation_episode.native_blast_database_tool_info import native_blast_database_tool_contracts
from test_native_blast_standard_database_contracts import job_for, forbid_io
from test_native_blast_contracts import job_for as paired_job
from test_native_blast_database_contracts import job_for as native6_job


def bindings():
    return [{'program': p, 'mode': 'database', 'software': job_for(p)['software'],
        'database_manifests': [job_for(p)['databases'][0]['manifest_file']]} for p in c.PROGRAMS]


def test_five_distinct_explicit_hpc_contracts_with_actual_selected_request_shapes(monkeypatch):
    selected = bindings(); original = deepcopy(selected)
    forbid_io(monkeypatch)
    rows = standard_blast_database_tool_contracts(selected,resource_kind='hpc',resource_id='declared-hpc')
    assert len(rows)==5 and {r['name'] for r in rows}=={'native.'+p+'.database' for p in c.PROGRAMS}
    for row,binding in zip(rows,selected):
        assert set(row)=={'name','description','resources','instructions','input_schema','invocation_route'}
        assert row['resources']=='hpc'
        assert row['invocation_route']=={'kind':'commission','routes':[{'entry_role':'launch','resource_id':'declared-hpc','resource_role':'launch_hpc'}]}
        request=c.requested_job_from_standard_blast_database(job_for(binding['program']))
        Draft202012Validator(row['input_schema']).validate(request)
        request['native_blast_standard_database']['software']['sha256']='f'*64
        assert not Draft202012Validator(row['input_schema']).is_valid(request)
        assert 'practical.job.start' in row['instructions']
        assert 'run_standard_blast_database_plan' in row['instructions']
        assert 'does not establish installed software' in row['instructions']
        assert 'not coefficients in that kernel' in row['instructions']
    rows[0]['input_schema'].clear()
    assert selected==original


def test_existing_library_freezes_instructions_and_exact_invocation_contracts(tmp_path):
    rows=standard_blast_database_tool_contracts(bindings(),resource_kind='hpc',resource_id='declared-hpc')
    library=ScientificToolLibrary.freeze(tmp_path/'library',catalog=[],tool_info=True,resource_catalogs={'hpc':rows})
    selection=[{'name':r['name'],'resources':r['resources']} for r in rows]
    info=library.resolve_tool_info(selection)
    assert info==[{k:r[k] for k in ['name','description','resources','instructions']} for r in rows]
    assert library.resolve_invocations(selection)==rows
    assert ScientificToolLibrary(tmp_path/'library').resolve_tool_info(selection)==info


@pytest.mark.parametrize('kind',['local','api','pbs_ssh',None])
def test_other_resource_routes_are_not_advertised(kind):
    with pytest.raises(ValueError,match='explicit_hpc_resource_required'):
        standard_blast_database_tool_contracts(bindings(),resource_kind=kind,resource_id='declared')


def test_binding_closed_and_empty_is_no_capability():
    assert standard_blast_database_tool_contracts([],resource_kind='hpc',resource_id='declared')==[]
    selected=bindings()
    for bad in [[selected[0],selected[0]], [{**selected[0],'installed':True}],
                [{**selected[0],'database_manifests':[]}], [{**selected[0],'database_manifests':[selected[0]['database_manifests'][0]]*2}]]:
        with pytest.raises(ValueError): standard_blast_database_tool_contracts(bad,resource_kind='hpc',resource_id='declared')


def test_existing_paired_native6_and_api_catalog_records_are_byte_equivalent():
    paired=[{'program':p,'mode':'pairwise','software':paired_job(p)['software']} for p in c.PROGRAMS]
    native6=[{'program':p,'mode':'database','software':native6_job(p)['software'],
        'database_manifests':[r['manifest_file'] for r in native6_job(p)['databases']]}
        for p in ['psiblast','deltablast','rpsblast','rpstblastn','blastn_vdb','tblastn_vdb']]
    def old():
        return json.dumps({'paired':native_blast_tool_contracts(paired,resource_kind='local',resource_id='local'),
            'native6':native_blast_database_tool_contracts(native6,resource_kind='hpc',resource_id='hpc'),
            'api_result':NCBIBlastService.result_capabilities(), 'api_request_schema':NCBIBlastService.request_schema},sort_keys=True)
    before=old()
    standard=standard_blast_database_tool_contracts(bindings(),resource_kind='hpc',resource_id='new-hpc')
    assert old()==before
    assert {r['name'] for r in standard}.isdisjoint(r['name'] for r in json.loads(before)['paired'])
