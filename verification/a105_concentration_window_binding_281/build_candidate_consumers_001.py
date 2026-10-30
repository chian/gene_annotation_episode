"""Prepare a review-only overlay. Does not modify production paths."""
from pathlib import Path

ROOT=Path(__file__).parent
C=ROOT/'candidate'

def edit(name,pairs):
    text=(ROOT/'before'/name).read_text()
    for old,new,count in pairs:
        assert text.count(old)==count,(name,old[:80],text.count(old),count)
        text=text.replace(old,new)
    (C/name).write_text(text)

edit('literature_episodes.py',[
    ("    from .literature_measurement_comparison_storage import measurement_comparison_operation_schema",
     "    from .literature_concentration_window_storage import concentration_window_operation_schema\n    result.append({'name': 'literature.concentration_window.populate',\n        'description': 'Populate exactly requested source concentration-window components from original values, units, coordinates and witnessed experimental meanings. Preserve actual molecule, construct, preparation, participants, endpoint, normalization, physical versus descriptive accounts, stoichiometric model, timing qualifications and covariance ownership. Interval averages are not initial rates or turnover constants. Missing inputs preserve partials; no unrequested operands or covariance matrix, molecular attribution, target transfer or annotation credit.',\n        'input_schema': concentration_window_operation_schema()})\n    from .literature_measurement_comparison_storage import measurement_comparison_operation_schema",1),
    ('                         "literature_measurement_comparison_inputs.py",',
     '                         "literature_concentration_window_inputs.py", "literature_concentration_window_calculations.py",\n                         "literature_concentration_window_prompt.py", "literature_concentration_window_storage.py",\n                         "literature_concentration_window_render.py",\n                         "literature_measurement_comparison_inputs.py",',1),
    ('            from .literature_measurement_comparison_storage import REQUESTED as COMPARISON_REQUESTED, COMPONENTS as COMPARISON_COMPONENTS',
     "            from .literature_concentration_window_storage import REQUESTED as WINDOW_REQUESTED, COMPONENTS as WINDOW_COMPONENTS\n            schema['properties'][WINDOW_REQUESTED] = {'type': 'array', 'uniqueItems': True,\n                'items': {'enum': list(WINDOW_COMPONENTS)}}\n            from .literature_measurement_comparison_storage import REQUESTED as COMPARISON_REQUESTED, COMPONENTS as COMPARISON_COMPONENTS",1),
    ('            result.update(self._measurement_comparison_display_context(context))',
     '            result.update(self._measurement_comparison_display_context(context))\n            result.update(self._concentration_window_display_context(context))',2),
    ('{"literature.measurement_comparison.populate",',
     '{"literature.concentration_window.populate", "literature.measurement_comparison.populate",',2),
    ('                self._measurement_comparison_repository().authorize_source_access(context, arguments[\'source_ref\'], arguments.get(\'representation\', \'text\'), tool_name)',
     '                self._measurement_comparison_repository().authorize_source_access(context, arguments[\'source_ref\'], arguments.get(\'representation\', \'text\'), tool_name)\n                self._concentration_window_repository().authorize_source_access(context, arguments[\'source_ref\'], arguments.get(\'representation\', \'text\'), tool_name)',1),
    ('                    self._measurement_comparison_repository().authorize_record_access(context, self.services.read_record(ref))',
     '                    self._measurement_comparison_repository().authorize_record_access(context, self.services.read_record(ref))\n                    self._concentration_window_repository().authorize_record_access(context, self.services.read_record(ref))',1),
    ('                    self._measurement_comparison_repository().authorize_record_access(context, record)',
     '                    self._measurement_comparison_repository().authorize_record_access(context, record)\n                    self._concentration_window_repository().authorize_record_access(context, record)',1),
    ('                repo = {"literature.measurement_comparison.populate": self._measurement_comparison_repository,',
     '                repo = {"literature.concentration_window.populate": self._concentration_window_repository,\n                        "literature.measurement_comparison.populate": self._measurement_comparison_repository,',1),
    ('    def _measurement_comparison_repository(self):',
     "    def _concentration_window_repository(self):\n        from .literature_concentration_window_storage import LiteratureConcentrationWindowRepository\n        if not hasattr(self, '_concentration_window_repo'):\n            self._concentration_window_repo = LiteratureConcentrationWindowRepository(self.services.workflow.store, self.services.workflow.run_id)\n        return self._concentration_window_repo\n\n    def _concentration_window_display_context(self, context):\n        return {'literature_concentration_window_receipt_bindings': self._concentration_window_repository().receipt_bindings()}\n\n    def _measurement_comparison_repository(self):",1),
    ('        from .literature_measurement_comparison_storage import MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2, NAMESPACE as COMPARISON_NAMESPACE',
     "        from .literature_concentration_window_storage import CONCENTRATION_WINDOW_CELLS_SCHEMA_V1, NAMESPACE as WINDOW_NAMESPACE\n        from .literature_numerical_contracts import RETURN_MEANINGS\n        result[WINDOW_NAMESPACE] = {'type': 'array', 'meaning': RETURN_MEANINGS[WINDOW_NAMESPACE],\n            'report_schema': deepcopy(CONCENTRATION_WINDOW_CELLS_SCHEMA_V1)}\n        from .literature_measurement_comparison_storage import MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2, NAMESPACE as COMPARISON_NAMESPACE",1),
    ('        result = ((COMPARISON_NAMESPACE, COMPARISON_REQUESTED, COMPARISON_PROVIDER, (), self._measurement_comparison_repository),',
     '        from .literature_concentration_window_storage import PROVIDER as WINDOW_PROVIDER, NAMESPACE as WINDOW_NAMESPACE, REQUESTED as WINDOW_REQUESTED\n        result = ((WINDOW_NAMESPACE, WINDOW_REQUESTED, WINDOW_PROVIDER, (), self._concentration_window_repository),\n                (COMPARISON_NAMESPACE, COMPARISON_REQUESTED, COMPARISON_PROVIDER, (), self._measurement_comparison_repository),',1),
    ('        comparison_cells = [row for name, node in schema.get(\'properties\', {}).items()',
     "        window_cells = [row for name, node in schema.get('properties', {}).items()\n            if node.get('x-source') == 'literature_concentration_window_cells' for row in form[name]]\n        references.extend(self._concentration_window_repository().cell_record_refs(window_cells))\n        comparison_cells = [row for name, node in schema.get('properties', {}).items()",1),
    ('{"literature_measurement_comparison_cells", "literature_kinetic_summary_precision_cells",',
     '{"literature_concentration_window_cells", "literature_measurement_comparison_cells", "literature_kinetic_summary_precision_cells",',3),
    ('raise ContractError("literature_measurement_comparison_requested_subset_mismatch" if',
     'raise ContractError("literature_concentration_window_requested_subset_mismatch" if namespace == "literature_concentration_window_cells" else "literature_measurement_comparison_requested_subset_mismatch" if',1),
])

