from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
import json
from gene_annotation_episode.episodic_workflow.root.a110.domain import canonical
from gene_annotation_episode.episodic_workflow.root.a110.episode_bindings import EpisodeBindingRegistry, BindingContext, _plain
from gene_annotation_episode.episodic_workflow.root.a110.state import Store
BASE = Path(__file__).parents[2] / 'tests/fixtures/source_records'

from gene_annotation_episode.episodic_workflow.root.a110.runtime import ContractInformationError, Episode, EpisodeGoal, EpisodeRequest, Record, _plain as _runtime_plain, validate_saved_fact_form

def source(store, raw, *, parents=(), text=None):
    artifact = store.artifact(raw, 'application/octet-stream')
    text_ref = store.artifact(text, 'text/plain') if text is not None else None
    return store.put('source', {'provider': 'source_reaction_example', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': text_ref, 'request_ref': None, 'version': None, 'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')

def witness(ref, raw, quote, representation='original'):
    token = quote.encode('utf-8')
    start = raw.index(token)
    return {'source_ref': ref, 'representation': representation, 'start': start, 'end': start + len(token), 'quote': quote}

def setup_case(path, *, primary=False, incomplete=False, target_sequence=None):
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT' if target_sequence is None else target_sequence, molecule='dna' if target_sequence is None else 'protein')
    raw = (BASE / 'primary_csid/PMC6265302_original.xml').read_bytes() if primary else b'SyntheticProtein produces ProductA per ProductB in independent preparations. Matched synthetic reaction and resource budget with declared usable supply.'
    paper = source(store, raw)
    refs = [paper['id']]
    literals = dict.fromkeys(LITERAL_FIELDS)
    if primary:
        layout = (BASE / 'primary_csid/supplement_layout.txt').read_bytes()
        supplement = source(store, (BASE / 'primary_csid/41467_2018_7563_MOESM1_ESM.pdf').read_bytes(), parents=[paper['id']], text=layout)
        refs.append(supplement['id'])
        sw = lambda quote: witness(supplement['id'], layout, quote, 'text')
        literals.update(molecule=witness(paper['id'], raw, 'CsiD'), construct=witness(paper['id'], raw, 'N-terminal His-tag'), experiment=sw('Supplementary Figure 2:'), numerator=sw('succinic acid'), denominator=sw('L-2-hydroxyglutarate'), endpoint=sw('products of the CsiD reaction'), condition=witness(paper['id'], raw, '20\u2009mM ammonium acetate buffer pH 7.25'))
        interpretations = [sw('succinic acid : L-2-hydroxyglutarate = 1:1')]
        ratio = {'mode': 'source_summary', 'ratio_kind': 'product_pair', 'unit': 'mol_per_mol', 'origin': 'reported', 'observations': [], 'mean': 1.0, 'sample_sd': None, 'independent_n': None, 'claim': 1.0, 'alternatives': []}
        budget = None
    else:
        w = lambda quote: witness(paper['id'], raw, quote)
        literals.update(molecule=w('SyntheticProtein'), numerator=w('ProductA'), denominator=w('ProductB'), experiment=w('independent preparations'), endpoint=w('synthetic reaction'), resource_context=w('declared usable supply'))
        interpretations = [w(raw.decode('utf-8'))]
        ratio = {'mode': 'independent_units', 'ratio_kind': 'product_pair', 'unit': 'mol_per_mol', 'origin': 'synthetic', 'observations': [{'measurement_key': 'preparation1', 'value': 0.7}, {'measurement_key': 'preparation2', 'value': 0.9}], 'mean': None, 'sample_sd': None, 'independent_n': None, 'claim': 1.0, 'alternatives': [{'key': 'half_product_ratio', 'prediction': 0.5}]}
        budget = {'basis': 'usable_batch', 'unit': 'umol', 'origin': 'synthetic', 'resources_complete': not incomplete, 'resources': [{'resource_key': 'reagent1', 'value': 12.0, 'lower': 12.0, 'upper': 12.0, 'coefficient': 1.0}, {'resource_key': 'reagent2', 'value': 6.0, 'lower': 6.0, 'upper': 6.0, 'coefficient': 1.0}], 'demand': 10.0}
    data = {'version': 'a110_source_reaction_measurements_v1', 'ratio': ratio, 'budget': budget}
    dataset = source(store, canonical(data), parents=refs)
    refs.append(dataset['id'])
    args = {'source_ref': paper['id'], 'data_source_ref': dataset['id'], 'source_kind': 'retained_extraction' if primary else 'synthetic_fixture', 'literals': literals, 'interpretation_witnesses': interpretations}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': refs, 'requested_reaction_components': COMPONENTS}
    context = BindingContext('reaction-fixture-run', 'reaction-fixture-child', 'literature', (('literature', 'fixture'),), store.validate_scope(), assignment, {}, tuple(refs))
    return (store, context, args)
COMPONENTS = ['ratio_mean', 'claim_mean_squared_error', 'reaction_comparison', 'resource_coverage', 'resource_comparison_upper']
LITERAL_FIELDS = ('molecule', 'construct', 'experiment', 'numerator', 'denominator', 'endpoint', 'condition', 'resource_context')
