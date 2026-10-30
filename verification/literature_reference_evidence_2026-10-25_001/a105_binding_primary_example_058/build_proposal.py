"""Own058 source nominations and code-only schema authentication, no Episode.

Image quotations are this investigating agent's controlled visual transcription.
They are not OCR output or evidence of actual configured-model extraction.
"""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = OUT.parent
CASE = BASE / 'a105_binding_case_042'
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.literature_binding_interaction_inputs import ROLES, ID_FIELDS, binding_interaction_arguments_schema
from gene_annotation_episode.literature_binding_interaction_storage import binding_interaction_cells_schema
from gene_annotation_episode.domain import validate_schema


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(name, value):
    with (OUT / name).open('x') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def main():
    # Retained bytes already inspected above, now used only to bind nominations.
    text_raw = (CASE / 'primary_text.txt').read_bytes()
    text = text_raw.decode()
    source, image_source = 'source_primary_058_proposal', 'source_table3_058_proposal'
    def witness(quote, start=0):
        at = text.index(quote, start)
        return {'kind': 'text', 'source_ref': source, 'representation': 'text',
            'start': len(text[:at].encode()), 'end': len(text[:at + len(quote)].encode()), 'quote': quote}
    def iw(region, quote):
        return {'kind': 'image', 'image_id': 'table3', 'region': list(region), 'quote': quote}
    def meaning(label, canonical, *support):
        return {'status': 'known', 'label': label, 'canonical_witness': canonical,
            'witnesses': [canonical, *support]}
    def enum(value, *support):
        return {'value': value, 'witnesses': list(support)}
    def literal(selected):
        return {'status': 'exact', 'candidates': [selected], 'fragments': []}
    assay = witness('Equilibrium competition fluorescence assays')
    paragraph_at = text.index('Equilibrium competition fluorescence assays')
    method = witness(text[paragraph_at:text.index('\n', paragraph_at)])
    endpoint = witness('The IC50 was determined by fitting a four parameter logistic curve to the data (SigmaPlot 12.0).', paragraph_at)
    definition = witness('The concentration of unlabeled mutant competitor required to decrease maximum binding (Amax) to labeled hya DNA by a factor of 0.5 (IC50).')
    normal = witness('The fraction bound was determined using the equation (A − Afree)/(Abound − Afree), where A is the anisotropy of a sample, Afree is the anisotropy of the DNA in the absence of IscR, and Abound is the anisotropy in the absence of competitor.', paragraph_at)
    nM = witness('nM', paragraph_at)
    uncertainty = witness('The standard deviation is derived from fitting a four-parameter logistic curve to the average of at least three independent titration experiments.')
    count = witness('at least three', text.index(uncertainty['quote']))
    repeat = witness('All assays to generate binding isotherms and competition data were repeated on at least three independent occasions.', paragraph_at)
    tracer = witness('5 nM Texas Red labeled wild-type hya', paragraph_at)
    wt, mutant = witness('22 nM apo-IscR', paragraph_at), witness('20 nM apo-IscR-E43A', paragraph_at)
    self_ligand = iw([31,62,99,83], 'hya')
    mutation_ligands = {'7C_to_G': iw([17,111,118,133], 'hya (7C to G)'),
        '8C_to_G': iw([17,136,118,158], 'hya (8C to G)')}
    rows = {
        'WT_self': {'region': [403,62,480,85], 'expression_region': [418,64,462,82], 'quote': '32 ± 2'},
        'E43A_self': {'region': [512,62,585,85], 'expression_region': [521,64,570,82], 'quote': '11 ± 1'},
        'WT_7C_to_G': {'region': [398,111,483,134], 'expression_region': [406,112,446,131], 'quote': '>510'},
        'E43A_7C_to_G': {'region': [511,111,590,134], 'expression_region': [522,112,573,131], 'quote': '17 ± 3'},
        'WT_8C_to_G': {'region': [398,136,483,159], 'expression_region': [406,137,446,156], 'quote': '>740'},
        'E43A_8C_to_G': {'region': [511,136,590,159], 'expression_region': [528,137,573,156], 'quote': '7 ± 3'},
    }
    cases = {}
    for changed in mutation_ligands:
        role_rows = ('WT_self', 'WT_' + changed, 'E43A_self', 'E43A_' + changed)
        roles = {}
        for i, (role, row_name) in enumerate(zip(ROLES, role_rows)):
            record = rows[row_name]
            protein = wt if i < 2 else mutant
            ligand = self_ligand if i % 2 == 0 else mutation_ligands[changed]
            cell = iw(record['region'], record['quote'])
            definitions = {name: {'status': 'unknown', 'label': None, 'witnesses': [], 'canonical_witness': None} for name in ID_FIELDS}
            definitions.update(
                subject=meaning('apo-WT IscR' if i < 2 else 'apo-IscR-E43A', protein, method),
                construct=meaning('source WT binding construct; boundaries unresolved' if i < 2 else 'source E43A binding construct; boundaries unresolved', protein, method),
                state=meaning('apo', protein, method),
                experiment=meaning('source Table3 equilibrium competition fluorescence experiment', assay, method),
                ligand=meaning('hya self competitor' if i % 2 == 0 else changed + ' hya competitor', ligand, method),
                tracer=meaning('Texas Red labeled wild-type hya', tracer, method),
                readout=meaning('four-parameter logistic competition IC50', endpoint, definition),
                normalization=meaning('fraction bound relative to no-protein and no-competitor anisotropy baselines', normal),
                conditions=meaning('reported WT nominal input22nM' if i < 2 else 'reported E43A nominal input20nM', protein, method),
                parameter_definition=meaning('unlabeled competitor concentration at half maximum normalized binding', definition, endpoint))
            roles[role] = {'parameter_kind': enum('ic50', endpoint, definition), 'definitions': definitions,
                'physical_fit': {'canonical_witness': cell, 'witnesses': [cell, uncertainty, endpoint]},
                'measurement': {'image_id': 'table3', 'cell_region': record['region'],
                    'expression': literal(iw(record['expression_region'], record['quote'])), 'unit': literal(nM)},
                'uncertainty': {'statistic': enum('sd', uncertainty), 'basis': enum('fit_to_averaged_curve', uncertainty),
                    'repetition_basis': enum('assay_occasions', repeat, uncertainty), 'interval': None,
                    'confidence_level': None, 'exact_count': None, 'minimum_count': literal(count)}}
        args = {'version': 'binding_interaction_source_inputs_v1', 'source_ref': source, 'source_kind': 'primary_source',
            'images': [{'image_id': 'table3', 'source_ref': image_source, 'original_source_ref': image_source, 'mapping': None}],
            'parameter_kind': enum('ic50', endpoint, definition), 'comparison_scope': 'reported_protocols', 'roles': roles,
            'relationships': {name: {'status': 'not_matched' if name == 'common_conditions' else 'supported',
                'witnesses': [method, definition] if name == 'common_conditions' else [method, definition, self_ligand, mutation_ligands[changed]]}
                for name in ('within_reference_subject', 'within_test_subject', 'ligand_correspondence', 'parameter_definition', 'separate_assays', 'common_conditions')}}
        validate_schema(args, binding_interaction_arguments_schema())
        cases[changed] = args
    save('PROPOSED_SOURCE_NOMINATIONS_001.json', {'scope': 'Controlled fixture nominations with placeholder source IDs; not executed or model-derived',
        'cases': cases, 'original_table_dimensions': [600,221], 'inspected_transcriptions': rows})
    # Verify the complete expanded schema by its actual producing implementation.
    stored_schema = json.loads((BASE / 'a105_binding_native_design_052/RETURN_SCHEMA_005.json').read_bytes())
    actual_schema = binding_interaction_cells_schema()
    assert stored_schema == actual_schema
    # Lossless DAG factoring: every repeated container refers to the same exact
    # finite node. This is an inspection artifact, not a runtime schema change.
    definitions, identifiers = {}, {}
    def factor(value):
        if not isinstance(value, (dict,list)):
            return value
        key = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
        if key not in identifiers:
            name = 'n' + str(len(identifiers))
            identifiers[key] = name
            definitions[name] = ({k: factor(v) for k,v in value.items()} if isinstance(value,dict) else [factor(v) for v in value])
        return {'$node': identifiers[key]}
    tree = factor(actual_schema)
    def expand(value):
        if isinstance(value,dict):
            return expand(definitions[value['$node']]) if set(value)=={'$node'} else {k: expand(v) for k,v in value.items()}
        return [expand(v) for v in value] if isinstance(value,list) else value
    assert expand(tree) == actual_schema
    save('RETURN_SCHEMA_DAG_001.json', {'root': tree, 'nodes': definitions})
    arithmetic = []
    for name, wt_value, mutant_value in (('7C_to_G',510,17),('8C_to_G',740,7)):
        wt_ratio = Fraction(wt_value,32)
        mutant_ratio = Fraction(mutant_value,11)
        ratio = wt_ratio / mutant_ratio
        arithmetic.append({'comparison':name,'reference_subject_ratio':{'threshold':float(wt_ratio),'relation':'gt'},
            'test_subject_ratio':{'value':float(mutant_ratio),'relation':'eq'},
            'interaction_ratio':{'threshold':float(ratio),'relation':'gt'},
            'log_interaction':{'threshold':math.log(ratio.numerator)-math.log(ratio.denominator),'relation':'gt'},
            'bound_kind':'reported_limit_arithmetic','model_variance_and_profile':None,
            'meaning':'Research-only expected arithmetic for proposed runtime assertions; no calculator or native operation executed'})
    save('EXPECTED_ARITHMETIC_001.json', arithmetic)
    files = ['primary.html','primary_text.txt','table3.jpg']
    save('SOURCE_IDENTITIES_001.json', {name:{'sha256':sha((CASE/name).read_bytes()),'bytes':(CASE/name).stat().st_size} for name in files})
    save('PREPARATION_RECEIPT_001.json', {'arguments_structurally_validated':2,'expanded_return_schema_exact_to_factory':True,
        'expanded_schema_bytes':(BASE/'a105_binding_native_design_052/RETURN_SCHEMA_005.json').stat().st_size,
        'lossless_schema_node_count':len(definitions),'lossless_schema_roundtrip_exact':True,
        'source_reader_calls':0,'calculator_calls':0,'Store_or_Episode_runs':0,'model_calls':0,'observations':0})
    print(json.dumps({'status':'proposal_prepared','case_count':len(cases),'schema_nodes':len(definitions),'episodes':0,'model_calls':0,'observations':0}))


if __name__ == '__main__':
    main()
