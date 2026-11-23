"""The grader and the sheet of A102's ``partner_cofolding``: does a proposed ligand fit the target, as Chai-1 co-folds them (design note
``docs/plan/designs/a102_partner_cofolding.md``). A result is structural compatibility as the model predicts it, never measured binding.

INPUT. ``scores.json`` of the job (``tools/.../partner_cofolding_job``): ``{component id: [per sample {aggregate_score, ptm, iptm,
per_chain_pair_iptm, has_inter_chain_clashes, chain_chain_clashes}]}``, the samples of one ligand's co-folding of the target.

THE RULE. A sample's value is its ``iptm`` (the interface score of the two chains), or 0 when ``has_inter_chain_clashes`` is true. A
candidate is ``ligand:<component id>`` (the name ``partner_contacts`` and ``ligand_transplants`` give a ligand); its value is the MEAN
of its samples' values (the samples are replicates of one test). ``ptm``, ``aggregate_score`` and the clash matrix are kept as facts
and weigh nothing. The grader holds no threshold.

The sheet is controlled data: numbers, booleans, chemical component ids and the schema and provider names."""
import math

SCHEMA = 'a102_partner_cofolding_sheet_v1'
PROVIDER = 'partner_cofolding'
SAMPLE_KEYS = {'aggregate_score', 'ptm', 'iptm', 'per_chain_pair_iptm', 'has_inter_chain_clashes', 'chain_chain_clashes'}


def _require(condition, code):
    if not condition:
        raise ValueError('a102_partner_cofolding_' + code)


def sample_value(sample):
    """The value of one sample: its ``iptm``, 0 when it has inter-chain clashes."""
    return 0.0 if sample['has_inter_chain_clashes'] else sample['iptm']


def grade_partner_cofolding(scores_json):
    """The sheet of one ``scores.json`` (``{component id: [samples]}``), candidates in the order of the ligands."""
    _require(type(scores_json) is dict and scores_json, 'scores_empty')
    candidates = []
    for component_id, samples in scores_json.items():
        _require(type(samples) is list and samples, 'ligand_without_samples')
        for sample in samples:
            _require(set(sample) == SAMPLE_KEYS, 'sample_keys_differ')
            _require(type(sample['has_inter_chain_clashes']) is bool, 'clash_flag_not_boolean')
        rows = [{'sample': index, 'iptm': sample['iptm'], 'ptm': sample['ptm'], 'aggregate_score': sample['aggregate_score'],
                 'has_inter_chain_clashes': sample['has_inter_chain_clashes'], 'chain_chain_clashes': sample['chain_chain_clashes'],
                 'per_chain_pair_iptm': sample['per_chain_pair_iptm'], 'value': sample_value(sample)}
                for index, sample in enumerate(samples)]
        candidates.append({'candidate': 'ligand:' + component_id, 'kind': 'ligand', 'identifier': component_id,
                           'sample_count': len(rows), 'value': math.fsum(row['value'] for row in rows) / len(rows),
                           'mean_ptm': math.fsum(row['ptm'] for row in rows) / len(rows),
                           'mean_aggregate_score': math.fsum(row['aggregate_score'] for row in rows) / len(rows),
                           'clashing_sample_count': sum(row['has_inter_chain_clashes'] for row in rows), 'rows': rows})
    return {'schema': SCHEMA, 'provider': PROVIDER, 'ligand_count': len(candidates), 'candidates_measured': len(candidates),
            'candidates': candidates}


__all__ = ['PROVIDER', 'SAMPLE_KEYS', 'SCHEMA', 'grade_partner_cofolding', 'sample_value']
