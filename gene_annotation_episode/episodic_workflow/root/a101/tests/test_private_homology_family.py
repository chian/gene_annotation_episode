"""Offline original Homology resources with all three predefined task owners."""
from contextlib import nullcontext
from importlib import import_module
from types import SimpleNamespace
import pytest

AXIS=__package__.rsplit('.tests',1)[0]
ROLES=('job_launch','job_monitor','job_results')

def module(name):return import_module(AXIS+'.'+name)

@pytest.fixture
def bindings(tmp_path):
    policy=module('local_jobs').LocalJobPolicy(128*1024**2,4*1024**2)
    jobs_module=module('homology_jobs')
    executable=tmp_path/'unexecuted-fixture';executable.write_text('synthetic identity; never executed\n')
    database=tmp_path/'reference.faa';database.write_text('>synthetic\nMA\n')
    jobs=jobs_module.HomologyJobs.create(tmp_path/'jobs',
        executable=jobs_module.FileAsset(executable,jobs_module.digest(executable)),
        reference_database=jobs_module.FileAsset(database,jobs_module.digest(database)),policy=policy,max_cpu=1)
    def operational(*args,**kwargs):return 2
    def monitoring(*args,**kwargs):return 3
    try:
        values=module('homology_service_setup').create_homology_bindings(jobs,parser_policy=policy,
            credit_projector=operational,credit_binding={'version':'original-operational'},
            monitoring_projector=monitoring,monitoring_binding={'version':'original-monitoring'})
        yield values
        assert jobs.db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0
    finally:jobs.close()


def normalized(value):
    name=AXIS+'.homology_binding_family'
    from importlib.util import find_spec
    assert find_spec(name) is not None,'private runtime Homology family adapter is missing'
    return import_module(name).normalize_homology_family(value)


def test_complete_family_keeps_original_three_descriptors_and_credit(bindings):
    family=normalized(bindings)
    assert family.roles==ROLES
    assert family.as_record()['bindings']=={role:bindings[role].as_record() for role in ROLES}
    assert family.fact_sources('scientific_process')=={}
    for role in ROLES:
        assert family.for_role(role) is bindings[role]
        assert family.binding_for(role)==bindings[role].binding_for(role)
        assert family.credit_kind(role)==('monitoring' if role=='job_monitor' else 'operational')
        assert family.instructions(role)==bindings[role].instructions(role)
        assert family.initial_credit(None,role,{},'original-owner','original-run')==(3 if role=='job_monitor' else 2)


@pytest.mark.parametrize('role',ROLES)
def test_singleton_keeps_caller_and_reconstructs_only_predefined_siblings(bindings,role):
    original=bindings[role];family=normalized(original)
    assert family.for_role(role) is original
    assert family.as_record()['bindings']=={name:value.as_record() for name,value in bindings.items()}
    assert normalized(family) is family
    assert family.jobs is original.jobs


def test_incomplete_family_and_unknown_role_are_rejected(bindings):
    family=normalized(bindings)
    with pytest.raises(TypeError,match='complete_private_homology'):
        normalized({'job_launch':bindings['job_launch']})
    with pytest.raises(ValueError,match='unknown_job_episode_role'):
        family.for_role('foreign')
    external=object()
    assert normalized(external) is external


@pytest.mark.parametrize('role',ROLES)
def test_original_runtime_build_selects_each_family_private_task(bindings,role,monkeypatch):
    family=normalized(bindings);runtime=module('runtime')
    Registry=module('episode_bindings').EpisodeBindingRegistry
    monkeypatch.setattr(runtime.Episode,'identity',lambda *args,**kwargs:SimpleNamespace(episode_id='original-owner'))
    monkeypatch.setattr(runtime,'FeedbackEpisode',lambda grain,key,source,*args,**kwargs:source)
    workflow=SimpleNamespace(context=object(),grains={role:object()},inprocess_completion_order=None,
        receipts=None,scientific_process_binding=None,episode_bindings=Registry(()),job_episodes=family,
        contract_information_profile=lambda source:None,binding_context=lambda source:source,specialist=lambda source:None,
        journal=SimpleNamespace(row=lambda *args:None,save=lambda *args:None),run_id='original-run',
        store=SimpleNamespace(transaction=nullcontext,db=SimpleNamespace(execute=lambda *args:None)),
        source_credit_view=lambda source:{'credit':0},expose_assigned_job=lambda source:None,
        receive_tool_attributions=lambda *args,**kwargs:None,archive=SimpleNamespace(store=lambda value:value))
    task=runtime.Workflow.build(workflow,role,'original','Original job task',{})
    assert type(task) is bindings[role].decision_source_type
    assert not isinstance(task,runtime.DecisionSource)


def test_parent_commission_schema_keeps_three_original_roles_and_launch_repair(bindings):
    family=normalized(bindings)
    schemas=family.commission_schemas({'properties':{'kind':{'const':'child'},'goal':{'type':'string'}}})
    assert len(schemas)==4
    roles=[schema['properties']['role']['const'] for schema in schemas]
    assert roles==['job_launch','job_launch','job_monitor','job_results']
    assert schemas[0]['properties']['cpu']['type']=='integer'
    assert schemas[0]['properties']['cpu']['minimum']==1
    assert family.jobs.config==bindings['job_launch'].jobs.config
    assert 'existing_job_ref' in schemas[1]['properties']
    assert 'prior_sample_refs' in schemas[2]['properties']
    assert set(family.describe())==set(ROLES)
