"""Explicit passive identity correlation; synthetic records, never native runs."""
from copy import deepcopy
from importlib import import_module
import pytest
from .retained_blast_manifest_fixtures import database, standard
from .test_private_retained_blast_manifest_identity import _RetainedContracts


def _manifest(family):
    value=database.manifest_for()
    stem='native_blast_'+family
    value['version']=stem+'_producer_manifest_v1'
    value['entry_module']='gene_annotation_episode.'+stem+'_driver'
    names=[stem+'_contracts.py',stem+'_driver.py']+(['blast_program_context.py'] if family=='standard_database' else [])
    value['package_files']=[{'relative_path':'gene_annotation_episode/__init__.py','sha256':'b'*64,'size_bytes':10},
        *[{'relative_path':'gene_annotation_episode/'+name,'sha256':'b'*64,'size_bytes':10} for name in names]]
    return value


def _validators(family):
    contracts=import_module('gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_'+family+'_contracts')
    middle='standard' if family=='standard_database' else 'native'
    return (getattr(contracts,'validate_'+middle+'_blast_database_producer_manifest'),
        getattr(contracts,'validate_retained_'+middle+'_blast_database_producer_manifest'))


@pytest.mark.parametrize('family',('database','standard_database'))
def test_live_validation_rejects_original_identity(monkeypatch,family):
    live,retained=_validators(family);value=_manifest(family);before=deepcopy(value)
    with monkeypatch.context() as guarded:
        database.forbid_io(guarded)
        with pytest.raises(ValueError,match='entry_module.*const'):
            live(value,module_root='/deploy',python_executable='/runtime/python')
        accepted=retained(value,module_root='/deploy',python_executable='/runtime/python')
        assert value==before and accepted==before and accepted is not value


@pytest.mark.parametrize('family',('database','standard_database'))
@pytest.mark.parametrize('changed',('entry_only','roster_only'))
def test_retained_validation_rejects_uncorrelated_identity_and_roster(monkeypatch,family,changed):
    _,retained=_validators(family);value=_manifest(family)
    if changed=='entry_only':
        value['entry_module']=value['entry_module'].replace('gene_annotation_episode.','gene_annotation_episode.episodic_workflow.root.a101.',1)
    else:
        for row in value['package_files']:
            if row['relative_path']!='gene_annotation_episode/__init__.py':
                row['relative_path']=row['relative_path'].replace('gene_annotation_episode/','gene_annotation_episode/episodic_workflow/root/a101/',1)
    before=deepcopy(value)
    with monkeypatch.context() as guarded:
        database.forbid_io(guarded)
        with pytest.raises(ValueError,match='producer_required_package_file_missing'):
            retained(value,module_root='/deploy',python_executable='/runtime/python')
        assert value==before


@pytest.mark.parametrize('family',('database','standard_database'))
def test_retained_manifest_preserves_original_extra_package_file_allowance(monkeypatch,family):
    _,retained=_validators(family);value=_manifest(family)
    value['package_files'].append({'relative_path':'gene_annotation_episode/original_extra_helper.py','sha256':'c'*64,'size_bytes':17})
    before=deepcopy(value)
    with monkeypatch.context() as guarded:
        database.forbid_io(guarded)
        result=retained(value,module_root='/deploy',python_executable='/runtime/python')
        assert result==before and value==before
        result['package_files'][-1]['size_bytes']=18
        assert value==before


def test_retained_standard_bundle_keeps_independent_attempt_requirement(monkeypatch):
    with monkeypatch.context() as guarded:
        guarded.setattr(standard,'n',_RetainedContracts(standard.n))
        database.forbid_io(guarded);inputs=standard.fixture();bundle=inputs['bundle'];before=deepcopy(bundle)
        wrong=deepcopy(inputs['attempt_identity']);wrong['plan_sha256']='0'*64
        with pytest.raises(ValueError,match='bundle_original_attempt_mismatch'):
            standard.n.validate_standard_blast_database_bundle(bundle,original_job=inputs['job'],attempt_identity=wrong)
        assert bundle==before


def test_null_manifest_failure_relationship_checks_match_current_interface(monkeypatch):
    contracts=import_module('gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_standard_database_contracts')
    with monkeypatch.context() as guarded:
        guarded.setattr(standard,'n',_RetainedContracts(standard.n))
        database.forbid_io(guarded);inputs=standard.fixture();bundle=deepcopy(inputs['bundle'])
        bundle['producer_verification']['manifest']=None;before=deepcopy(bundle)
        errors=[]
        for validate in (contracts.validate_standard_blast_database_bundle,contracts.validate_retained_standard_blast_database_bundle):
            with pytest.raises(ValueError,match='producer_invalid_manifest_relationship') as failure:
                validate(bundle,original_job=inputs['job'],attempt_identity=inputs['attempt_identity'])
            errors.append(failure.value.args)
        assert errors[0]==errors[1] and bundle==before


@pytest.mark.parametrize('family',('database','standard_database'))
@pytest.mark.parametrize('boundary',('manifest','bundle'))
@pytest.mark.parametrize('invalid',('custom_entry_equality','custom_key_equality','cyclic_data'))
def test_original_finite_json_defense_precedes_profile_inspection(monkeypatch,family,boundary,invalid):
    contracts=import_module('gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_'+family+'_contracts')
    middle='standard' if family=='standard_database' else 'native'
    suffix=middle+'_blast_database_'+('producer_manifest' if boundary=='manifest' else 'bundle')
    validators=(getattr(contracts,'validate_'+suffix),getattr(contracts,'validate_retained_'+suffix))
    comparisons=[]
    class EqualityTrap:
        def __hash__(self):
            return hash('entry_module' if boundary=='manifest' else 'producer_verification')
        def __eq__(self,other):
            comparisons.append(other)
            raise AssertionError('non-JSON equality executed before finite JSON validation')
    if invalid=='custom_key_equality':
        value={EqualityTrap():None}
    elif invalid=='custom_entry_equality':
        manifest={'entry_module':EqualityTrap()}
        value=manifest if boundary=='manifest' else {'producer_verification':{'manifest':manifest}}
    else:
        value={};value['cycle']=value
    arguments={'module_root':'/deploy','python_executable':'/runtime/python'} if boundary=='manifest' else {'original_job':{},'attempt_identity':{}}
    failures=[]
    with monkeypatch.context() as guarded:
        database.forbid_io(guarded)
        for validate in validators:
            with pytest.raises(ValueError,match='finite_json_required') as failure:
                validate(value,**arguments)
            failures.append(failure.value.args)
        assert failures[0]==failures[1]
        assert comparisons==[]
