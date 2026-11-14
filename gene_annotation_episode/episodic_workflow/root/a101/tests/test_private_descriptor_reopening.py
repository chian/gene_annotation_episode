"""Reopen literal private descriptors against original offline caller resources."""
from copy import deepcopy
import pytest

from .test_actual_private_registry import constructed, module


def compose(constructed,descriptors,role_credit_bindings=None):
    store,host,registry,bindings,literature=constructed
    return module('episode_composition').compose_episode_bindings(bindings[0].services,
        store=store,journal=host.journal,execution_backend=None,
        descriptors=descriptors,job_episodes=None,resource_estimator=None,
        role_credit_bindings=role_credit_bindings or {},directory=host.directory,
        tool_registry=host.tools)


def test_original_frozen_science_and_every_private_literature_descriptor_reopen(constructed):
    store,host,_,bindings,literature=constructed
    original=(bindings[0],*literature)
    descriptors=[binding.as_record() for binding in original]
    reopened=compose(constructed,descriptors)
    assert [binding.as_record() for binding in reopened.bindings]==descriptors
    assert [type(binding) for binding in reopened.bindings]==[type(binding) for binding in original]
    assert all(binding.binding_path==record['binding_id'] for binding,record in zip(reopened.bindings,descriptors))
    assert reopened.progress_provider is None
    assert store.db.execute('SELECT COUNT(*) FROM runtime_actions').fetchone()[0]==0


def test_original_api_execution_descriptors_reopen_with_explicit_own_credit(constructed):
    store,_,_,bindings,_=constructed
    original=[binding for binding in bindings if type(binding).__name__=='ExecutionEpisode']
    descriptors=[binding.as_record() for binding in original]
    credit={role:{'definition':{'version':'explicit-construction-credit'},'project':binding.project_credit}
        for binding in original for role in binding.roles}
    reopened=compose(constructed,descriptors,credit)
    assert [binding.as_record() for binding in reopened.bindings]==descriptors
    assert [type(binding) for binding in reopened.bindings]==[type(binding) for binding in original]
    assert len(reopened.resource_capabilities)==1
    assert reopened.resource_capabilities[0]['resource_id']=='original-api'
    assert store.db.execute('SELECT COUNT(*) FROM tool_operations').fetchone()[0]==0


@pytest.mark.parametrize('change',['hash','unknown_path','configuration'])
def test_reopen_rejects_changed_private_descriptor_without_identity_relabel(constructed,change):
    *_,literature=constructed
    descriptor=deepcopy(literature[0].as_record())
    if change=='hash':descriptor['implementation_sha256']='0'*64
    elif change=='unknown_path':descriptor['binding_id']='foreign/unknown_episode'
    else:descriptor['configuration']['unrecognized_original_operand']=True
    with pytest.raises(module('method_loop.durable').DurableExecutionError):
        compose(constructed,[descriptor])


def test_execution_reopen_requires_original_explicit_credit_projector(constructed):
    _,_,_,bindings,_=constructed
    binding=next(binding for binding in bindings if type(binding).__name__=='ExecutionEpisode')
    with pytest.raises(module('method_loop.durable').DurableExecutionError):
        compose(constructed,[binding.as_record()])


def test_current_private_homology_resource_descriptor_reopens_exact_role_family(constructed,tmp_path):
    store,host,_,bindings,_=constructed
    policy=module('local_jobs').LocalJobPolicy(128*1024**2,4*1024**2)
    jobs_module=module('homology_jobs')
    executable=tmp_path/'unexecuted-fixture'
    executable.write_text('synthetic executable identity; never launched\n')
    database=tmp_path/'reference.faa'
    database.write_text('>synthetic\nMA\n')
    jobs=jobs_module.HomologyJobs.create(tmp_path/'homology-registry',
        executable=jobs_module.FileAsset(executable,jobs_module.digest(executable)),
        reference_database=jobs_module.FileAsset(database,jobs_module.digest(database)),
        policy=policy,max_cpu=1)
    def credit(*args,**kwargs):
        return 0
    try:
        family=module('homology_service_setup').create_homology_bindings(jobs,
            parser_policy=policy,credit_projector=credit,
            credit_binding={'version':'original-test-operational-credit'},
            monitoring_projector=credit,
            monitoring_binding={'version':'original-test-monitoring-credit'})
        adapter=module('a101_homology_resource_adapter').HomologyResourceAdapter(
            family,store,host.journal)
        original=module('scientific_process.resource_work_submission.episode').ResourceEpisode(
            bindings[0].services,resource_adapters=[adapter])
        descriptor=original.as_record()
        assert descriptor['configuration']['resource_adapters'][0]['version']=='homology_resource_adapter_v2'
        reopened=module('episode_composition').compose_episode_bindings(bindings[0].services,
            store=store,journal=host.journal,execution_backend=None,
            descriptors=[descriptor],job_episodes=family,resource_estimator=None,
            role_credit_bindings={'launch':{'definition':{'version':'original-test-operational-credit'},
                'project':credit}},directory=host.directory,tool_registry=host.tools)
        assert [value.as_record() for value in reopened.bindings]==[descriptor]
        assert len(reopened.resource_capabilities)==1
        assert reopened.resource_capabilities[0]['resource_id']==adapter.resource_id
        assert set(next(iter(reopened.bindings[0].adapters.values())).homology)=={
            'job_launch','job_monitor','job_results'}
        assert jobs.db.execute('SELECT COUNT(*) FROM orders').fetchone()[0]==0
    finally:
        jobs.close()
