"""The page's content candidates, its information needs and Jev's measurement of them, ported from nano-graphrag.

nano-graphrag's page (``question_pipeline/episode_binding/page_binding.py``) splits its source into candidate input
units before it plans: the table regions ``source_table_language.discover_table_regions`` finds and the prose chunks
``utilities/extraction.chunk_spans`` cuts from the rest. It derives its information needs from the Goal contract
(``PageBinding._page_information_needs``: one need per result slot, one subject-identity need per result table), has
Jev measure every candidate once against every need (``assess_page_content``: windowed to Jev's budgets, one 'could
contribute' probability per window and need, a candidate's probability the maximum over its windows), and shows the
planner, for the candidates not yet consumed only, the top needs of each table region, the best single chunk per table
and the top chunks per need (``PageContentAssessment.planner_context``). Child options exist only for unconsumed
candidates, and the report child reads the remaining prose in document order (``report_binding.ReportWindowSource``).

What differs here, and why:

- Offsets are UTF-8 byte offsets of the commissioned representation (the leaves read byte windows); regions and chunks
  are found on the decoded text as in nano-graphrag and their character offsets converted.
- nano-graphrag chunks the table-blanked text, so a prose chunk may span a blanked table; a leaf here reads the
  original bytes of its window, so the prose is chunked segment by segment between table regions and no prose chunk
  holds a table's bytes.
- The information needs come from the A105 commission: per commissioned experiment one result need (its assay class
  and the methods of that class) and one subject-identity need (the molecules of the claim), the analogue of a result
  table's slots and its identity key columns.
- A report window is a byte range: consecutive remaining chunks that touch or overlap are merged into one window (up to
  nano-graphrag's ``REPORT_WINDOW_TEXT_CHARS``, counted in bytes); a gap (a consumed chunk or a table) starts a new one.

Every function is pure: nothing here reads or writes the Store. The page reads the bytes through custody and holds the
assessment it is handed (``page/task.py``)."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
import re

from gene_annotation_episode.episodic_workflow.episode_support.literature.grading.experimental_activity_evidence.literature_row_contract import (
    CLASS_OF_EXPERIMENT_TYPE)
from gene_annotation_episode.episodic_workflow.episode_support.model_exchange.jev_client import (
    JEV_EVALUATION_TOKEN_BUDGET, JEV_REQUEST_TOKEN_BUDGET, JEV_TOKEN_BOUND, JEV_TOKEN_HEADROOM, token_bound,
    window_text)

PAGE_CONTENT_ASSESSMENT_VERSION = 'jev_goal_need_vector_v1'      # nano-graphrag's version name
SOURCE_TABLE = 'source_table'
PROSE_CHUNK = 'prose_chunk'
CHUNK_SIZE = 2000              # nano-graphrag's pipeline chunk_size (characters)
CHUNK_OVERLAP = 200            # nano-graphrag's pipeline chunk_overlap (characters)
REPORT_WINDOW_BYTES = 1_000_000  # nano-graphrag's REPORT_WINDOW_TEXT_CHARS
TABLE_PREVIEW_CHARS = 512      # nano-graphrag's PAGE_CHILD_TABLE_PREVIEW_CHARS

# ---------------------------------------------------------------------------------------------------------------------
# Table regions (nano-graphrag ``source_table_language/source.py``: ``source_lines``, ``_line_blocks``,
# ``_markdown_separator``, ``_stable_width``, ``_make_region``, ``discover_table_regions``), character offsets.
# ---------------------------------------------------------------------------------------------------------------------
_HTML_TABLE_RE = re.compile(r'<table\b[^>]*>.*?</table\s*>', re.I | re.S)
_HTML_ROW_RE = re.compile(r'<tr\b[^>]*>.*?</tr\s*>', re.I | re.S)
_MARKDOWN_SEPARATOR_CELL_RE = re.compile(r'^:?-{3,}:?$')
_FIXED_COLUMN_RE = re.compile(r'\s{2,}')


def _stable_id(value):
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), default=str)
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]


def _source_lines(text):
    lines, offset = [], 0
    for raw in text.splitlines(keepends=True):
        content = raw.rstrip('\r\n')
        lines.append((content, offset, offset + len(content)))
        offset += len(raw)
    if offset < len(text):
        lines.append((text[offset:], offset, len(text)))
    return lines


def _line_blocks(lines, predicate):
    blocks, current = [], []
    for line in lines:
        if predicate(line[0]):
            current.append(line)
        elif current:
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks


def _markdown_separator(line):
    cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
    return len(cells) >= 2 and all(bool(_MARKDOWN_SEPARATOR_CELL_RE.fullmatch(cell)) for cell in cells)


def _stable_width(block, splitter):
    widths = []
    for line in block:
        try:
            widths.append(len(tuple(splitter(line[0]))))
        except (csv.Error, ValueError):
            return False
    useful = [width for width in widths if width >= 2]
    if len(useful) < 3:
        return False
    return Counter(useful).most_common(1)[0][1] / len(useful) >= 0.75


def _region(kind, text, lines):
    start, end = lines[0][1], lines[-1][2]
    return {'region_id': _stable_id({'kind': kind, 'start': start, 'end': end, 'text': text[start:end]}),
            'parser_hint': kind, 'start': start, 'end': end}


def discover_table_regions(text):
    """Non-overlapping regions of ``text`` with measurable table structure, in document order (character offsets)."""
    lines, candidates = _source_lines(text), []
    for match in _HTML_TABLE_RE.finditer(text):
        rows = tuple(_HTML_ROW_RE.finditer(match.group(0)))
        if len(rows) >= 2:
            candidates.append((0, _region('html', text, [(row.group(0), match.start() + row.start(),
                                                          match.start() + row.end()) for row in rows])))
    for block in _line_blocks(lines, lambda value: value.count('|') >= 2):
        if len(block) >= 2 and any(_markdown_separator(line[0]) for line in block):
            candidates.append((1, _region('markdown', text, block)))
    for block in _line_blocks(lines, lambda value: value.count('\t') >= 1):
        if len(block) >= 3 and _stable_width(block, lambda value: value.split('\t')):
            candidates.append((2, _region('tab', text, block)))
    for delimiter, kind, priority in ((',', 'csv', 3), (';', 'semicolon', 4)):
        for block in _line_blocks(lines, lambda value, token=delimiter: value.count(token) >= 2):
            if len(block) >= 4 and _stable_width(
                    block, lambda value, token=delimiter: next(csv.reader([value], delimiter=token))):
                candidates.append((priority, _region(kind, text, block)))
    for block in _line_blocks(lines, lambda value: len(_FIXED_COLUMN_RE.split(value.strip())) >= 3):
        if len(block) >= 4 and _stable_width(block, lambda value: _FIXED_COLUMN_RE.split(value.strip())):
            candidates.append((5, _region('fixed_width', text, block)))
    selected = []
    for _priority, region in sorted(candidates, key=lambda item: (item[1]['start'], item[0],
                                                                    -(item[1]['end'] - item[1]['start']))):
        if any(region['start'] < kept['end'] and kept['start'] < region['end'] for kept in selected):
            continue
        selected.append(region)
    return sorted(selected, key=lambda item: item['start'])


def chunk_spans(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """nano-graphrag's ``chunk_spans``: (start, end) character spans of ``text`` with exact offsets."""
    if chunk_size <= 0:
        raise ValueError('chunk_size must be positive')
    if overlap >= chunk_size:
        raise ValueError('overlap must be smaller than chunk_size')
    spans, start = [], 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        spans.append((start, end))
        if end >= len(text) or len(text) - end <= overlap:
            break
        start = end - overlap
    return spans


