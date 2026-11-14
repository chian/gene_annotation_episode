from __future__ import annotations
import re
COMPLETENESS = ('complete', 'partial', 'truncated', 'unknown')

def fail(code):
    raise ValueError('phylogeny_' + code)

def require(condition, code):
    if not condition:
        fail(code)

def shape(value, keys, code='operand_shape_invalid'):
    require(type(value) is dict and set(value) == set(keys), code)

def text(value, *, nullable=False, empty=False):
    require(nullable and value is None or (type(value) is str and (empty or bool(value))), 'text_invalid')

def integer(value, *, nullable=False, minimum=0):
    require(nullable and value is None or (type(value) is int and value >= minimum), 'integer_invalid')

def sequence(value, *, stored=False):
    require(type(value) is list if stored else type(value) in (list, tuple), 'array_invalid')

def digest(value, *, nullable=False):
    require(nullable and value is None or (type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None), 'digest_invalid')

def evidence(value):
    sequence(value, stored=True)
    for item in value:
        shape(item, {'content', 'pointer'}, 'evidence_shape_invalid')
        content = item['content']
        shape(content, {'source_ref', 'artifact_field', 'artifact_ref', 'sha256', 'byte_count'}, 'evidence_shape_invalid')
        text(content['source_ref'])
        text(content['artifact_ref'])
        require(content['artifact_field'] in ('artifact_ref', 'text_ref', 'stdout_ref', 'stderr_ref'), 'evidence_invalid')
        digest(content['sha256'])
        integer(content['byte_count'])
        text(item['pointer'], empty=True)
        require((item['pointer'] == '' or item['pointer'].startswith('/')) and re.search('~(?![01])', item['pointer']) is None, 'evidence_pointer_invalid')

def location(value):
    shape(value, {'artifact', 'byte_start_0based', 'byte_end_0based_exclusive', 'line_start_1based', 'line_end_1based_inclusive', 'xml_path'}, 'source_location_invalid')
    artifact = value['artifact']
    shape(artifact, {'raw_artifact_ref', 'source_ref', 'sha256'}, 'source_location_invalid')
    text(artifact['raw_artifact_ref'])
    text(artifact['source_ref'])
    digest(artifact['sha256'])
    present = False
    for start, end, minimum in (('byte_start_0based', 'byte_end_0based_exclusive', 0), ('line_start_1based', 'line_end_1based_inclusive', 1)):
        a, b = (value[start], value[end])
        if a is None and b is None:
            continue
        integer(a, minimum=minimum)
        integer(b, minimum=minimum)
        require(b >= a, 'source_location_invalid')
        present = True
    if value['xml_path'] is not None:
        text(value['xml_path'])
        require(value['xml_path'].startswith('/'), 'source_location_invalid')
        present = True
    require(present, 'source_location_missing')
