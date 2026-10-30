"""Synthetic bounded repro of existing parent fact projection; no shared edits.
Run from the checkout with PYTHONDONTWRITEBYTECODE=1 and .venv/bin/python -B.
This is an adapter/typed-form exercise, not a model or shared method_loop run.
"""
import asyncio
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from gene_annotation_episode.communication import form_with_facts, validate_form
from gene_annotation_episode.domain import obj
from gene_annotation_episode.episode_bindings import BindingContext
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_experimental_contracts import HEADERS
from gene_annotation_episode.literature_rate_storage import rate_cells_schema
from gene_annotation_episode.state import Store

HERE = Path(__file__).resolve().parent

def main():
    # Only this audit's directory is writable by this script.
    root = HERE / 'synthetic_subset_store_002'
    if root.exists():
        raise RuntimeError('Use a fresh owned output directory; existing repro is preserved.')
    store = Store(root)
    try:
        store.create_problem(raw_sequence='ATGGCT', molecule='dna')
        rows = [
            ['fixture molecule','fixture experiment','reference','reference condition','endpoint','per_preparation','2','umol/min','sd','.2','3','unspecified','synthetic'],
            ['fixture molecule','fixture experiment','test','test condition','endpoint','per_preparation','1','umol/min','sd','.3','3','unspecified','synthetic'],
        ]
        raw = '\t'.join(HEADERS) + '\n' + '\n'.join('\t'.join(r) for r in rows) + '\n'
        artifact = store.artifact(raw, 'text/tab-separated-values')
        source = store.put('source', {'provider':'coverage041.synthetic','accession':None,'uri':None,'artifact_ref':artifact,'text_ref':artifact,'request_ref':None,'version':None,'retrieved_at':None}, origin='caller')
        run = 'coverage041-synthetic-run'
        workflow = SimpleNamespace(store=store, run_id=run, tools=SimpleNamespace(catalog=lambda **kwargs: {}))
        services = WorkflowServices(workflow)
        binding = LiteratureEpisodes(services, rate_population=True)
        scope = store.validate_scope()
        child = BindingContext(run,'child-strategy','literature_strategy',(('literature','parent'),('literature_strategy','child')),scope,
            {'version':'strategy_assignment_v1','question_context_refs':[source['id']],'prior_search_refs':[], 'requested_rate_components':['rate_difference']},{},(source['id'],))
        args = {'source_ref':source['id'],'source_representation':'original','table_kind':'synthetic_fixture','delimiter':'\t','subject':'fixture molecule','experiment':'fixture experiment','reference_arm':'reference','test_arm':'test','reference_condition':'reference condition','test_condition':'test condition','dependence':'unknown','observation_model':'none'}
        outcome = asyncio.run(binding.execute(child,'literature.rate.populate',args,'child-selected-population'))
        assert outcome['status'] == 'completed', outcome
        sheet_ref = outcome['result']['sheet_ref']
        child = replace(child, received_record_refs=(*child.received_record_refs,*outcome['record_refs']))
        child_facts = binding.facts(child,{'committed_record_refs':[sheet_ref]})
        schema = obj({'measurements':rate_cells_schema()})
        form = form_with_facts({},schema,child_facts)
        assert [r['component'] for r in form['measurements']] == ['rate_difference']
        parent = BindingContext(run,'parent-literature','literature',(('literature','parent'),),scope,
            {'version':'literature_assignment_v1','question_context_refs':[],'source_refs':[source['id']]},{},(source['id'],*outcome['record_refs']))
        validate_form(form,schema,lambda ref, namespace: ref in parent.received_record_refs and store.get(ref)['record_type'] == namespace)
        binding.validate_received_report(parent,form,schema)
        binding.received_form_references(parent,form,schema,'trusted-synthetic-admitted-subset')
        repo = services.literature_rate_repository()
        admitted = repo.received_cells(parent)
        assert [r['component'] for r in admitted] == ['rate_difference']
        def forbidden(*args,**kwargs):
            raise AssertionError('Projection must not read original source bytes or recalculate.')
        original_get = store.get_artifact
        def saved_only(ref):
            if ref == artifact:
                forbidden()
            return original_get(ref)
        with patch('gene_annotation_episode.literature_rate_storage.read_rate_table',forbidden), patch('gene_annotation_episode.literature_rate_storage.populate_rate_contrast',forbidden), patch.object(store,'get_artifact',saved_only):
            expanded = binding.facts(parent,{'committed_record_refs':[sheet_ref]})['literature_rate_cells']
            annotation = replace(parent,role='annotation',path=(('annotation','outer'),))
            exact_outer = binding.received_report_facts(annotation)['literature_rate_cells']
        expanded_names = [r['component'] for r in expanded]
        assert 'reference_rate' in expanded_names and 'test_rate' in expanded_names
        assert exact_outer == admitted
        # The projection can reach the ordinary bound typed form with no prose
        # or independent numerical interpretation by a model.
        downstream_form = form_with_facts({},schema,{'literature_rate_cells':expanded})
        validate_form(downstream_form,schema,lambda ref, namespace: ref in parent.received_record_refs and store.get(ref)['record_type'] == namespace)
        report = {'status':'reproduced','synthetic_only':True,'model_calls':0,'runtime_loop_run':False,
            'source_parser_calculator_disabled_during_parent_projection':True,
            'original_source_bytes_forbidden_during_parent_projection':True,
            'child_requested_components':['rate_difference'],
            'parent_admitted_cells':[{k:r[k] for k in ('component','value','unit')} for r in admitted],
            'literature_parent_projected_cells':[{k:r[k] for k in ('component','value','unit')} for r in expanded],
            'annotation_parent_received_components':[r['component'] for r in exact_outer],
            'expanded_typed_form_valid':True,
            'population_operation_count':store.db.execute('SELECT count(*) FROM literature_rate_operations').fetchone()[0],
            'received_subset_count':store.db.execute('SELECT count(*) FROM literature_rate_received').fetchone()[0],
            'limitations':['Adapter/closed-form admission exercised; this repro does not claim a full shared-loop child commissioning or runtime_report_attempts receipt.','Reproduced v1 rate family. Other nonoptical routes share the same unconditional _rate_facts project_cells branch; their family-specific value projection was inspected but not separately executed here.','No scientific observation or credit is inferred from this synthetic fixture.']}
        (HERE/'SUBSET_EXPANSION_RECEIPT.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
    finally:
        store.close()

if __name__ == '__main__':
    main()
