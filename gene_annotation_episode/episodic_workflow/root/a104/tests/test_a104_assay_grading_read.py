"""A104 authenticates the original A105 sheet without importing its reader."""

from gene_annotation_episode.episodic_workflow.root.a104.a104_assay_grading_read import A104AssayGradingReader
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_assay_grading_storage import LiteratureAssayGradingRepository
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_a105_assay_type_binding_322 import grading_fixture
from gene_annotation_episode.state import Store


def test_a104_read_only_grade_matches_authentic_selected_a105_sheet(tmp_path):
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        context, args, _ = grading_fixture(store, assay_type='activity_rate')
        owner = LiteratureAssayGradingRepository(store, context.run_id)
        result = owner.populate(context, args, 'a104-reader-control')
        sheet_ref = result['result']['sheet_ref']
        reader = A104AssayGradingReader(store, context.run_id)
        saved = reader.read(sheet_ref)
        assert saved == owner.read(sheet_ref)
        components = ['source_log_evidence_ratio', 'measured_effect']
        assert reader.rows(saved, sheet_ref, components) == owner.rows(saved, sheet_ref, components)