def page_candidates(content):
    """The candidate input units of a page whose bytes are ``content`` (UTF-8), in document order: every table region
    (``source_table:<region id>``) and every non-blank prose chunk of the text between them (``prose_chunk:<index>``),
    each ``{'candidate_id', 'candidate_type', 'index', 'start', 'end'}`` with UTF-8 byte offsets (a table also has its
    ``parser_hint``). Candidates do not overlap a table; neighbouring prose chunks overlap by ``CHUNK_OVERLAP``
    characters, as in nano-graphrag."""
    text = content.decode('utf-8')
    byte_at = [0]
    for character in text:
        byte_at.append(byte_at[-1] + len(character.encode('utf-8')))
    regions = discover_table_regions(text)
    tables = [{'candidate_id': SOURCE_TABLE + ':' + region['region_id'], 'candidate_type': SOURCE_TABLE,
               'index': index, 'start': byte_at[region['start']], 'end': byte_at[region['end']],
               'parser_hint': region['parser_hint']} for index, region in enumerate(regions)]
    segments, cursor = [], 0
    for region in regions:
        segments.append((cursor, region['start']))
        cursor = region['end']
    segments.append((cursor, len(text)))
    chunks = []
    for segment_start, segment_end in segments:
        for start, end in chunk_spans(text[segment_start:segment_end]):
            if text[segment_start + start:segment_start + end].strip():
                chunks.append({'candidate_id': PROSE_CHUNK + ':' + format(len(chunks), '04d'),
                               'candidate_type': PROSE_CHUNK, 'index': len(chunks),
                               'start': byte_at[segment_start + start], 'end': byte_at[segment_start + end]})
    return sorted(tables + chunks, key=lambda item: (item['start'], item['candidate_type']))


