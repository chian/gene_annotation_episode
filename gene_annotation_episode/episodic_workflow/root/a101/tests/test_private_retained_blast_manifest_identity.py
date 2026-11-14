"""Old and current producer identities; pure synthetic records, no native run."""
from copy import deepcopy
from importlib import import_module
import pytest
from .retained_blast_manifest_fixtures import database, standard


def test_original_database_manifest_pure_defensive_closed(monkeypatch):
    with monkeypatch.context() as guarded:
        guarded.setattr(database, 'c', _RetainedContracts(database.c))
        database.test_producer_manifest_is_pure_defensive_and_closed(guarded)


def test_original_standard_bundle_keeps_retained_producer_identity(monkeypatch):
    with monkeypatch.context() as guarded:
        guarded.setattr(standard, 'n', _RetainedContracts(standard.n))
        database.forbid_io(guarded)
        inputs=standard.fixture()
        bundle=inputs['bundle'];before=deepcopy(bundle)
        result=standard.n.validate_standard_blast_database_bundle(bundle,
            original_job=inputs['job'],attempt_identity=inputs['attempt_identity'])
        assert result==before and bundle==before
        assert bundle['producer_verification']['manifest']['entry_module']=='gene_annotation_episode.native_blast_standard_database_driver'


@pytest.mark.parametrize('family',('database','standard_database'))
def test_current_private_producer_manifest_remains_valid_and_defensive(monkeypatch,family):
    with monkeypatch.context() as guarded:
        module=import_module('gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_'+family+'_contracts')
        manifest=database.manifest_for()
        if family=='standard_database':
            manifest['version']='native_blast_standard_database_producer_manifest_v1'
        stem='native_blast_'+family
        manifest['entry_module']='gene_annotation_episode.episodic_workflow.root.a101.'+stem+'_driver'
        names=[stem+'_contracts.py',stem+'_driver.py']+(['blast_program_context.py'] if family=='standard_database' else [])
        manifest['package_files']=[{'relative_path':'gene_annotation_episode/__init__.py','sha256':'b'*64,'size_bytes':10},
            *[{'relative_path':'gene_annotation_episode/episodic_workflow/root/a101/' + ('library/' if name in ('blast_program_context.py', 'native_blast_database_contracts.py', 'native_blast_standard_database_contracts.py') else '') + name,'sha256':'b'*64,'size_bytes':10} for name in names]]
        before=deepcopy(manifest)
        validator=module.validate_standard_blast_database_producer_manifest if family=='standard_database' else module.validate_native_blast_database_producer_manifest
        database.forbid_io(guarded)
        result=validator(manifest,module_root='/deploy',python_executable='/runtime/python')
        assert result==before and manifest==before and result is not manifest
        result['python']['size_bytes']=99
        assert manifest['python']['size_bytes']==23


class _RetainedContracts:
    """Fixture-only view selecting explicit passive validation interfaces."""
    def __init__(self, contracts):
        self._contracts = contracts

    def __getattr__(self, name):
        selected = {
            'validate_native_blast_database_producer_manifest': 'validate_retained_native_blast_database_producer_manifest',
            'validate_standard_blast_database_producer_manifest': 'validate_retained_standard_blast_database_producer_manifest',
            'validate_native_blast_database_bundle': 'validate_retained_native_blast_database_bundle',
            'validate_standard_blast_database_bundle': 'validate_retained_standard_blast_database_bundle',
        }
        return getattr(self._contracts, selected.get(name, name))
