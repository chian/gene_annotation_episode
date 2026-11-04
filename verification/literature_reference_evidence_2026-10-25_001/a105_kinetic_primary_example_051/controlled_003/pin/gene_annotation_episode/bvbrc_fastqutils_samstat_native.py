"""Version-aware SAMstat dispatch over supplied, content-bound HTML bytes."""
from __future__ import annotations

from html.parser import HTMLParser
import re

from .bvbrc_fastqutils_contracts import FastqUtilsContractError, checked_bytes, validate_contract
from .bvbrc_fastqutils_fastqc_reader import _Report

_FORMATS = {'samstat_html', 'samstat_html_2_2_3', 'samstat_html_2_5_0', 'samstat_bvbrc_error_html'}
_VERSION = re.compile(r'SAMStat (?:version )?([0-9]+\.[0-9]+\.[0-9]+)(?![0-9A-Za-z])')
_FAILURE = 'Your samstat job had a segfault error. The results could not be displayed.'


class _Probe(HTMLParser):
    """Labels only; scripts/styles remain inert and cannot assert a version."""
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.lines = [0]
        for m in re.finditer('\n', text):
            self.lines.append(m.end())
        self.stack = []
        self.versions = []
        self.failure = False
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag not in {'meta', 'link', 'br', 'hr', 'img', 'input', 'path', 'rect', 'line', 'circle'}:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self.stack:
            del self.stack[len(self.stack)-1-self.stack[::-1].index(tag):]

    def handle_data(self, value):
        if any(t in self.stack for t in ('script', 'style')):
            return
        if self.stack and self.stack[-1] == 'h2' and value.strip() == _FAILURE:
            self.failure = True
        if 'p' not in self.stack:
            return
        line, offset = self.getpos()
        start = self.lines[line-1] + offset
        for match in _VERSION.finditer(value):
            a, b = start+match.start(1), start+match.end(1)
            self.versions.append((match[1], len(self.text[:a].encode('utf-8')), len(self.text[:b].encode('utf-8'))))


def _unsupported(raw, context, versions=(), *, code='unsupported_version', malformed=False):
    report = _Report(raw, context, context['declared_format'], 'SAMStat')
    report.doc['artifact']['actual_format'] = 'unknown'
    report.doc['parse_scope'] = 'malformed' if malformed else 'unsupported'
    section = report.section('samstat_header', start=0, end=len(raw), state='malformed' if malformed else 'unsupported')
    report.raw(section, name='supplied SAMstat HTML', state=section['state'])
    for version, start, end in versions:
        report.label(section, 'producer_version', version, report.loc(section, 'native_version', start=start, end=end))
    if context['producer_version'] is not None:
        report.label(section, 'producer_version', context['producer_version'], report.loc(section, 'supplied_version'))
    report.issue(code, affected=[report.ref], required='native_version' if not versions else 'supported_parser')
    if len({v[0] for v in versions}) > 1 or versions and context['producer_version'] not in (None, versions[0][0]):
        report.issue('native_header_conflict', affected=[report.ref], required='native_version')
    return report.finish()


def parse_samstat_html(raw: bytes, *, context: dict) -> dict:
    """ParseContext -> NativeDocument; no acquisition or HTML/JS evaluation."""
    context = validate_contract('ParseContext', context)
    checked_bytes(raw, content=context['content'])
    if context['declared_format'] not in _FORMATS:
        raise FastqUtilsContractError('shape_invalid', '/declared_format')
    try:
        probe = _Probe(raw.decode('utf-8', errors='strict'))
    except (UnicodeError, ValueError, RecursionError):
        return _unsupported(raw, context, code='malformed_native', malformed=True)
    if probe.failure:
        from .bvbrc_fastqutils_samstat_svg import parse_samstat_bvbrc_error_html
        return parse_samstat_bvbrc_error_html(raw, context=context)
    versions = {row[0] for row in probe.versions}
    if len(versions) != 1:
        return _unsupported(raw, context, probe.versions)
    version = next(iter(versions))
    actual = {'2.2.3': 'samstat_html_2_2_3', '2.5.0': 'samstat_html_2_5_0'}.get(version)
    if actual is None or context['declared_format'] not in ('samstat_html', actual) or context['producer_version'] not in (None, version):
        return _unsupported(raw, context, probe.versions)
    if version == '2.5.0':
        from .bvbrc_fastqutils_samstat_svg import parse_samstat_html_2_5_0
        return parse_samstat_html_2_5_0(raw, context=context)
    # The legacy reader has a separate owner. Absence is a typed capability gap,
    # not permission to reinterpret its literal payload as the current format.
    try:
        from .bvbrc_fastqutils_samstat_legacy import parse_samstat_html_2_2_3
    except ModuleNotFoundError as error:
        if error.name != __package__ + '.bvbrc_fastqutils_samstat_legacy':
            raise
        return _unsupported(raw, context, probe.versions, code='unsupported_format')
    return parse_samstat_html_2_2_3(raw, context=context)


__all__ = ['parse_samstat_html']