def candidate_text(content, candidate):
    return content[candidate['start']:candidate['end']].decode('utf-8')


def report_windows(candidates, remaining_ids):
    """The windows a report reads, in document order: the remaining prose chunks, consecutive ones that touch or overlap
    merged into one byte window up to ``REPORT_WINDOW_BYTES``; ``[[start, end], ...]``. Each remaining chunk lies in
    exactly one window."""
    windows = []
    for candidate in candidates:
        if candidate['candidate_type'] != PROSE_CHUNK or candidate['candidate_id'] not in remaining_ids:
            continue
        if windows and candidate['start'] <= windows[-1][1] and candidate['end'] - windows[-1][0] <= REPORT_WINDOW_BYTES:
            windows[-1][1] = max(windows[-1][1], candidate['end'])
        else:
            windows.append([candidate['start'], candidate['end']])
    return windows


# ---------------------------------------------------------------------------------------------------------------------
# Information needs from the commission (nano-graphrag ``PageBinding._page_information_needs``).
# ---------------------------------------------------------------------------------------------------------------------
def information_needs(experiments, claim):
    """The needs Jev measures: for each commissioned experiment (``{'experiment_ref', 'assay_type', 'label'}``) one
    ``result`` need and one ``subject_identity`` need (its 'table' is the experiment); ``claim`` is ``{'predicate',
    'subject_id', 'partner_id'}``. Without commissioned experiments the claim itself is the one table."""
    claim_text = f"{claim['subject_id']} {claim['predicate']} {claim['partner_id']}"
    molecules = [claim['subject_id']] + ([claim['partner_id']] if claim['partner_id'] is not None else [])
    tables = [(item['experiment_ref'], item['label'], item['assay_type']) for item in experiments] or [
        ('claim', claim_text, None)]
    results, identities = [], []
    for table, label, assay_type in tables:
        methods = sorted(kind for kind, kind_class in CLASS_OF_EXPERIMENT_TYPE.items() if kind_class == assay_type)
        results.append({
            'need_id': 'result:' + table, 'table': table, 'kind': 'result', 'label': label, 'columns': methods,
            'description': (f"A reported result of the commissioned experiment '{label}'"
                            + (f" (assay class {assay_type}; methods of this class: {', '.join(methods)})"
                               if assay_type else '')
                            + f" bearing on the claim '{claim_text}': a measured value with its unit, an estimate "
                              'basis (fit, replicates, spread), the conditions, or the method that produced it.')})
        identities.append({
            'need_id': 'identity:' + table, 'table': table, 'kind': 'subject_identity',
            'label': 'identity context for ' + label, 'columns': ['subject_id', 'partner_id'],
            'description': ('Information needed to identify or link the molecules of a result of '
                            f"'{label}' to the claim '{claim_text}' using: {', '.join(molecules)} "
                            '(names, constructs, variants, tags, organisms).')})
    return results + identities


