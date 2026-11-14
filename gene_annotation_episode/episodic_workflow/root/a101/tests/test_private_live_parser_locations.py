"""Actual native input-syntax parser selection; no native executable is run."""
from copy import deepcopy
from pathlib import Path
import pytest
from gene_annotation_episode.episodic_workflow.root.a101.library import blast_pssm_inputs
from gene_annotation_episode.episodic_workflow.root.a101 import native_blast_database_driver
from gene_annotation_episode.episodic_workflow.root.a101 import native_blast_standard_database_driver
from .test_native_blast_database_contracts import job_for as database_job
from .retained_blast_manifest_fixtures.standard import job_for as standard_job

PSSM = b'''PssmWithParameters ::= { pssm { isProtein TRUE, numRows 2, numColumns 2,
 query seq { inst { repr raw, mol aa, length 2, seq-data iupacaa "AC" } },
 finalData { scores { 1, 2, 3, 4 }, lambda 1.0, kappa 1.0, h 1.0 } } }
'''
ROOT = Path(__file__).resolve().parents[5]


@pytest.mark.parametrize('family',('database','standard_database'))
@pytest.mark.parametrize('selection',('actual','missing','shadowed'))
def test_actual_pssm_parser_source_selection(tmp_path,monkeypatch,family,selection):
    driver=native_blast_database_driver if family=='database' else native_blast_standard_database_driver
    job=database_job('psiblast','pssm') if family=='database' else standard_job('blastp','pssm')
    before=deepcopy(job)
    path=tmp_path/'selected-query.asn';path.write_bytes(PSSM)
    actual=Path(blast_pssm_inputs.__file__).resolve()
    relative=actual.relative_to(ROOT).as_posix()
    manifest={'module_root':str(ROOT),'package_files':[{'relative_path':relative}]}
    if selection=='actual':
        assert driver._pssm(path,job,producer_manifest=manifest) is None
    else:
        def forbid_parser(*args,**kwargs):
            raise AssertionError('unselected parser must not consume query bytes')
        monkeypatch.setattr(blast_pssm_inputs,'read_blast_pssm',forbid_parser)
        if selection=='missing':
            manifest['package_files']=[]
            expected=ModuleNotFoundError;message='selected_deployment_pssm_parser_unavailable'
        else:
            manifest['module_root']=str(tmp_path/'different-deployment')
            expected=ImportError;message='selected_deployment_pssm_parser_shadowed'
        with pytest.raises(expected,match=message):
            driver._pssm(path,job,producer_manifest=manifest)
    assert job==before and path.read_bytes()==PSSM
