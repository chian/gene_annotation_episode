"""Original constructed A106 summary operands with private typed custody.

Moved verbatim from test_literature_perturbation_summary_integration. These are
synthetic measurement fixtures, not scientific commissions or acquired evidence.
"""
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_repositories import LiteratureContext
from gene_annotation_episode.state import Store
from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.perturbation_evidence.tests.test_literature_perturbation_summary import source_data, paired_data, arguments, TEXT, graph_data, IMAGE

REQUESTED=["perturbation_difference","W_mean_variance","perturbation_mean_variance","perturbation_variance_upper","reference_restoration_index"]


def source(store,body,parents=()):
    artifact=store.artifact(body,'application/octet-stream')
    return store.put('source',{'provider':'constructed_a106_summary','accession':None,'uri':None,
        'artifact_ref':artifact,'text_ref':None,'request_ref':None,'version':None,'retrieved_at':None,
        'parent_source_refs':list(parents)},origin='caller')


def fixture(path,*,paired=False,graph=False):
    store=Store(path);store.create_problem(raw_sequence='ATGGCT',molecule='dna')
    root=source(store,TEXT);refs=[root['id']]
    data=paired_data() if paired else source_data()
    if graph:
        data,images=graph_data()
        image=source(store,images[IMAGE],parents=[root['id']]);refs.append(image['id'])
        data['measurements']['W']['graph']['source_ref']=image['id']
    retained=source(store,canonical(data),parents=[root['id']]);refs.append(retained['id'])
    args=arguments();args.update(source_ref=root['id'],data_source_ref=retained['id'])
    for witness in args['interpretation_witnesses']:witness['source_ref']=root['id']
    args['literals']['molecule']={**args['interpretation_witnesses'][0]}
    assignment={'version':'literature_assignment_v1','question_context_refs':[],'source_refs':refs,
        'requested_perturbation_summary_components':REQUESTED}
    context=LiteratureContext('summary-fixture-run','summary-child','literature',(('literature','fixture'),),
        store.validate_scope({'subject_refs': store.problem()['subject_refs']}),assignment,{},tuple(refs))
    return store,context,args


