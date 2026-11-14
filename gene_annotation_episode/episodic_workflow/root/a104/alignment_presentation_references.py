"""A104 private admitted-alignment reference codec for presentation."""
from urllib.parse import quote, unquote

REFERENCE_KINDS = ('field', 'alignment', 'member', 'population', 'category', 'group',
    'tree', 'split', 'function', 'taxon', 'comparison', 'test', 'family', 'method',
    'transformation', 'role', 'requirement', 'reason', 'xmfa_document', 'xmfa_file', 'xmfa_record')

def require(condition, code='shape_invalid'):
    if not condition:
        raise ValueError('bvbrc_alignment_bundle_' + code)


def encode_reference(kind: str, analysis_id: str, identifier: str) -> str:
    require(kind in REFERENCE_KINDS and type(analysis_id) is str and bool(analysis_id)
        and type(identifier) is str and bool(identifier), 'reference_invalid')
    require(kind not in ('requirement', 'reason') or analysis_id == '@requirements', 'reference_scope_invalid')
    try:
        return 'bvbrc_alignment_' + kind + ':' + quote(analysis_id, safe='') + '/' + quote(identifier, safe='')
    except UnicodeError as exc:
        raise ValueError('bvbrc_alignment_bundle_reference_invalid') from exc


def decode_reference(reference: str) -> tuple[str, str, str]:
    require(type(reference) is str and reference.startswith('bvbrc_alignment_'), 'reference_invalid')
    prefix, separator, rest = reference.partition(':')
    parts = rest.split('/')
    require(separator and len(parts) == 2, 'reference_invalid')
    try:
        kind = prefix.removeprefix('bvbrc_alignment_')
        aid, identity = (unquote(part, encoding='utf-8', errors='strict') for part in parts)
    except UnicodeError as exc:
        raise ValueError('bvbrc_alignment_bundle_reference_invalid') from exc
    require(encode_reference(kind, aid, identity) == reference, 'reference_noncanonical')
    return kind, aid, identity


