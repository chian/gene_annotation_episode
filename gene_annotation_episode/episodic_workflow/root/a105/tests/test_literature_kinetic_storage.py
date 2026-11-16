"""Synthetic selected kinetic persistence, source custody and saved-only facts."""
import pytest
from gene_annotation_episode.episodic_workflow.root.a105.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_validation import validate_saved_kinetic
from gene_annotation_episode.episodic_workflow.root.a105.state import Store
from gene_annotation_episode.episodic_workflow.root.a105.tests.test_literature_kinetic_inputs import fixture, SOURCE_REF, Source

def setup(path, *, kind='catalytic_efficiency', unit='uM^-1min^-1', n='8', d='2', change=None, extra=''):
    original, args = fixture(kind, unit, n, d, extra=extra)
    for role, printed in (('numerator', n), ('denominator', d)):
        if printed.startswith('<') or printed.startswith('about '):
            prefix = 1 if printed.startswith('<') else len('about ')
            args[role]['measurement']['number']['number_start'] += prefix
    store = Store(path)
    store.create_problem(raw_sequence='ATGGCT', molecule='dna')
    artifact = store.artifact(original.raw, 'application/xml')
    source = store.put('source', {'provider': 'synthetic_kinetic_fixture', 'accession': None, 'uri': None, 'artifact_ref': artifact, 'text_ref': artifact, 'request_ref': None, 'version': None, 'retrieved_at': None}, origin='caller')['id']

    def bind(value):
        if isinstance(value, dict):
            return {k: bind(v) for k, v in value.items()}
        if isinstance(value, list):
            return [bind(v) for v in value]
        return source if value == SOURCE_REF else value
    args = bind(args)
    if change:
        change(args)
    context = BindingContext('kinetic-run', 'kinetic-child', 'literature', (('literature', 'case'),), store.validate_scope(), {'version': 'literature_assignment_v1', 'question_context_refs': [], 'source_refs': [source]}, {}, (source,))
    return (store, context, args)

def project(repo, outcome, components=None):
    return repo.project_cells([outcome['result']['sheet_ref']], permitted_record_refs=outcome['record_refs'], components=components)












@pytest.mark.parametrize('target', ['number_relation', 'number_approximation', 'row_approximation', 'source_qualification', 'canonical_censor', 'populated_reason', 'missing_unavailable_reason', 'raw_value', 'wrong_partial_reason'])
def test_detached_semantic_contract_rejects_qualification_and_cell_contradictions(target, monkeypatch):
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_inputs import read_kinetic_inputs
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_calculations import populate_kinetic_contrast
    source, selection = fixture()
    if target == 'wrong_partial_reason':
        selection['numerator']['measurement']['unit'] = None
    extraction = read_kinetic_inputs(selection, read_source=source.read)
    calculation = populate_kinetic_contrast(extraction['calculation_inputs'])
    numerator = extraction['operands']['numerator']
    if target == 'number_relation':
        numerator['number']['relation'] = 'gt'
    elif target == 'number_approximation':
        numerator['number']['approximate'] = True
    elif target == 'row_approximation':
        numerator['approximate'] = True
    elif target == 'source_qualification':
        selection['numerator']['qualification']['value'] = 'source_qualified_approximate'
        numerator['qualification']['value'] = 'source_qualified_approximate'
    elif target == 'canonical_censor':
        for operand in (numerator['calculation_operand'], extraction['calculation_inputs']['numerator'], calculation['inputs']['numerator']):
            operand.update(status='censored', relation='lt')
    elif target == 'populated_reason':
        calculation['cells']['numerator_parameter']['unavailable_reason'] = 'source_measurement_unreported'
    elif target == 'raw_value':
        calculation['cells']['numerator_parameter']['value'] = 77
    elif target == 'wrong_partial_reason':
        calculation['cells']['numerator_parameter']['unavailable_reason'] = 'source_measurement_unreported'
    else:
        calculation['cells']['log_contrast_variance']['unavailable_reason'] = None

    def forbidden(*_a, **_kw):
        raise AssertionError('Detached invariants may not reread sources or rerun scientific calculations')
    monkeypatch.setattr(source, 'read', forbidden)
    monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_inputs.read_kinetic_inputs', forbidden)
    monkeypatch.setattr('gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_calculations.populate_kinetic_contrast', forbidden)
    with pytest.raises(ExperimentalContractError, match='kinetic_saved_mismatch'):
        validate_saved_kinetic(selection, extraction, calculation)

@pytest.mark.parametrize('case', ['censored', 'approximate', 'qualified_approximate', 'unknown_qualification', 'conflicting_qualification', 'missing_unit', 'missing_measurement', 'missing_operand', 'zero'])
def test_detached_semantic_invariants_preserve_valid_native_partials(case):
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_inputs import read_kinetic_inputs
    from gene_annotation_episode.episodic_workflow.root.a105.library.literature_kinetic_calculations import populate_kinetic_contrast
    n = '<8' if case == 'censored' else 'about 8' if case == 'approximate' else '0' if case == 'zero' else '8'
    source, selection = fixture(n=n)
    numerator = selection['numerator']
    if case in ('censored', 'approximate'):
        numerator['measurement']['number']['number_start'] += 1 if case == 'censored' else len('about ')
    elif case == 'qualified_approximate':
        numerator['qualification']['value'] = 'source_qualified_approximate'
    elif case == 'unknown_qualification':
        numerator['qualification'] = {'value': 'unknown', 'witnesses': []}
    elif case == 'conflicting_qualification':
        numerator['qualification'] = {'value': 'conflicting', 'witnesses': [source.witness('substrateN'), source.witness('substrateD')]}
    elif case == 'missing_unit':
        numerator['measurement']['unit'] = None
    elif case == 'missing_measurement':
        numerator['measurement'] = None
    elif case == 'missing_operand':
        selection['numerator'] = None
    extraction = read_kinetic_inputs(selection, read_source=source.read)
    calculation = populate_kinetic_contrast(extraction['calculation_inputs'])
    assert validate_saved_kinetic(selection, extraction, calculation) == (extraction, calculation)
