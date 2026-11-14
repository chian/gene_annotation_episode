"""Private original genome-alignment presentation reference codec."""
from urllib.parse import quote, unquote

PREFIX = 'bvbrc_genome_alignment_bundle_'
REFERENCE_KINDS = ('field', 'request', 'document', 'population', 'method', 'file',
    'record', 'member', 'transformation', 'role', 'requirement', 'reason', 'qualification')

def _require(condition, code):
    if not condition:
        raise ValueError(PREFIX + code)


def encode_reference(kind: str, analysis_id: str, identity: str) -> str:
    _require(type(kind) is str and kind in REFERENCE_KINDS, 'reference_kind_unknown')
    _require(type(analysis_id) is str and bool(analysis_id) and type(identity) is str and bool(identity), 'reference_invalid')
    try:
        return 'bvbrc_genome_alignment_' + kind + ':' + quote(analysis_id, safe='') + '/' + quote(identity, safe='')
    except UnicodeError as error:
        raise ValueError(PREFIX + 'reference_invalid') from error


def decode_reference(reference: str) -> tuple[str, str, str]:
    _require(type(reference) is str and reference.startswith('bvbrc_genome_alignment_'), 'reference_invalid')
    prefix, colon, rest = reference.partition(':')
    _require(bool(colon) and rest.count('/') == 1, 'reference_invalid')
    kind = prefix[len('bvbrc_genome_alignment_'):]
    _require(kind in REFERENCE_KINDS, 'reference_kind_unknown')
    try:
        analysis_id, identity = (unquote(x, errors='strict') for x in rest.split('/'))
    except UnicodeError as error:
        raise ValueError(PREFIX + 'reference_invalid') from error
    _require(encode_reference(kind, analysis_id, identity) == reference, 'reference_noncanonical')
    return kind, analysis_id, identity


