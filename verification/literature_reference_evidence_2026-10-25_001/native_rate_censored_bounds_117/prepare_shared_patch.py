from pathlib import Path
import difflib
import hashlib
import json
root = Path.cwd()
artifact = root / 'verification/literature_reference_evidence_2026-10-25_001/native_rate_censored_bounds_117'
changes = {}
def change(name):
    return (root / 'gene_annotation_episode' / name).read_text()
def once(text, old, new):
    assert text.count(old) == 1, (old[:80], text.count(old))
    return text.replace(old, new, 1)
name = 'literature_episodes.py'
a = change(name)
b = a.replace('"literature_rate_source_render.py",', '"literature_rate_source_render.py", "literature_rate_domains.py",')
b = b.replace('result.update(self._native_rate_display_context(context))', 'result.update(self._native_rate_display_context(context))\n            result.update(self._native_rate_domain_display_context(context))')
start = b.index('    def _native_rate_display_context(self, context):')
end = b.index('    def _rate_fact_sources(self):', start)
method = b[start:end].replace('_native_rate_display_context', '_native_rate_domain_display_context').replace('.source_projection()', '.source_domain_projection()').replace('literature_rate_source_display', 'literature_rate_source_domain_display')
b = b[:end] + method + b[end:]
b = once(b, '    def _rate_fact_sources(self):\n', '    def _rate_fact_sources(self):\n        from .literature_rate_domains import rate_source_domain_cells_schema\n')
needle = '            "literature_quantity_cells": {"type": "array", "meaning":'
entry = '''            "literature_rate_source_domain_cells": {"type": "array", "meaning":
                "The same saved native rate components with conditional logical enclosures of reported operands. Finite bounds, inclusivity, undefined denominators and outward numerical projection are explicit; range failure can qualify a still-useful partial enclosure. Status concerns the point estimate. Domains are not sampling confidence intervals, independence, endpoint co-attainability, target transfer or annotation credit. This is another closed return view of the same numerical sheet, not another assay.",
                "report_schema": rate_source_domain_cells_schema()},
'''
b = once(b, needle, entry + needle)
needle = '''                ("literature_rate_source_cells", "requested_rate_components", PROVIDER,
                 COMPONENTS, self.services.literature_rate_repository().source_projection),'''
b = once(b, needle, needle + '''
                ("literature_rate_source_domain_cells", "requested_rate_components", PROVIDER,
                 COMPONENTS, self.services.literature_rate_repository().source_domain_projection),''')
b = b.replace('{"literature_rate_cells", "literature_rate_source_cells"}', '{"literature_rate_cells", "literature_rate_source_cells", "literature_rate_source_domain_cells"}')
old = 'Request its closed literature_rate_source_cells return projection, which preserves each arm\'s subject, construct, preparation and approximation;'
new = 'Request literature_rate_source_domain_cells for full reported-operand domains, including finite two-sided enclosures; the original literature_rate_source_cells projection preserves each arm\'s subject, construct, preparation, approximation and one-sided limits;'
b = once(b, old, new)
changes[name] = (a,b)
name = 'literature_experimental_prompt.py'
a = change(name); b = once(a, 'from . import literature_rate_source_render as _native_rate', 'from . import literature_rate_source_render as _native_rate\nfrom . import literature_rate_domains as _rate_domains')
b = once(b, '    "literature_rate_source_display",', '    "literature_rate_source_display", "literature_rate_source_domain_display",')
needle = '    hidden_native_rate = _native_rate.hidden_records(native_rows)'
replacement = '''    domain_rows = list(_rate_domains.rows_from_reports(state.get("child_reports", ())))
    domain_rows.extend(_rate_domains.own_rows(own, state.get("literature_rate_source_domain_display", {}).get("cells", ())))
    native_rows.extend(_rate_domains.base_rows(domain_rows))
''' + needle
b = once(b, needle, replacement)
b = once(b, '        native_rate_display=None, values=_values):', '        native_rate_display=None, native_rate_domain_display=None, values=_values):')
needle = '    native_rate_display = native_rate_display or {}'
replacement = '''    native_rate_domain_display = native_rate_domain_display or {}
    domain_rows = _rate_domains.own_rows(content, native_rate_domain_display.get("cells", ()))
    if domain_rows:
        _section(parts, title, values(_pick(value, ("status", "selected_tool", "feedback"))))
        _rate_domains.render_received(parts, domain_rows, native_rate_domain_display.get("records", {}),
            section=_section, table=_table)
        return
''' + needle
b = once(b, needle, replacement)
b = once(b, 'native_rate_records=None, values=_values):', 'native_rate_records=None, native_rate_domain_records=None, values=_values):')
b = once(b, '    native_rate = {}', '    native_rate = {}\n    rate_domains = {}')
needle = '            if isinstance(value, (list, tuple)) and value and all(_native_rate.is_row(row) for row in value):'
replacement = '''            if isinstance(value, (list, tuple)) and value and all(_rate_domains.is_row(row) for row in value):
                for row in value:
                    rate_domains.setdefault(row["sheet_ref"], []).append(row)
            elif isinstance(value, (list, tuple)) and value and all(_native_rate.is_row(row) for row in value):'''
