"""Prepare a reviewable delta only; never modify the live shared runtime."""
from pathlib import Path
import difflib
import hashlib

out = Path(__file__).resolve().parent
original = (out / 'runtime.py').read_text()
assert hashlib.sha256(original.encode()).hexdigest() == '07b9aafe11440a57a3d681abe694f57b8ff2e91191a3850b3bb3781d32fa85bc'
result = original

def replace(before, after):
    global result
    assert result.count(before) == 1, before[:120]
    result = result.replace(before, after)

replace('from method_loop.durable import DurableExecutionStore, EventTargetError, canonical\n',
    'from method_loop.durable import DurableExecutionStore, EventTargetError, canonical\n'
    'from . import literature_numerical_contracts\n')
replace('def _compile_form(text, extra_sources=None):\n    schema = validate_closed_schema(parse_json_object(text))\n    extra_sources = runtime_report_sources() | (extra_sources or {})',
    'def _compile_form(text, extra_sources=None, *, include_runtime_sources=True):\n'
    '    schema = validate_closed_schema(parse_json_object(text))\n'
    '    extra_sources = (runtime_report_sources() if include_runtime_sources else {}) | (extra_sources or {})')
replace('            if profile is not None:\n                self.workflow.validate_contract_information(saved)\n',
    '            if profile is not None:\n                self.workflow.validate_contract_information(saved)\n'
    '            if literature_numerical_contracts.SAVED_MEMBER in saved:\n'
    '                if profile is not None:\n'
    "                    raise WorkflowError('original_literature_numerical_profile_mismatch')\n"
    '                literature_numerical_contracts.validate_frozen_contracts(saved)\n')
replace('            saved = {"context": context, "schema": schema}\n        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:',
    '            saved = {"context": context, "schema": schema}\n'
    '            if profile is None:\n'
    '                frozen = self.workflow.freeze_literature_numerical_contracts(self, context, schema)\n'
    '                if frozen is not None:\n'
    '                    saved[literature_numerical_contracts.SAVED_MEMBER] = frozen\n'
    '        if self.workflow.decision_protocol == DECISION_EXCHANGE_PROTOCOL:')
replace('        saved = {"context": context, "schema": schema}\n        if transport is not None:',
    '        saved = {"context": context, "schema": schema,\n'
    '            **({literature_numerical_contracts.SAVED_MEMBER: saved[literature_numerical_contracts.SAVED_MEMBER]}\n'
    '                if literature_numerical_contracts.SAVED_MEMBER in saved else {})}\n'
    '        if transport is not None:')
replace("            if original_request is not None and 'contract_information' in original_request:\n",
    "            if original_request is not None and ('contract_information' in original_request\n"
    '                    or literature_numerical_contracts.SAVED_MEMBER in original_request):\n')
replace('    def expanded_contract_form(self, source, selection, index, role, *, original_child=True):\n',
'''    def freeze_literature_numerical_contracts(self, source, context, schema):
        """Freeze a bounded declaration surface only for fresh literature tasks."""
        from .literature_experimental_prompt import is_literature_experimental_context
        if not is_literature_experimental_context(context):
            return None
        roles = list(self.available_child_roles(source))
        builtins = {name: {'type': 'number' if name == 'credit' else 'array',
            'meaning': FACT_MEANINGS[name]} for name in FACT_SOURCES}
        facts = {role: builtins | _plain(self.report_sources(role)) for role in roles}
        return literature_numerical_contracts.freeze_contracts(facts_by_role=facts,
            permitted_child_roles=roles, action_schema=schema)

    def expanded_contract_form(self, source, selection, index, role, *, original_child=True):
''')
replace("        if self.contract_information_profile(source) is None:\n            return _compile_form(selection['schema_json'], self.report_sources(role)), None\n",
'''        if self.contract_information_profile(source) is None:
            submitted = parse_json_object(selection['schema_json'])
            if not literature_numerical_contracts.uses_fact_references(submitted):
                # Existing literal legacy forms retain their original compiler,
                # declaration=None and registration semantics, including local
                # references inside existing exact native documents.
                return _compile_form(selection['schema_json'], self.report_sources(role)), None
            if original_child:
                identity = Episode.identity(self.context, self.grains[role], f'child_{index}', parent_path=source.path)
                child = self.journal.row('runtime_episodes', identity.episode_id)
                if child is not None:
                    request = json.loads(child['request'])
                    declaration = request['message'].get('report_contract_declaration')
                    if declaration is None:
                        raise WorkflowError('original_report_contract_declaration_unavailable')
                    schema = validate_saved_fact_form(child_role=role, submitted_schema_json=selection['schema_json'],
                        expanded_schema=request['report_contract']['measurements']['schema'], declaration=declaration)
                    return schema, declaration
            row = self.journal.row('runtime_model_calls', source.episode_id, index)
            saved = json.loads(row['request']) if row is not None and row['purpose'] == 'decision' else {}
            if literature_numerical_contracts.SAVED_MEMBER not in saved:
                # Never manufacture a declaration snapshot for an old saved
                # decision. Its original literal-only route stays unchanged.
                return _compile_form(selection['schema_json'], self.report_sources(role)), None
            record = literature_numerical_contracts.validate_frozen_contracts(saved)
            result = literature_numerical_contracts.expand_numerical_form(selection['schema_json'],
                child_role=role, saved=saved)
            schema = _compile_form(_json(result['expanded_schema']), record['source_types_by_role'][role],
                include_runtime_sources=False)
            validate_saved_fact_form(child_role=role, submitted_schema_json=selection['schema_json'],
                expanded_schema=schema, declaration=result['declaration'])
            return schema, result['declaration']
''')
(out / 'runtime.proposed.py').write_text(result)
(out / 'runtime.unapplied.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),result.splitlines(True),fromfile='a/gene_annotation_episode/runtime.py',tofile='b/gene_annotation_episode/runtime.py')))
print('Prepared unapplied runtime delta; live runtime untouched.')
