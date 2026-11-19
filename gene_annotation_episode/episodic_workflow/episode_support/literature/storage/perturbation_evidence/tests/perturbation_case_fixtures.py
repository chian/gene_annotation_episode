"""Constructed A106 perturbation cases on the scoped store of a running episode, and a commissioner's typed receipt of their cells.

Synthetic or cited-source inputs for repository tests; they make no scientific
claim. A literature episode populates its sheet through its repository and
returns the selected cells in its commissioner's typed form (C5); the parent
then receives exactly those cells.
"""
from pathlib import Path

from gene_annotation_episode.episodic_workflow.episode_support.forms.perturbation_evidence.communication import form_with_facts, validate_form
from gene_annotation_episode.episodic_workflow.episode_support.records.perturbation_evidence.domain import canonical
from gene_annotation_episode.episodic_workflow.episode_support.literature.inputs.perturbation_evidence.literature_perturbation_inputs import LITERAL_FIELDS, PRIMITIVE_ORDER
from gene_annotation_episode.episodic_workflow.episode_support.literature.storage.literature_repositories import LiteratureContext

BASE = Path(__file__).parent / 'fixtures'
PRIMARY = BASE / 'primary_cas2/PMC4075942.xml'
COMPONENTS = ['symmetric_effect', 'restoration_fraction_raw', 'reference_restoration_index', 'reference_index_lower']


def source(store, data, *, parents=()):
    artifact = store.artifact(data, 'application/octet-stream')
    return store.put('source', {'provider': 'source_perturbation_example', 'accession': None, 'uri': None,
        'artifact_ref': artifact, 'text_ref': None, 'request_ref': None, 'version': None,
        'retrieved_at': None, 'parent_source_refs': list(parents)}, origin='caller')


def witness(ref, raw, quote):
    token = quote.encode('utf-8')
    start = raw.index(token)
    return {'source_ref': ref, 'representation': 'original', 'start': start,
            'end': start+len(token), 'quote': quote}


def setup_case(ctx, *, primary=False):
    store = ctx.store
    raw = PRIMARY.read_bytes() if primary else (
        b'SyntheticProtein in recipient cells: reference, perturbed and restored arms measure '
        b'the same calibrated endpoint. Restored protein amount is a nuisance comparison; '
        b'supplied controls bound alternative endpoint contributions.')
    root = source(store, raw)
    ref = root['id']
    def w(quote):
        return witness(ref, raw, quote)
    literals = dict.fromkeys(LITERAL_FIELDS)
    if primary:
        literals.update(molecule=w('Cas2'), recipient=w('BL21-AI'), donor=w('MG1655'),
            partner=w('Cas1'), endpoint=w('PCR'),
            normalization=w('OD<sub>600</sub> measurements'))
        interpretation = [w('lack all <italic toggle="yes">cas</italic> genes'), w('PCR')]
    else:
        literals.update(molecule=w('SyntheticProtein'), recipient=w('recipient cells'),
            reference_arm=w('reference'), perturbed_arm=w('perturbed'), restored_arm=w('restored'),
            endpoint=w('calibrated endpoint'))
        interpretation = [w(raw.decode('utf-8'))]
    data_ref = None
    refs = [ref]
    if not primary:
        values = dict(zip(PRIMITIVE_ORDER, [100., 20., 90., 100., 90., 8., 7.]))
        data = {'version': 'a106_source_measurements_v1', 'endpoint_unit': 'events_per_100000_cells',
            'exposure_unit': 'molecules_per_cell', 'origin': 'synthetic', 'uncertainty_basis': 'unreported',
            'measurements': {role: {'value': values[role], 'measurement_id': role+'-observed'} for role in PRIMITIVE_ORDER}}
        data_source = source(store, canonical(data), parents=[ref])
        data_ref = data_source['id']
        refs.append(data_ref)
    args = {'source_ref': ref, 'data_source_ref': data_ref,
        'source_kind': 'primary_source' if primary else 'synthetic_fixture', 'literals': literals,
        'design': 'cas_free_reconstitution' if primary else 'selective_perturbation_restoration',
        'measurement_status': 'qualitative_only' if primary else 'validated_ratio_scale',
        'same_endpoint_scope': 'unknown' if primary else 'yes', 'amount_role': 'unknown' if primary else 'nuisance',
        'orientation': None if primary else 1, 'interpretation_witnesses': interpretation}
    assignment = {'version': 'literature_assignment_v1', 'question_context_refs': [],
                  'source_refs': refs, 'requested_perturbation_components': COMPONENTS}
    context = LiteratureContext(ctx.run_id, ctx.episode_id, 'literature',
        (('literature', 'fixture'),), store.validate_scope({'subject_refs': store.problem()['subject_refs']}), assignment, {}, tuple(refs))
    return store, context, args


def returned_form(projection, context, sheet_refs, schema, components):
    """The episode's typed return: its own saved cells under the form's recorded field, checked against the form."""
    (name, node), = schema['properties'].items()
    rows = projection.project_cells(list(sheet_refs), permitted_record_refs=context.received_record_refs,
                                    components=components)
    form = form_with_facts({}, schema, {node['x-source']: rows})
    received = set(context.received_record_refs)
    validate_form(form, schema, lambda reference, namespace: reference in received)
    return form
