"""Case167 original-source Table 3 comparison; no invented common assay model."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from types import SimpleNamespace

from gene_annotation_episode.domain import identity
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_measurement_comparison_inputs import (
    read_measurement_comparison_inputs, compile_measurement_comparison_inputs,
)
from gene_annotation_episode.literature_measurement_comparison_calculations import populate_measurement_comparison
from gene_annotation_episode.literature_measurement_comparison_storage import (
    LiteratureMeasurementComparisonRepository, measurement_comparison_operation_schema,
    REQUESTED,
)
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry

from test_literature_measurement_comparison_components_258 import source_fixture
from test_literature_measurement_comparison_binding_268 import selected as selected_operation


ORIGINAL = Path(__file__).resolve().parents[1] / 'research/experimental_scoring_review_2026-10-23/a105_calibration_primary_case_167/source/PMC6454709.xml'
SHA256 = '86896c47556f7eeef975856dbbe2d3bab3b6143b91d1f826078e29771761b698'


def selection_from_original():
    content = ORIGINAL.read_bytes()
    assert hashlib.sha256(content).hexdigest() == SHA256
    text = content.decode()
    reference = identity('source', {'original': SHA256, 'case': 'wst8_method_contrast_291'})
    artifact = 'artifact_' + SHA256

    def witness(token, container=None, occurrence=0):
        if container is None:
            start = text.index(token)
        else:
            base = text.index(container)
            start = base
            for _ in range(occurrence + 1):
                start = text.index(token, start)
            assert start < base + len(container)
        return {'source_ref': reference, 'representation': 'original',
                'start': len(text[:start].encode()), 'end': len(text[:start + len(token)].encode()),
                'quote': token}

    def fragment(tag, identifier):
        match = re.search(r'<' + tag + r'\b[^>]*\bid="' + identifier + r'"[^>]*>.*?</' + tag + '>', text, re.S)
        assert match is not None
        return match.group()

    table, wst, uv = fragment('table-wrap', 'Tab3'), fragment('p', 'Par33'), fragment('p', 'Par39')
    plate = fragment('p', 'Par29')
    statistics = fragment('p', 'Par43')
    rows = re.findall(r'<tr(?:\s[^>]*)?>.*?</tr>', table, re.S)
    method_rows = rows[-2:]
    heading = 'Enzyme activity (nmole/min/μg)'
    def meaning(value, quote=None, container=None):
        return {'value': value, 'witnesses': [] if quote is None else [witness(quote, container)]}

    selected, _, _ = source_fixture(table=True)
    selected.update(source_ref=reference, source_kind='primary_source', common_model=None,
                    covariance_source_refs=[], optical=None)
    selected['assertion'] = {'question': 'quantitative_activity',
        'molecule': witness('G6PD', table),
        'functional_assertion': witness('NAD(P)H produced per minute per microgram of protein', wst)}
    selected['requested_cells'] = ['native_left', 'native_right', 'converted_left', 'converted_right',
        'protocol_difference', 'protocol_ratio', 'common_ratio', 'difference_variance', 'combined_estimate']

    for role, row, protocol, value, spread in (
            ('left', method_rows[0], wst, '12.51', '0.36'),
            ('right', method_rows[1], uv, '14.88', '0.39')):
        q = deepcopy(selected['quantities'][role])
        q['layout'] = 'table'; q['record'] = None
        method = 'Colorimetric WST-8 (450\u2009nm)' if role == 'left' else 'UV-spectrophotometry (340\u2009nm)'
        q['row_label'] = witness(method, row)
        rate_cell = next(c for c in re.findall(r'<td[^>]*>.*?</td>', row, re.S) if value in c)
        q['number'] = {'witness': witness(rate_cell, row), 'number_start': rate_cell.index(value),
                       'number_end': rate_cell.index(value) + len(value)}
        q['quantity_label'] = witness('Enzyme activity', table)
        q['unit'] = witness('nmole/min/μg', table)
        q['quantity_kind'] = meaning('specific_activity', heading, table)
        q['estimator_scale'] = meaning('reported_mean', 'mean\u2009±\u2009standard deviation', statistics)
        q['semantics'] = meaning('reported_point_estimate', rate_cell, row)
        q['qualification'] = meaning('reported_point', rate_cell, row)
        q['normalization'] = meaning('protein_mass', 'per microgram of protein', protocol)
        q['subject'] = {field: None for field in q['subject']}
        q['subject']['molecule'] = witness('G6PD', protocol)
        q['subject']['organism'] = witness('human', fragment('p', 'Par28'))
        q['assay'] = {field: None for field in q['assay']}
        q['assay']['assay'] = witness(method, row)
        q['assay']['preparation'] = witness('Purified G6PD', table)
        q['assay']['substrates'] = witness('500\u2009μM G6P, 200\u2009μM NADP', protocol)
        q['assay']['conditions'] = witness(protocol, protocol)
        q['assay']['direct_endpoint'] = witness('WST-8', wst) if role == 'left' else witness('NAD(P)H absorption at 340\u2009nm', uv)
        q['assay']['inferred_quantity'] = witness('NAD(P)H produced per minute per microgram of protein', protocol)
        q['assay']['denominator'] = witness('microgram of protein', protocol)
        q['assay']['additional_differences'] = witness(plate, plate) if role == 'left' else witness(uv, uv)
        q['assay']['sampling_unit'] = witness('triplicate', statistics)
        q['physical_identity'] = None; q['dependency_witnesses'] = []
        q['uncertainty'] = {'statistic': meaning('sd', 'standard deviation', statistics),
            'magnitude': {'witness': witness(rate_cell, row), 'number_start': rate_cell.index(spread),
                          'number_end': rate_cell.index(spread) + len(spread)},
            'interval': None, 'confidence_level': None, 'unit': None,
            'unit_relationship': meaning('same_as_estimate', heading, table),
            'count': None, 'repetition_basis': meaning('unknown'), 'estimate_basis': meaning('unknown')}
        selected['quantities'][role] = q
    for role in ('epsilon_signal', 'epsilon_nuisance', 'nuisance'):
        selected['quantities'][role] = None

    relationships = dict(construct='unknown', preparation='unknown', preparation_target='unknown',
        protocol='additional_differences', endpoint='same_quantity', denominator='same_basis_supported',
        functional_bearing='same_quantitative_assertion', attribution='unknown',
        sampling='unknown', systematic_coverage='unknown',
        left_validity='identified_unresolved_interference', right_validity='unknown',
        left_readout_isolation='unknown', right_readout_isolation='unknown')
    support = {'protocol': ('0.1\u2009μg G6PD enzyme', wst),
        'endpoint': ('NAD(P)H produced per minute per microgram of protein', wst),
        'denominator': (heading, table), 'functional_bearing': ('NAD(P)H produced per minute per microgram of protein', wst),
        'left_validity': ('formazan', fragment('p', 'Par31'))}
    selected['relationships'] = {name: meaning(value, *(support[name] if name in support else ()))
        for name, value in relationships.items()}
    selected['relationships']['protocol']['witnesses'] = [
        witness('0.1\u2009μg G6PD enzyme', wst), witness('0.5\u2009μg G6PD enzyme', uv),
        witness('150\u2009μL', plate), witness('1\u2009mL', uv)]
    selected['common_quantity']['label'] = witness('NAD(P)H produced per minute per microgram of protein', wst)
    selected['common_quantity']['unit'] = 'umol/min/mg'
    for role in ('left', 'right'):
        protocol = wst if role == 'left' else uv
        selected['common_quantity'][role + '_conversion'] = {
            'kind': 'identity', 'direction': meaning('same_direction_supported', 'NAD(P)H produced', protocol),
            'support_status': meaning('supported', 'NAD(P)H produced per minute per microgram of protein', protocol),
            'reaction': None, 'endpoint_species': witness('NAD(P)H', protocol),
            'common_species': witness('NAD(P)H', wst),
            'endpoint_coefficient': None, 'common_coefficient': None}

    def read_source(source_ref, representation):
        assert (source_ref, representation) == (reference, 'original')
        return {'artifact_ref': artifact, 'content': content}
    return selected, read_source


def test_original_wst8_uv_reported_protocol_contrast_without_common_correction():
    selected, read_source = selection_from_original()
    extraction = read_measurement_comparison_inputs(selected, read_source=read_source)
    sheet = populate_measurement_comparison(compile_measurement_comparison_inputs(extraction))
    cells = {row['component']: row for row in sheet['cells']}
    assert cells['native_left']['value'] == 12.51
    assert cells['native_right']['value'] == 14.88
    assert cells['converted_left']['value'] == 12.51
    assert cells['converted_right']['value'] == 14.88
    assert cells['protocol_ratio']['exact_value'] == {'numerator': '417', 'denominator': '496'}
    assert cells['protocol_difference']['exact_value'] == {'numerator': '-237', 'denominator': '100'}
    assert cells['common_ratio']['value'] is None
    assert 'protocols_not_matched' in cells['common_ratio']['reasons']['relationship']
    assert cells['difference_variance']['value'] is None
    assert cells['combined_estimate']['value'] is None
    assert extraction['quantities']['left']['value']['canonical_unit'] == 'umol/min/mg'
    assert extraction['quantities']['left']['reported_uncertainty']['statistic'] == 'sd'
    assert extraction['quantities']['right']['reported_uncertainty']['statistic'] == 'sd'
    assert sheet['annotation_credit'] is None


def test_original_wst8_uv_selected_operation_returns_typed_cells(tmp_path):
    selection, _ = selection_from_original()
    old_ref = selection['source_ref']
    path = tmp_path / 'state'
    store = Store(path)
    try:
        manifest = path / 'empty-manifest.json'
        manifest.write_text(json.dumps({'schema_version': 1, 'entries': []}))
        store.create_problem(manifest_path=manifest)
        artifact = store.artifact(ORIGINAL.read_bytes(), 'application/xml')
        source = store.put('source', {'provider': 'retained_original_PMC6454709',
            'accession': 'PMC6454709', 'uri': 'https://doi.org/10.1186/s12858-019-0108-1',
            'artifact_ref': artifact, 'text_ref': None, 'request_ref': None,
            'version': None, 'retrieved_at': None}, origin='caller')['id']
        def remap(value):
            if isinstance(value, dict): return {key: remap(child) for key, child in value.items()}
            if isinstance(value, list): return [remap(child) for child in value]
            return source if value == old_ref else value
        selection = remap(selection)
        fields = measurement_comparison_operation_schema()['properties']['return_context']['properties']
        context = {role: {field: [] for field in spec['properties']} for role, spec in fields.items()}
        for role in ('left', 'right'):
            q = selection['quantities'][role]
            for name in ('organism', 'molecule'):
                selected = q['subject'][name]
                context[role]['subject.' + name] = [{'start': selected['start'], 'end': selected['end']}]
            selected = q['assay']['direct_endpoint']
            context[role]['assay.direct_endpoint'] = [{'start': selected['start'], 'end': selected['end']}]
            source_text = q['assay']['conditions']['quote']
            mass = '0.1\u2009μg G6PD enzyme' if role == 'left' else '0.5\u2009μg G6PD enzyme'
            selected = q['assay']['conditions']; offset = len(source_text[:source_text.index(mass)].encode())
            context[role]['assay.conditions'] = [{'start': selected['start'] + offset,
                'end': selected['start'] + offset + len(mass.encode())}]
            source_text = q['assay']['additional_differences']['quote']
            volume = '150\u2009μL' if role == 'left' else '1\u2009mL'
            selected = q['assay']['additional_differences']; offset = len(source_text[:source_text.index(volume)].encode())
            context[role]['assay.additional_differences'] = [{'start': selected['start'] + offset,
                'end': selected['start'] + offset + len(volume.encode())}]
        assertion_context = {name: [{'start': selection['assertion'][name]['start'],
            'end': selection['assertion'][name]['end']}] for name in ('molecule', 'functional_assertion')}
        args = {'version': 'literature_measurement_comparison_population_v2',
            'selection': selection, 'return_context': context,
            'return_assertion_context': assertion_context}
        assignment = {'version': 'literature_assignment_v1', 'source_refs': [source],
            'question_context_refs': [], REQUESTED: selection['requested_cells']}
        ctx = BindingContext('wst8-291', 'source-child', 'literature', (('literature', 'source-child'),),
            store.validate_scope(), assignment, {}, (source,))
        host = SimpleNamespace(store=store, run_id=ctx.run_id, tools=ToolRegistry(store))
        binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True,
            reference_parent_sources=[source])
        host.episode_bindings = EpisodeBindingRegistry((binding,))
        current, outcome, rows = selected_operation(store, ctx, args, binding, 'wst8-table3')
        by_name = {row['component']: row for row in rows}
        assert by_name['protocol_ratio']['cell']['value'] == float(Fraction(417, 496))
        assert by_name['common_ratio']['cell']['value'] is None
        assert by_name['protocol_ratio']['source_kind'] == 'primary_source'
        assert by_name['protocol_ratio']['assertion_context']['molecule']['fragments'][0]['text'] == 'G6PD'
        meanings = by_name['protocol_ratio']['role_meanings']
        detail = {role['role']: {item['field']: item['fragments'][0]['text'] for item in role['contexts']
            if item['fragments']} for role in meanings}
        assert detail['left']['assay.conditions'] == '0.1\u2009μg G6PD enzyme'
        assert detail['left']['assay.additional_differences'] == '150\u2009μL'
        assert detail['right']['assay.conditions'] == '0.5\u2009μg G6PD enzyme'
        assert detail['right']['assay.additional_differences'] == '1\u2009mL'
        saved = binding._measurement_comparison_repository().read(outcome['result']['sheet_ref'])
        assert saved['sheet']['axis'] == 'A105'
        assert saved['sheet']['annotation_credit'] is None
        assert current.received_record_refs[-1] == outcome['result']['sheet_ref']
        assert saved['original_implementation']['version'] == 'measurement_comparison_original_implementation_v2'
        source_record = store.get(outcome['result']['sheet_ref'])
        allowed = {source_record[name] for name in ('artifact_ref', 'request_ref')}
        assert tuple(store.db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()) == (0, 0, 0)
        store.close()
        store = None
        cold = Store.__new__(Store)
        cold.path, cold._savepoint = path, 0
        cold.db = sqlite3.connect((path / 'state.sqlite3').resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
        cold.db.row_factory = sqlite3.Row
        cold.db.execute('PRAGMA query_only=ON')
        try:
            original_get = cold.get_artifact
            cold.get_artifact = lambda ref: original_get(ref) if ref in allowed else (
                _ for _ in ()).throw(AssertionError('scientific source reread during cold reconstruction'))
            assert LiteratureMeasurementComparisonRepository(cold, ctx.run_id).read(
                outcome['result']['sheet_ref']) == saved
            assert cold.db.total_changes == 0
        finally:
            cold.db.close()
    finally:
        if store is not None:
            store.close()


def test_saved_v1_comparison_remains_readable_without_scientific_source_io():
    state = Path(__file__).resolve().parents[1] / (
        'verification/a105_measurement_comparison_binding_268/pytest_003/'
        'test_actual_parent_converted_s0/state')
    assert (state / 'state.sqlite3').is_file()
    cold = Store.__new__(Store)
    cold.path, cold._savepoint = state, 0
    cold.db = sqlite3.connect((state / 'state.sqlite3').resolve().as_uri() + '?mode=ro&immutable=1', uri=True)
    cold.db.row_factory = sqlite3.Row
    cold.db.execute('PRAGMA query_only=ON')
    try:
        operation = cold.db.execute(
            'SELECT run_id,outcome FROM literature_measurement_comparison_operations LIMIT 1').fetchone()
        reference = json.loads(operation['outcome'])['result']['sheet_ref']
        original_get = cold.get_artifact
        allowed = {cold.get(reference)[name] for name in ('artifact_ref', 'request_ref')}
        def saved_only(artifact_ref):
            assert artifact_ref in allowed, 'scientific source reread during reconstruction'
            return original_get(artifact_ref)
        cold.get_artifact = saved_only
        restored = LiteratureMeasurementComparisonRepository(cold, operation['run_id']).read(reference)
        assert restored['original_implementation']['version'] == 'measurement_comparison_original_implementation_v1'
        assert cold.db.total_changes == 0
    finally:
        cold.db.close()