# ---------------------------------------------------------------------------------------------------------------------
# Jev's measurement (nano-graphrag ``_page_content_questions``, ``_page_content_state``,
# ``_page_content_request_fits``, ``assess_page_content``).
# ---------------------------------------------------------------------------------------------------------------------
def _questions(windows, needs):
    questions, lookup = {}, {}
    for window_index, window in enumerate(windows):
        for need_index, need in enumerate(needs):
            name = f'w{window_index:04d}_n{need_index:04d}'
            questions[name] = {
                'instructions': (f"Could candidate window {window['window_id']!r} contribute source evidence for "
                                 f"information need {need['need_id']!r} when interpreted with the supplied page "
                                 'context? The window need not contain a complete output row or repeat subject '
                                 'identity that appears elsewhere on this page.'),
                'criteria': {
                    'true': ('The window contains a reported value, estimate basis, subject identity, relationship, '
                             'label, or context that could help satisfy this specific information need.'),
                    'false': ('The window cannot contribute to this information need, even when interpreted with the '
                              'supplied page context.')}}
            lookup[name] = (window['candidate_id'], need['need_id'])
    return questions, lookup


def _state(goal, page_context, needs, windows):
    return {'page_goal': dict(goal), 'page_context': dict(page_context), 'information_needs': list(needs),
            'candidate_windows': [dict(window) for window in windows]}


def _fits(jev, state, questions):
    return (jev.nouls_request_token_count(state=state, questions=questions)
            <= JEV_REQUEST_TOKEN_BUDGET - JEV_TOKEN_HEADROOM
            and jev.nouls_request_token_count(state=state, questions=questions, largest_evaluation=True)
            <= JEV_EVALUATION_TOKEN_BUDGET - JEV_TOKEN_HEADROOM)


def _window(candidate, text, window_id):
    return {'window_id': window_id, 'candidate_id': candidate['candidate_id'],
            'candidate_type': candidate['candidate_type'], 'index': candidate['index'],
            'start_offset': candidate['start'], 'end_offset': candidate['end'], 'text': text}