b = once(b, needle, replacement)
needle = '''    if len(native_rate) > 1:
        _section(parts, "Returned comparison labels",
            "Comparison numbers identify returned records, not independent experiments.")
    for comparison_number, rows in enumerate(native_rate.values(), 1):
        _native_rate.render_received(parts, rows, native_rate_records or records or {},
            section=_section, table=_table, comparison_number=comparison_number)'''
replacement = '''    native_sheets = list(dict.fromkeys((*native_rate, *rate_domains)))
    if len(native_sheets) > 1:
        _section(parts, "Returned comparison labels",
            "Comparison numbers identify returned records, not independent experiments.")
    for comparison_number, sheet_ref in enumerate(native_sheets, 1):
        domain_rows = rate_domains.get(sheet_ref, [])
        combined = {}
        for row in [*native_rate.get(sheet_ref, []), *_rate_domains.base_rows(domain_rows)]:
            key = (row["sheet_ref"], row["component"])
            if key in combined and combined[key] != row:
                from .domain import ContractError
                raise ContractError("literature_rate_cross_view_display_mismatch")
            combined[key] = row
        meanings = {**(records or {}), **(native_rate_records or {}), **(native_rate_domain_records or {})}
        _native_rate.render_received(parts, list(combined.values()), meanings,
            section=_section, table=_table, comparison_number=comparison_number)
        if domain_rows:
            _rate_domains.render_domains(parts, domain_rows, section=_section, table=_table)'''
b = once(b, needle, replacement)
needle = '    native_rate_display = {**native_rate_display, "records": native_rate_records}'
replacement = needle + '''
    native_rate_domain_display = state.get("literature_rate_source_domain_display", {})
    native_rate_domain_records = {**controlled_records, **native_rate_domain_display.get("records", {})}
    native_rate_domain_display = {**native_rate_domain_display, "records": native_rate_domain_records}'''
b = once(b, needle, replacement)
needle = "        received_native_rate_sheets = {row['sheet_ref'] for row in _native_rate.rows_from_reports(state.get('child_reports', ()))}"
b = once(b, needle, needle + "\n        received_native_rate_sheets.update(row['sheet_ref'] for row in _rate_domains.rows_from_reports(state.get('child_reports', ())))")
b = b.replace('native_rate_display=native_rate_display, values=semantic_values)', 'native_rate_display=native_rate_display, native_rate_domain_display=native_rate_domain_display, values=semantic_values)')
b = once(b, 'native_rate_records=native_rate_records, values=semantic_values)', 'native_rate_records=native_rate_records, native_rate_domain_records=native_rate_domain_records, values=semantic_values)')
changes[name] = (a,b)
name = 'literature_reference_parent_prompt.py';a = change(name)
b = once(a, '        "literature_received_fact_display")', '        "literature_received_fact_display", "literature_rate_source_domain_display")')
changes[name] = (a,b)
manifest = {}
patch = []
for name,(a,b) in changes.items():
    assert a != b
    compile(b, name, 'exec')
    manifest[name] = {'before_sha256':hashlib.sha256(a.encode()).hexdigest(), 'proposed_sha256':hashlib.sha256(b.encode()).hexdigest()}
    patch.extend(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/gene_annotation_episode/'+name,tofile='b/gene_annotation_episode/'+name))
(artifact/'shared_integration_proposal.diff').write_text(''.join(patch))
(artifact/'shared_integration_proposal_hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(manifest,indent=2))
print('Shared production files have not been modified.')