edit('literature_task_selection.py',[
    ('from .literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK',
     'from .literature_measurement_comparison_prompt import MEASUREMENT_COMPARISON_TASK\nfrom .literature_concentration_window_prompt import CONCENTRATION_WINDOW_TASK',1),
    ('_FAMILIES = (',
     '_FAMILIES = (\n    _Family("literature_concentration_window_cells", CONCENTRATION_WINDOW_TASK, "literature_concentration_window_storage", "LiteratureConcentrationWindowRepository", "requested_concentration_window_components", "literature.concentration_window.populate"),',1),
    ('_SCOPE_SOURCE = {','_SCOPE_SOURCE = {\n    \'source_concentration_window\': \'literature_concentration_window_cells\',',1),
    ('_ROW_VERSION_SOURCE = {','_ROW_VERSION_SOURCE = {\n    \'concentration_window_return_v1\': \'literature_concentration_window_cells\',',1),
    ("required_versions = {'source_measurement_comparison':", "required_versions = {'source_concentration_window': 'concentration_window_return_v1', 'source_measurement_comparison':",1),
    ("expected = {'literature_measurement_comparison_cells':", "expected = {'literature_concentration_window_cells': 'source_concentration_window', 'literature_measurement_comparison_cells':",1),
])

meaning='Exactly requested source concentration-window components with actual molecule, construct, preparation, participants, analyte, units, basis and normalization. Preserve native versus calculated origins, per-pair and cross-readout comparability and physical account, interpreted stoichiometric coefficients, qualified timing, conditional sensitivity and covariance selection/status/ownership/dependence. Concentration changes and product-fate fractions do not establish unique molecular attribution, independent replication, target transfer or annotation credit. Unrequested native operands and covariance matrices remain private; missing scientific inputs and unfinished approximate, bounded or raw-table covariance calculations stay distinct.'
edit('literature_numerical_contracts.py',[
    ('_SCHEMAS = {',"_SCHEMAS = {\n    'literature_concentration_window_cells': ('literature_concentration_window_storage', 'concentration_window_cells_schema'),",1),
    ('RETURN_MEANINGS = {',"RETURN_MEANINGS = {\n    'literature_concentration_window_cells': "+repr(meaning)+',',1),
])
edit('literature_numerical_return_presentation.py',[
    ("return {'literature.measurement_comparison.populate':", "return {'literature.concentration_window.populate': 'literature_concentration_window_cells',\n            'literature.measurement_comparison.populate':",1),
])
edit('episode_contract_information.py',[
    ("'literature_kinetic_summary_precision_cells', 'literature_measurement_comparison_cells'}}",
     "'literature_kinetic_summary_precision_cells', 'literature_measurement_comparison_cells', 'literature_concentration_window_cells'}}",1),
])
edit('literature_a105_worksheet.py',[
    ('FAMILIES = {',"FAMILIES = {\n    'literature_concentration_window_cells': ('requested_concentration_window_components',\n        'literature_concentration_window_storage', 'concentration_window_cells_schema',\n        'observed_concentration_window_and_product_fate'),",1),
    ('_SCOPES = {',"_SCOPES = {\n    'literature_concentration_window_cells': 'source_concentration_window',",1),
    ('Eight supported formats do not represent eight completed assays.','Nine supported formats do not represent nine completed assays.',1),
])
edit('literature_a105_worksheet_render.py',[
    ('from . import literature_measurement_comparison_render as comparison',
     'from . import literature_measurement_comparison_render as comparison\nfrom . import literature_concentration_window_render as concentration',1),
    ("        elif scope == 'source_measurement_comparison':", "        elif scope == 'source_concentration_window':\n            concentration.render_received(parts, rows, section=section, table=table)\n        elif scope == 'source_measurement_comparison':",1),
])

