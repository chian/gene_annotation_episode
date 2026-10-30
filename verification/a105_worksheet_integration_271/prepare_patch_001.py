"""Prepare reviewable worksheet hooks without changing the locked checkout."""
import ast
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def replace_once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('one exact integration anchor required: ' + before[:70])
    return text.replace(before, after, 1)


def episode_candidate(text):
    text = replace_once(text,
        '            for name in ("literature_experimental_contracts.py", "literature_rate_reader.py",',
        '            for name in ("literature_a105_worksheet.py", "literature_a105_worksheet_render.py",\n'
        '                         "literature_experimental_contracts.py", "literature_rate_reader.py",')
    hook = '''
        # Interpretation-only report_update values lack the bound numerical
        # fields. Check their relationships at the complete ordinary admission
        # boundary, including valid empty numerical partials.
        from .literature_a105_worksheet import FAMILIES as WORKSHEET_FAMILIES, validate_a105_worksheet_links
        if requested_sources.intersection(WORKSHEET_FAMILIES):
            known = set(context.received_record_refs)
            def read_public_record(reference):
                if reference not in known:
                    try:
                        selection = self.services.record_selection(context)
                    except (AttributeError, LookupError):
                        return None
                    if (selection.get('run_id') != context.run_id
                            or selection.get('episode_id') != context.episode_id):
                        raise ReportBoundaryError('Worksheet reference receiver differs',
                            code='a105_worksheet_receiver_mismatch')
                    known.update(selection.get('known_record_refs', ()))
                return self.services.read_record(reference) if reference in known else None
            try:
                validate_a105_worksheet_links(form, schema, context.assignment,
                    read_public_record=read_public_record)
            except ContractError as error:
                raise ReportBoundaryError(str(error), code=str(error)) from error

'''
    return replace_once(text, '\n    def resolve(self, context, reference, namespace):',
        '\n' + hook + '    def resolve(self, context, reference, namespace):')


def prompt_candidate(text):
    text = replace_once(text, 'from collections.abc import Mapping\n',
        'from collections.abc import Mapping\n\n'
        'from .literature_a105_worksheet import VERSION as _WORKSHEET_VERSION\n'
        'from .literature_a105_worksheet_render import render_a105_worksheet\n')
    helper = '''def _worksheet_context(report):
    if not isinstance(report, Mapping):
        return None
    contexts = [(name, value) for name, value in report.items()
        if isinstance(value, Mapping) and value.get('version') == _WORKSHEET_VERSION]
    return contexts[0] if len(contexts) == 1 else None


'''
    text = replace_once(text, 'def _received_returns(parts, reports,', helper + 'def _received_returns(parts, reports,')
    text = replace_once(text,
        '            ordinary.append(report)\n            continue\n        for name, value in report.items():',
        '            ordinary.append(report)\n            continue\n'
        '        if _worksheet_context(report) is not None:\n'
        '            render_a105_worksheet(parts, report, section=_section, table=_table,\n'
        '                public_records=records or {})\n'
        '            continue\n'
        '        for name, value in report.items():')
    text = replace_once(text,
        '    if (isinstance(content, Mapping) and any(isinstance(v, (tuple, list)) and v and all(_measurement_comparison.is_row(r) for r in v) for v in content.values()) or',
        '    if (_worksheet_context(content) is not None or isinstance(content, Mapping) and any(isinstance(v, (tuple, list)) and v and all(_measurement_comparison.is_row(r) for r in v) for v in content.values()) or')
    text = replace_once(text,
        "            and (any(_measurement_comparison.history_record(row) for row in content['records']) or",
        "            and (any(_worksheet_context(row.get('admitted_report')) is not None for row in content['records'] if isinstance(row, Mapping)) or any(_measurement_comparison.history_record(row) for row in content['records']) or")
    text = replace_once(text,
        '    if state.get("current_report_update"):\n        if (list(_measurement_comparison.rows_from_values(state["current_report_update"])) or',
        '    current_worksheet = _worksheet_context(state.get("current_report_update"))\n'
        '    duplicate_context = (current_worksheet is not None and len(state["current_report_update"]) == 1\n'
        '        and any(_worksheet_context(report) is not None\n'
        '            and _worksheet_context(report)[1] == current_worksheet[1]\n'
        '            for report in state.get("child_reports", ())))\n'
        '    if state.get("current_report_update") and not duplicate_context:\n'
        '        if (current_worksheet is not None or list(_measurement_comparison.rows_from_values(state["current_report_update"])) or')
    return text


def main():
    rows, diff = [], []
    candidates = HERE / 'candidate_001'
    candidates.mkdir(exist_ok=True)
    for filename, make in [('literature_episodes.py', episode_candidate),
            ('literature_experimental_prompt.py', prompt_candidate)]:
        source = ROOT / 'gene_annotation_episode' / filename
        original = source.read_text()
        changed = make(original)
        ast.parse(changed)
        (candidates / filename).write_text(changed)
        rows.append({'path': str(source.relative_to(ROOT)),
            'original_sha256': hashlib.sha256(original.encode()).hexdigest(),
            'candidate_sha256': hashlib.sha256(changed.encode()).hexdigest()})
        diff.extend(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
            fromfile='a/gene_annotation_episode/' + filename,
            tofile='b/gene_annotation_episode/' + filename))
    (HERE / 'INTEGRATION_PATCH_001.diff').write_text(''.join(diff))
    (HERE / 'CANDIDATE_PIN_001.json').write_text(json.dumps({'files': rows,
        'production_changed': False, 'applied': False, 'static_parse': 'passed',
        'note': 'Prepared under the268 lock; regenerate from its final frozen shared files before applying.'}, indent=2)+'\n')
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
