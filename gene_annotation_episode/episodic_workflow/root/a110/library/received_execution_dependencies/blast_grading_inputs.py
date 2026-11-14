from __future__ import annotations
from copy import deepcopy
import math
import re
_INT_MIN = {'query_from': 1, 'query_to': 1, 'hit_from': 1, 'hit_to': 1, 'identity': 0, 'positive': 0, 'align_len': 1, 'gaps': 0, 'num': 0, 'density': 0}
_SCORES = {'bit_score', 'score', 'evalue'}
_STRINGS = {'qseq', 'hseq', 'midline'}
STANDARD_TABULAR_FIELDS = ['qseqid', 'sseqid', 'pident', 'length', 'mismatch', 'gapopen', 'qstart', 'qend', 'sstart', 'send', 'evalue', 'bitscore']
_LABELS = {'query id': 'qseqid', 'query gi': 'qgi', 'query acc.': 'qacc', 'query acc.ver': 'qaccver', 'query length': 'qlen', 'subject id': 'sseqid', 'subject ids': 'sallseqid', 'subject gi': 'sgi', 'subject gis': 'sallgi', 'subject acc.': 'sacc', 'subject acc.ver': 'saccver', 'subject accs': 'sallacc', 'subject accs.': 'sallacc', 'subject length': 'slen', 'q. start': 'qstart', 'q. end': 'qend', 's. start': 'sstart', 's. end': 'send', 'query seq': 'qseq', 'subject seq': 'sseq', 'evalue': 'evalue', 'e-value': 'evalue', 'bit score': 'bitscore', 'score': 'score', 'alignment length': 'length', '% identity': 'pident', 'identical': 'nident', 'mismatches': 'mismatch', 'positives': 'positive', 'gap opens': 'gapopen', 'gaps': 'gaps', '% positives': 'ppos', 'query/sbjct frames': 'frames', 'query frame': 'qframe', 'sbjct frame': 'sframe', 'btop': 'btop', 'subject tax ids': 'staxids', 'subject sci names': 'sscinames', 'subject com names': 'scomnames', 'subject blast names': 'sblastnames', 'subject super kingdoms': 'sskingdoms', 'subject title': 'stitle', 'subject titles': 'salltitles', 'subject strand': 'sstrand', '% query coverage per subject': 'qcovs', '% query coverage per hsp': 'qcovhsp', '% query coverage per unique subject': 'qcovus'}
_TAB_HSP = {'bitscore': 'bit_score', 'score': 'score', 'evalue': 'evalue', 'nident': 'identity', 'positive': 'positive', 'length': 'align_len', 'gaps': 'gaps', 'qstart': 'query_from', 'qend': 'query_to', 'sstart': 'hit_from', 'send': 'hit_to', 'qframe': 'query_frame', 'sframe': 'hit_frame', 'qseq': 'qseq', 'sseq': 'hseq', 'pident': 'identity_percent', 'qcovhsp': 'query_coverage_percent', 'qcovs': 'query_subject_coverage_percent', 'qcovus': 'query_unique_subject_coverage_percent'}
_TAB_INTS = {'nident', 'positive', 'length', 'gaps', 'qstart', 'qend', 'sstart', 'send', 'qframe', 'sframe', 'qlen', 'slen', 'mismatch', 'gapopen'}
_TAB_NUMBERS = {'bitscore', 'score', 'evalue', 'pident', 'ppos', 'qcovs', 'qcovhsp', 'qcovus'}

def _issue(issues, code, **locator):
    issues.append({'code': code, **locator})

def _finite(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)

def _hsp(native, issues, **locator):
    if not isinstance(native, dict):
        _issue(issues, 'blast_hsp_object_required', **locator)
        return None
    result = deepcopy(native)
    for key, value in native.items():
        valid = True
        if key in _INT_MIN:
            valid = type(value) is int and value >= _INT_MIN[key]
        elif key in {'query_frame', 'hit_frame'}:
            valid = type(value) is int and -3 <= value <= 3
        elif key in _SCORES:
            valid = _finite(value) and (key != 'evalue' or value >= 0)
        elif key in _STRINGS:
            valid = isinstance(value, str)
        elif key in {'query_strand', 'hit_strand'}:
            valid = isinstance(value, str) and value in {'Plus', 'Minus'}
        if not valid:
            result.pop(key, None)
            _issue(issues, 'blast_hsp_field_invalid', field=key, **locator)
    missing = [key for key in ('query_from', 'query_to', 'hit_from', 'hit_to') if key not in result]
    if missing:
        _issue(issues, 'blast_hsp_coordinates_incomplete', fields=missing, **locator)
    return result

def _fields(fields):
    if not isinstance(fields, list) or not fields or any((not isinstance(x, str) or not x.strip() for x in fields)):
        raise ValueError('blast_tabular_fields_required')
    result = []
    for name in fields:
        name = _LABELS.get(name.strip().lower(), name.strip().lower())
        result.extend(STANDARD_TABULAR_FIELDS if name == 'std' else [name])
    if len(set(result)) != len(result):
        raise ValueError('blast_tabular_duplicate_fields')
    return result

def _tab_number(value, field):
    if value in {'', 'N/A', 'NA', 'n/a'}:
        return None
    if field in _TAB_INTS:
        if re.fullmatch('[+-]?\\d+', value) is None:
            raise ValueError('integer_required')
        number = int(value)
        if field in {'qframe', 'sframe'}:
            if not -3 <= number <= 3:
                raise ValueError('frame_invalid')
        elif field in {'qlen', 'slen', 'qstart', 'qend', 'sstart', 'send', 'length'}:
            if number <= 0:
                raise ValueError('positive_integer_required')
        elif number < 0:
            raise ValueError('nonnegative_integer_required')
        return number
    number = float(value)
    if not math.isfinite(number) or (field == 'evalue' and number < 0):
        raise ValueError('finite_number_required')
    if field in {'pident', 'ppos', 'qcovs', 'qcovhsp', 'qcovus'} and (not 0 <= number <= 100):
        raise ValueError('percentage_outside_range')
    return number
