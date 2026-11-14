"""Private root annotation axis contribution readers."""
from __future__ import annotations

def axis_contribution_readers(store, run_id):
    from gene_annotation_episode.episodic_workflow.root.a101.scientific_process.native_correspondence_credit import A101SequenceCredit
    from .a102.a102_credit import A102StructuralCredit
    from .a103.a103_credit import A103ContextCredit
    from .a104.a104_credit import A104EvolutionaryCredit
    from .a105.library.literature_a105_aggregation_storage import LiteratureA105AggregationRepository
    from .a106.library.literature_a106_subscore_storage import LiteratureA106SubscoreRepository
    from .a108.library.literature_a108_aggregation_storage import LiteratureA108AggregationRepository
    from .a107.a107_qualification import annotation_contribution as a107
    from .a110.a110_qualification import annotation_contribution as a110
    return {'A101': A101SequenceCredit().annotation_contribution, 'A102': A102StructuralCredit().annotation_contribution, 'A103': A103ContextCredit().annotation_contribution, 'A104': A104EvolutionaryCredit().annotation_contribution, 'A105': LiteratureA105AggregationRepository(store, run_id).annotation_contribution, 'A106': LiteratureA106SubscoreRepository(store, run_id).annotation_contribution, 'A107': a107, 'A108': LiteratureA108AggregationRepository(store, run_id).annotation_contribution, 'A110': a110}