edit('literature_experimental_prompt.py',[
    ('from . import literature_measurement_comparison_render as _measurement_comparison',
     'from . import literature_measurement_comparison_render as _measurement_comparison\nfrom . import literature_concentration_window_render as _concentration_window',1),
    ('"literature_summary_precision_receipt_bindings", "literature_measurement_comparison_receipt_bindings",',
     '"literature_summary_precision_receipt_bindings", "literature_measurement_comparison_receipt_bindings", "literature_concentration_window_receipt_bindings",',1),
    ('    hidden_comparison = _measurement_comparison.hidden_records(comparison_rows, records,',
     "    window_rows = list(_concentration_window.rows_from_values((state.get('last_local_outcome'),\n        state.get('child_reports'), state.get('current_report_update'), lookup_results)))\n    hidden_window = _concentration_window.hidden_records(window_rows, records,\n        state.get('literature_concentration_window_receipt_bindings'))\n    hidden_comparison = _measurement_comparison.hidden_records(comparison_rows, records,",1),
    ('or reference in hidden_comparison:', 'or reference in hidden_comparison or reference in hidden_window:',1),
    ('"requested_measurement_comparison_components", "requested_kinetic_summary_precision_components",',
     '"requested_concentration_window_components", "requested_measurement_comparison_components", "requested_kinetic_summary_precision_components",',1),
    ("    if isinstance(content, Mapping) and content.get('view') == 'measurement_comparison_components':",
     "    if isinstance(content, Mapping) and content.get('view') == 'concentration_window_components':\n        _section(parts, title, values(_pick(value, ('status', 'selected_tool', 'feedback'))))\n        _concentration_window.render_received(parts, content['cells'], section=_section, table=_table)\n        return\n    if isinstance(content, Mapping) and content.get('view') == 'measurement_comparison_components':",1),
    ('if (_worksheet_context(content) is not None or', 'if (_worksheet_context(content) is not None or list(_concentration_window.rows_from_values(content)) or',1),
    ("and (any(_worksheet_context(row.get('admitted_report'))", "and (any(_concentration_window.history_record(row) for row in content['records']) or any(_concentration_window.rows_from_values(content['records'])) or any(_worksheet_context(row.get('admitted_report'))",1),
    ('{"measurement_comparison_components", "kinetic_summary_precision_components", "endpoint_signal_components"}',
     '{"concentration_window_components", "measurement_comparison_components", "kinetic_summary_precision_components", "endpoint_signal_components"}',1),
    ('    measurement_comparisons = {}', '    measurement_comparisons = {}\n    concentration_windows = {}',1),
    ('            if isinstance(value, (list, tuple)) and value and all(_measurement_comparison.is_row(row) for row in value):',
     "            if isinstance(value, (list, tuple)) and value and all(_concentration_window.is_row(row) for row in value):\n                for row in value:\n                    concentration_windows.setdefault(row['sheet_ref'], []).append(row)\n            elif isinstance(value, (list, tuple)) and value and all(_measurement_comparison.is_row(row) for row in value):",1),
    ('    _measurement_comparison.render_received(parts, [row for rows in measurement_comparisons.values() for row in rows], section=_section, table=_table)',
     '    _concentration_window.render_received(parts, [row for rows in concentration_windows.values() for row in rows], section=_section, table=_table)\n    _measurement_comparison.render_received(parts, [row for rows in measurement_comparisons.values() for row in rows], section=_section, table=_table)',1),
    ("        received_comparison_sheets =", "        received_window_sheets = {r['sheet_ref'] for r in _concentration_window.rows_from_values(state.get('child_reports', ()))}\n        received_comparison_sheets =",1),
    ('        if comparison_forwarded or', "        window_forwarded = isinstance(content, Mapping) and content.get('view') == 'concentration_window_components' and content.get('sheet_ref') in received_window_sheets\n        if window_forwarded or comparison_forwarded or",1),
    ('(received_comparison_sheets |', '(received_window_sheets | received_comparison_sheets |',1),
    ('if (current_worksheet is not None or', 'if (current_worksheet is not None or list(_concentration_window.rows_from_values(state["current_report_update"])) or',1),
    ("    state = _measurement_comparison.state_view(state, lookup_results)",
     "    state = _measurement_comparison.state_view(state, lookup_results)\n    lookup_results = _concentration_window.sanitize_private(lookup_results, state.get('literature_concentration_window_receipt_bindings', {}))\n    state = _concentration_window.state_view(state, lookup_results)",1),
])
edit('literature_reference_parent_prompt.py',[
    ('    state = comparison_state_view(state, lookup_results)',
     "    state = comparison_state_view(state, lookup_results)\n    from .literature_concentration_window_render import state_view as window_state_view, sanitize_private as window_private\n    lookup_results = window_private(lookup_results, state.get('literature_concentration_window_receipt_bindings', {}))\n    state = window_state_view(state, lookup_results)",1),
    ('"literature_measurement_comparison_receipt_bindings")',
     '"literature_measurement_comparison_receipt_bindings", "literature_concentration_window_receipt_bindings")',1),
])