async def assess_page_content(jev, *, goal, page_context, needs, candidates, content):
    """Measure every candidate once against every need, before the page plans; the assessment record. ``content`` is
    the page's bytes (the candidates' text is read from it)."""
    if not needs:
        raise ValueError('Page content assessment requires information needs')
    if not candidates:
        raise ValueError('Page content assessment requires content candidates')
    windows = []
    for candidate in candidates:
        pending, fitted = [candidate_text(content, candidate)], []
        while pending:
            text = pending.pop(0)
            probe = _window(candidate, text, candidate['candidate_id'] + '#window-probe')
            questions, _ = _questions((probe,), needs)
            if _fits(jev, _state(goal, page_context, needs, (probe,)), questions):
                fitted.append(text)
                continue
            tokens = token_bound(text)
            if tokens <= 1:
                raise ValueError('Jev Page assessment metadata exceeds its request budget')
            pieces = window_text(text, budget=max(1, tokens // 2))
            if len(pieces) < 2:
                raise ValueError('unable to fit Page candidate into Jev request')
            pending[0:0] = pieces
        windows.extend(_window(candidate, text, f"{candidate['candidate_id']}#window-{number:04d}")
                       for number, text in enumerate(fitted, start=1))
    batches, current = [], []
    for window in windows:
        trial = [*current, window]
        questions, _ = _questions(trial, needs)
        if _fits(jev, _state(goal, page_context, needs, trial), questions):
            current = trial
            continue
        if not current:
            raise ValueError('one fitted Page candidate still exceeds Jev request budget')
        batches.append(current)
        current = [window]
    if current:
        batches.append(current)
    values = {candidate['candidate_id']: {need['need_id']: [] for need in needs} for candidate in candidates}
    requests = []
    for request_index, batch in enumerate(batches, start=1):
        questions, lookup = _questions(batch, needs)
        decision = await jev.nouls(state=_state(goal, page_context, needs, batch), questions=questions)
        for name, probability in decision.probabilities.items():
            candidate_id, need_id = lookup[name]
            values[candidate_id][need_id].append(float(probability))
        requests.append({'request_index': request_index,
                         'candidate_window_ids': [window['window_id'] for window in batch],
                         'model': decision.response.model, 'input_tokens': decision.response.input_tokens,
                         'output_tokens': decision.response.output_tokens, 'attempts': decision.response.attempts})
    return {'version': PAGE_CONTENT_ASSESSMENT_VERSION, 'token_bound': JEV_TOKEN_BOUND,
            'information_needs': list(needs),
            'candidates': [{'candidate_id': candidate['candidate_id'], 'candidate_type': candidate['candidate_type'],
                            'index': candidate['index'], 'start_offset': candidate['start'],
                            'end_offset': candidate['end'],
                            'probabilities': {need_id: max(found) for need_id, found in
                                              values[candidate['candidate_id']].items()},
                            'window_probabilities': values[candidate['candidate_id']],
                            'text_tokens': token_bound(candidate_text(content, candidate))}
                           for candidate in candidates],
            'requests': requests}


def planner_context(assessment, candidate_ids):
    """nano-graphrag's ``PageContentAssessment.planner_context`` over the held assessment record, for the candidates in
    ``candidate_ids`` (the unconsumed ones) only."""
    allowed = set(candidate_ids)
    candidates = [item for item in assessment['candidates'] if item['candidate_id'] in allowed]
    prose = [item for item in candidates if item['candidate_type'] == PROSE_CHUNK]
    needs = assessment['information_needs']
    by_table = {}
    for need in needs:
        by_table.setdefault(need['table'], []).append(need)
    coverage = []
    for table, table_needs in by_table.items():
        if not prose or not table_needs:
            continue
        best = max(prose, key=lambda item: min(item['probabilities'].get(need['need_id'], 0.0) for need in table_needs))
        coverage.append({'table': table, 'candidate_id': best['candidate_id'],
                         'joint_min_probability': min(best['probabilities'].get(need['need_id'], 0.0)
                                                      for need in table_needs),
                         'probabilities': {need['need_id']: best['probabilities'].get(need['need_id'], 0.0)
                                           for need in table_needs}})
    top = []
    for need in needs:
        ranked = sorted(prose, key=lambda item: item['probabilities'].get(need['need_id'], 0.0), reverse=True)[:3]
        top.append({'need_id': need['need_id'], 'chunks': [
            {'candidate_id': item['candidate_id'], 'index': item['index'], 'start_offset': item['start_offset'],
             'probability': item['probabilities'].get(need['need_id'], 0.0)} for item in ranked]})
    tables = []
    for item in candidates:
        if item['candidate_type'] != SOURCE_TABLE:
            continue
        ranked = sorted(item['probabilities'].items(), key=lambda pair: (-float(pair[1]), str(pair[0])))[:3]
        tables.append({'candidate_id': item['candidate_id'], 'index': item['index'],
                       'start_offset': item['start_offset'], 'end_offset': item['end_offset'],
                       'top_information_needs': [{'need_id': need_id, 'probability': float(probability)}
                                                 for need_id, probability in ranked]})
    return {'version': assessment['version'], 'information_needs': needs, 'source_table_assessments': tables,
            'best_single_chunk_coverage_by_table': coverage, 'top_chunks_by_need': top}


__all__ = ['CHUNK_OVERLAP', 'CHUNK_SIZE', 'PROSE_CHUNK', 'REPORT_WINDOW_BYTES', 'SOURCE_TABLE', 'TABLE_PREVIEW_CHARS',
           'assess_page_content', 'candidate_text', 'chunk_spans', 'discover_table_regions', 'information_needs',
           'page_candidates', 'planner_context', 'report_windows']
