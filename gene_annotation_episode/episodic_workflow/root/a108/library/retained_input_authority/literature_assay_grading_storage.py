"""Persist selected assay grading and deliver exact requested A105 components.

Only population reads scientific inputs and calculates. Reconstruction validates
committed identities and typed cells; it does not rerun a reader or grader.
"""
from copy import deepcopy
import json
from pathlib import Path
from gene_annotation_episode.episodic_workflow.root.a108.domain import obj
from gene_annotation_episode.episodic_workflow.root.a108.library.retained_input_authority.literature_assay_grading import assay_grading_sheet_schema, assay_grading_cell_schema
NAMESPACE = 'literature_assay_grading_cells'

def assay_grading_cells_schema():
    cell_schema = assay_grading_cell_schema()
    fields = deepcopy(cell_schema['properties'])
    sheet = assay_grading_sheet_schema()['properties']
    fields.update({'sheet_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}, 'evidence_source_ref': {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'source'}, **{name: deepcopy(sheet[name]) for name in ('evaluation_scope', 'assay_type', 'assertion_ref', 'quantity_kind', 'interpretations', 'prediction_model', 'annotation_credit')}})
    fields['experiment_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'reference'}
    fields['assertion_ref'] = {'type': 'string', 'format': 'reference', 'x-reference-namespace': 'hypothesis'}
    fields['source_refs']['items'] = {'type': 'string', 'format': 'reference'}
    for criterion in fields['interpretations']['properties'].values():
        criterion['properties']['support_refs']['items'] = {'type': 'string', 'format': 'reference'}
    fields['prediction_model']['anyOf'][0]['properties']['support_refs']['items'] = {'type': 'string', 'format': 'reference'}
    return {'type': 'array', 'x-source': NAMESPACE, 'items': obj(fields, required=[*cell_schema['required'], 'sheet_ref', 'evidence_source_ref', 'evaluation_scope', 'assay_type', 'assertion_ref', 'quantity_kind', 'interpretations', 'prediction_model', 'annotation_credit'])}

def legacy_assay_grading_cells_schema():
    """Original frozen four-type parent contract; never infer new old fields."""
    return json.loads(Path(__file__).with_name('literature_assay_grading_legacy_cells_v1.json').read_text())
