"""A bound external query remains transferable evidence, not a new target."""
import pytest

from gene_annotation_episode.communication import validate_form,ReportBoundaryError
from gene_annotation_episode.homology_episodes import HomologyEpisodes,obj,reference
from gene_annotation_episode.homology_jobs import HomologyJobs,FileAsset,digest
from gene_annotation_episode.local_jobs import LocalJobPolicy
from gene_annotation_episode.state import Store
from a103_test_support import source,protein,native_pair
from gene_annotation_episode.a101_credit import A101SequenceCredit


def test_result_query_reference_resolves_only_as_the_bound_operand_without_target_credit(tmp_path):
    executable=tmp_path/'not-executed';executable.write_text('#!/bin/sh\nexit 99\n');executable.chmod(0o700)
    fasta=tmp_path/'references.faa';fasta.write_text('>engineering\nMNNQ\n')
    policy=LocalJobPolicy(128 * 1024 ** 2, 32 * 1024 ** 2)
    jobs=HomologyJobs.create(tmp_path/'jobs',executable=FileAsset(executable,digest(executable)),
        reference_database=FileAsset(fasta,digest(fasta)),policy=policy,max_cpu=1)
    try:
        with Store(tmp_path/'state') as store:
            target,=store.create_problem(raw_sequence='MDEAKG',molecule='protein')['subject_refs']
            scope={'subject_refs':[target]}
            origin=source(store,'engineering.query-return',{'meaning':'typed operand identity control; no native search'})
            query=protein(store,'MNNQ',origin,'external-query')
            comparator=protein(store,'MNNQ',origin,'external-comparator')
            job=jobs.order(query_ref=query,query_fasta='>query\nMNNQ\n',cpu=1,operation_key='declared-query')
            binding=HomologyEpisodes(jobs,parser_policy=policy,credit_projector=lambda *a,**k:0,
                credit_binding={'kind':'engineering'},monitoring_projector=lambda *a,**k:0,
                monitoring_binding={'kind':'engineering'})
            assignment={'job_ref':job,'query_ref':query,'cpu':1}
            resolve=lambda value,namespace:binding.resolve(store,scope,value,namespace,assignment=assignment)
            schema=obj({'query_ref':reference('subject')})
            validate_form({'query_ref':query},schema,resolve)
            for wrong in (comparator,origin):
                with pytest.raises(ReportBoundaryError):validate_form({'query_ref':wrong},schema,resolve)
            known={target,query,comparator,origin}
            native_pair(store,query,comparator,known)
            assert A101SequenceCredit()(store,scope,known_record_refs=known)['credit']==0
            assert store.problem()['subject_refs']==[target]
            assert not list((tmp_path/'jobs').glob('*/native.handle.json'))
    finally:jobs.close()
