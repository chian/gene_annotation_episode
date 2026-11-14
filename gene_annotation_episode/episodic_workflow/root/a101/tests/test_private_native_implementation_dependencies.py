"""Actual native scientific dependency construction; no native execution."""
from copy import deepcopy
import hashlib
from pathlib import Path

import pytest

from gene_annotation_episode.episodic_workflow.root.a101.library import alignment_correspondence as correspondence
from .. import native_blast_database_result_worker as database
from .. import native_blast_standard_database_result_worker as standard
import gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_database_worker_values as _scientific_native_blast_database_result_worker
import gene_annotation_episode.episodic_workflow.root.a101.library.native_blast_standard_database_worker_values as _scientific_native_blast_standard_database_result_worker


@pytest.mark.parametrize('family,options',[
    ('database',{}),('database',{'execution_program':'psiblast'}),
    ('database',{'execution_program':'blastn_vdb','vdb_function':True}),('standard',{}),
])
def test_actual_scientific_worker_closure_requires_original_correspondence_provider(family,options):
    worker=database if family=='database' else standard
    modules=worker._implementation_modules(**options)
    assert modules[correspondence.__name__] is correspondence
    files=[{'module':name,'path':str(Path(module.__file__).resolve()),
        'sha256':hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()}
        for name,module in modules.items()]
    identify=(_scientific_native_blast_database_result_worker.native_blast_database_implementation_identity if family=='database'
        else _scientific_native_blast_standard_database_result_worker.standard_blast_database_implementation_identity)
    selected={'files':files,'manifest_sha256':identify(files)}
    worker._verify_implementation(selected,**options)
    missing=deepcopy(selected)
    missing['files']=[row for row in files if row['module']!=correspondence.__name__]
    missing['manifest_sha256']=identify(missing['files'])
    with pytest.raises(worker._WorkerFailure) as caught:
        worker._verify_implementation(missing,**options)
    assert caught.value.failure['code']==('native_blast_database_artifact_identity_mismatch'
        if family=='database' else 'native_blast_standard_database_artifact_identity_mismatch')
    assert caught.value.failure['pointer']=='/implementation/files'
    assert caught.value.failure['detail_code']=='artifact_digest_conflict'
