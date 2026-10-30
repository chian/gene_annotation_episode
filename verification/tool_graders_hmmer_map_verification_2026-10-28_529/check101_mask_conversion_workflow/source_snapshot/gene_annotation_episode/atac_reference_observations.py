"""Pure parsing of supplied, retained BAM SAM-text reference observations.

LN is the native reference length in bp, with no statistical denominator. M5 is
the optional sequence MD5, never a SHA256 or an annotation confidence component.
The caller owns BAM inspection and exact byte retention. This parser never
opens a path, invokes a BAM reader or compares a dictionary with a reference.
"""
from __future__ import annotations

from collections import defaultdict
import re
from typing import BinaryIO

from .atac_differential_contracts import AtacArtifact, ParsedAtacBamReference, issue
from .atac_differential_inputs import _chunks, _lines, _native_issue, _number, _seal, _start, _stats


def _reference_row(fields, ordinal, locator, artifact, key):
    issues = []
    tags = defaultdict(list)
    for token in fields[1:]:
        name, separator, value = token.partition(':')
        # Keep malformed occurrences of a required tag in its occurrence set;
        # a later valid token must not silently replace it.
        if not separator or re.fullmatch('[A-Za-z][A-Za-z0-9]', name) is None:
            issues.append(_native_issue('metadata_conflict', artifact, key, ordinal, locator,
                                        name if name in ('SN', 'LN', 'M5') else 'original_fields',
                                        'original_native_metadata'))
        if name in ('SN', 'LN', 'M5'):
            tags[name].append(value if separator else None)
    values = {}
    for tag, field in (('SN', 'chromosome'), ('LN', 'length_bp'), ('M5', 'sequence_md5')):
        tokens = tags[tag]
        values[field] = None
        if not tokens:
            if tag != 'M5':
                issues.append(_native_issue('metadata_missing', artifact, key, ordinal, locator,
                                            field, 'original_native_metadata'))
            continue
        if len(tokens) != 1:
            issues.append(_native_issue('metadata_conflict', artifact, key, ordinal, locator,
                                        field, 'original_native_metadata'))
            continue
        token = tokens[0]
        if token is None:
            continue
        if tag == 'LN':
            values[field] = _number(token, issues, artifact, key, ordinal, locator, field,
                                    integer=True, minimum=1)
        elif tag == 'SN':
            if token and token[0] not in '*=' and all(33 <= ord(c) <= 126 for c in token):
                values[field] = token
            else:
                issues.append(_native_issue('metadata_conflict', artifact, key, ordinal, locator,
                                            field, 'original_native_metadata'))
        elif re.fullmatch('[0-9a-fA-F]{32}', token):
            values[field] = token
        else:
            issues.append(_native_issue('metadata_conflict', artifact, key, ordinal, locator,
                                        field, 'original_native_metadata'))
    return dict(row_ordinal=ordinal, locator=locator, original_fields=fields, **values), issues


def parse_atac_bam_reference(content: bytes | BinaryIO | None, *, artifact: AtacArtifact,
                             callpeak_run_key: str, input_ordinal: int,
                             input_artifact_ref: str) -> ParsedAtacBamReference:
    """Preserve each @SQ occurrence, its exact tokens and source-byte locator.

    Repeated SN/LN/M5 fields produce no arbitrarily selected value. Duplicate
    chromosome rows remain separate, qualified occurrences. Absent M5 means
    unknown sequence identity. Stream failures retain complete preceding lines
    with the common parser's partial-byte identity and extent semantics.
    """
    if (type(callpeak_run_key) is not str or not callpeak_run_key
            or type(input_ordinal) is not int or input_ordinal < 0
            or type(input_artifact_ref) is not str or not input_artifact_ref):
        raise ValueError('invalid_atac_bam_reference_binding')
    try:
        callpeak_run_key.encode('utf-8')
        input_artifact_ref.encode('utf-8')
    except UnicodeEncodeError as error:
        raise ValueError('invalid_atac_bam_reference_binding') from error
    key = callpeak_run_key + ':input:' + str(input_ordinal)
    result = _start(artifact, key, 'atac_bam_reference_parsed_v1', 'sam_header_text',
                    missing=content is None)
    result.update(callpeak_run_key=callpeak_run_key, input_ordinal=input_ordinal,
                  input_artifact_ref=input_artifact_ref)
    if content is None:
        return result
    stats, malformed, chromosomes = _stats(), set(), defaultdict(list)
    read_failed = False
    try:
        for raw, locator in _lines(_chunks(content), stats):
            ordinal = stats['data']
            try:
                text = raw.removesuffix(b'\n').removesuffix(b'\r').decode('utf-8')
            except UnicodeDecodeError:
                fields = None
                row_issues = [_native_issue('invalid_utf8', artifact, key, ordinal, locator)]
            else:
                fields = text.split('\t')
                if fields[0] in ('@HD', '@RG', '@PG', '@CO'):
                    result['headers'].append(dict(locator=locator, kind='sam_header', text=text))
                    continue
                if not text or text.isspace():
                    result['headers'].append(dict(locator=locator, kind='blank', text=text))
                    continue
                row_issues = []
                if fields[0] != '@SQ':
                    row_issues.append(_native_issue('metadata_conflict', artifact, key, ordinal, locator,
                                                    'sam_header', 'original_native_metadata'))
            stats['data'] += 1
            if fields is None or fields[0] != '@SQ':
                result['invalid_records'].append(dict(row_ordinal=ordinal, locator=locator,
                    fields=fields, reason_codes=[item['code'] for item in row_issues]))
            else:
                row, row_issues = _reference_row(fields, ordinal, locator, artifact, key)
                result['rows'].append(row)
                result['readable_data_row_count'] += 1
                if row['chromosome'] is not None:
                    chromosomes[row['chromosome']].append(row)
            if row_issues:
                malformed.add(ordinal)
                result['issues'].extend(row_issues)
    except OSError:
        read_failed = True
        result['issues'].append(_native_issue('stream_read_failed', artifact, key,
                                              requirement='complete_artifact'))
    for rows in chromosomes.values():
        if len(rows) > 1:
            ordinals = [row['row_ordinal'] for row in rows]
            malformed.update(ordinals)
            result['issues'].append(issue('duplicate_record', artifact['artifact_ref'], key,
                row_ordinals=ordinals, locations=[row['locator'] for row in rows],
                field='chromosome', requirement='original_native_metadata'))
    if not result['rows']:
        result['issues'].append(_native_issue('metadata_missing', artifact, key,
                                              field='SQ', requirement='original_native_metadata'))
    result['malformed_data_row_count'] = len(malformed)
    if (malformed or not result['rows']) and result['state']['format'] != 'unsupported':
        result['state']['format'] = 'malformed'
    return _seal(result, stats, read_failed=read_failed)


__all__ = ['parse_atac_bam_reference']
