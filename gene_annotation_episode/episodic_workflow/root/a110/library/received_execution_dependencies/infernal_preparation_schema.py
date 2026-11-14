from __future__ import annotations
import math
PROGRAM_MODES = {'cmbuild': frozenset({'build', 'refine'}), 'cmcalibrate': frozenset({'calibrate', 'forecast', 'memory_estimate', 'split_commands', 'partition_scores', 'merge_scores'}), 'cmconvert': frozenset({'ascii', 'binary', 'legacy_ascii', 'maximum_likelihood_hmm', 'filter_hmm'}), 'cmemit': frozenset({'sample_unaligned', 'sample_aligned', 'consensus'}), 'cmfetch': frozenset({'single_key', 'key_file', 'index'}), 'cmpress': frozenset({'press'}), 'cmstat': frozenset({'summary', 'scores_at_evalue', 'scores_at_pvalue', 'evalues_at_score', 'evalues_at_ga', 'evalues_at_nc', 'evalues_at_tc'})}
VALUE_STATES = frozenset({'present', 'missing', 'not_measured', 'failed', 'truncated', 'incompatible', 'invalid'})
VALUE_BASES = frozenset({'native_reported', 'model_header', 'derived', 'native_prediction'})
UNITS = frozenset({'count', 'nt', 'column', 'bit', 'bit_per_position', 'inverse_bit', 'fraction', 'second', 'MB', 'Mnt', 'byte', 'log2_odds', 'dimensionless', 'index', 'expected_count'})

def require_finite_json(item):
    """Accept JSON data only, without coercing keys, tuples or NaN/Infinity."""
    if type(item) is dict:
        if any((type(key) is not str for key in item)):
            raise ValueError('infernal_preparation_json_key')
        for child in item.values():
            require_finite_json(child)
    elif type(item) is list:
        for child in item:
            require_finite_json(child)
    elif type(item) is float:
        if not math.isfinite(item):
            raise ValueError('infernal_preparation_nonfinite_number')
    elif item is not None and type(item) not in (str, int, bool):
        raise ValueError('infernal_preparation_non_json_value')
