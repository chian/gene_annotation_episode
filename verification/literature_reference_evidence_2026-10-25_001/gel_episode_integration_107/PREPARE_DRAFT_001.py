"""Prepare reviewable drafts only; never write shared production files."""
import ast
from pathlib import Path

base=Path(__file__).resolve().parent
package=Path('gene_annotation_episode')
def converted(text):
    return text.replace('controlled_response_descriptor','gel_descriptor').replace('controlled_response_evidence_origin','gel_evidence_origin').replace('controlled_response','gel').replace('CONTROLLED_RESPONSE','GEL').replace('LiteratureControlledResponseRepository','LiteratureGelRepository').replace('literature.gel.source_v3.populate','literature.gel.populate').replace('controlled-response','gel').replace('controlled response','gel').replace('CONTROLLED_COMPONENTS','GEL_COMPONENTS')
def clone_nodes(source,predicate):
    lines=source.splitlines(keepends=True);nodes=[n for n in ast.walk(ast.parse(source)) if predicate(n)]
    for node in sorted(nodes,key=lambda n:n.lineno,reverse=True):
        chunk=''.join(lines[node.lineno-1:node.end_lineno]);lines[node.end_lineno:node.end_lineno]=[converted(chunk)]
    return ''.join(lines)
s=(package/'literature_episodes.py').read_text()
s=clone_nodes(s,lambda n:isinstance(n,ast.If) and ast.unparse(n.test)=='self.controlled_response_population')
s=clone_nodes(s,lambda n:isinstance(n,ast.FunctionDef) and n.name in ('_controlled_response_repository','_controlled_response_bindings'))
a=s.index('        if type(controlled_response_population) is not bool:');b=s.index('        from .composition_information',a)
s=s[:b]+converted(s[a:b])+s[b:]
s=s.replace('def _population_catalog(*, ratio_source_population=False, controlled_response_population=False):','def _population_catalog(*, ratio_source_population=False, controlled_response_population=False, gel_population=False):')
s=clone_nodes(s,lambda n:isinstance(n,ast.If) and ast.unparse(n.test)=='controlled_response_population' and n.col_offset==4)
s=s.replace('controlled_response_descriptor=None, controlled_response_evidence_origin="reported_source"):', 'controlled_response_descriptor=None, controlled_response_evidence_origin="reported_source",\n                 gel_population=False, gel_descriptor=None, gel_evidence_origin="reported_source"):')
s=s.replace('controlled_response_population=self.controlled_response_population)', 'controlled_response_population=self.controlled_response_population, gel_population=self.gel_population)')
s=s.replace('"literature.controlled_response.source_v3.populate"}:', '"literature.controlled_response.source_v3.populate", "literature.gel.populate"}:')
s=s.replace('"literature.controlled_response.source_v3.populate": self._controlled_response_repository,', '"literature.controlled_response.source_v3.populate": self._controlled_response_repository,\n                        "literature.gel.populate": self._gel_repository,')
s=s.replace('Exact saved controlled-response component keys and views, preserving each alternative\'s scientific meaning, source origins, uncertainty, controls and partial support. Conditional graph-reading bounds are not sampling uncertainty. Derived views do not grant possession of raw operands or covariance. Dependent representations do not create independent evidence, target transfer or annotation credit.', 'Exact saved controlled-response component keys and views, preserving each alternative\'s scientific meaning, source origins, uncertainty, controls and partial support. Conditional graph-reading bounds are not sampling uncertainty. Derived views do not grant possession of raw operands or covariance. Dependent representations do not create independent evidence, target transfer or annotation credit.')
s=s.replace('Exact saved controlled-response component keys and views', 'Exact saved controlled-response component keys and views')
# GEL fact meaning is independent of controlled-response terminology.
a=s.index('            result["literature_gel_component_cells"] = {"type": "array", "meaning":');b=s.index('\n                "report_schema": gel_cells_schema()}',a)
s=s[:a]+'''            result["literature_gel_component_cells"] = {"type": "array", "meaning":
                "Exact saved gel display components and coherent ROI alternatives with source-backed experiment/lane meanings, actual origin, exact arithmetic, units, method, dependence and partial available-only sensitivity. Image darkness is not calibrated molecular occupancy; ROI ranges are not sampling confidence intervals. Derived returns grant no unrequested raw operands, target transfer or annotation credit.",'''+s[b:]
ast.parse(s);(base/'literature_episodes.py.draft').write_text(s)
s=(package/'episode_services.py').read_text()
s=clone_nodes(s,lambda n:isinstance(n,ast.FunctionDef) and n.name=='literature_controlled_response_repository')
ast.parse(s);(base/'episode_services.py.draft').write_text(s)
s=(package/'communication.py').read_text()
s=clone_nodes(s,lambda n:isinstance(n,ast.If) and ast.unparse(n.test)=="source == 'literature_controlled_response_component_cells'")
s=s.replace('node.get("x-source") == "literature_controlled_response_component_cells"', 'node.get("x-source") in {"literature_controlled_response_component_cells", "literature_gel_component_cells"}')
ast.parse(s);(base/'communication.py.draft').write_text(s)
print('Prepared three non-production drafts; production unchanged.')
s=(package/'literature_experimental_prompt.py').read_text()
s=s.replace('from .literature_controlled_response_prompt import CONTROLLED_RESPONSE_TASK', 'from .literature_controlled_response_prompt import CONTROLLED_RESPONSE_TASK\nfrom .literature_gel_prompt import GEL_TASK')
s=s.replace('    "requested_controlled_response_component_keys", "literature_controlled_response_return_bindings",', '    "requested_controlled_response_component_keys", "literature_controlled_response_return_bindings",\n    "requested_gel_component_keys", "literature_gel_return_bindings",')
a=s.index('    from .literature_controlled_response_render import hidden_records');b=s.index('    selected = {}',a)
chunk=s[a:b];s=s[:b]+converted(chunk).replace('controlled','gel')+s[b:]
s=s.replace('or reference in hidden_controlled:', 'or reference in hidden_controlled or reference in hidden_gel:')
s=clone_nodes(s,lambda n:isinstance(n,ast.If) and ast.unparse(n.test)=="state.get('literature_controlled_response_work', {}).get('version') == 'literature_controlled_response_task_v1'")
s=s.replace('"requested_controlled_response_component_keys", "constraints",', '"requested_controlled_response_component_keys", "requested_gel_components", "requested_gel_views", "requested_gel_component_keys", "constraints",')
s=s.replace('        controlled_assignment=None):', '        controlled_assignment=None, gel_bindings=None, gel_assignment=None):')
a=s.index('    from .literature_controlled_response_render import render_own_result');b=s.index('    metadata = _pick(value',a)
chunk=s[a:b];addition=converted(chunk).replace('controlled_','gel_').replace('row["kind"]','row["view"]').replace('records=gel_records','records=controlled_records')
s=s[:b]+addition+s[b:]
s=s.replace('ratio_source_meanings=None, controlled_bindings=None):', 'ratio_source_meanings=None, controlled_bindings=None, gel_bindings=None):')
s=s.replace('    controlled = {}\n', '    controlled = {}\n    gel = {}\n')
s=s.replace('    from .literature_controlled_response_render import is_row as controlled_row, render_received as controlled_received', '    from .literature_controlled_response_render import is_row as controlled_row, render_received as controlled_received\n    from .literature_gel_render import is_row as gel_row, render_received as gel_received')
a=s.index('            if isinstance(value, (list, tuple)) and value and all(controlled_row');b=s.index('            elif (isinstance(value',a)
s=s[:b]+s[a:b].replace('            if ', '            elif ',1).replace('controlled','gel')+s[b:]
a=s.index('    for rows in controlled.values():');b=s.index('\n\n',a)
s=s[:b]+'\n'+s[a:b].replace('controlled','gel')+s[b:]
s=s.replace('    controlled_bindings = state.get("literature_controlled_response_return_bindings")', '    controlled_bindings = state.get("literature_controlled_response_return_bindings")\n    gel_bindings = state.get("literature_gel_return_bindings")')
s=s.replace("        received_controlled_sheets = {row['sheet_ref'] for row in controlled_rows(state.get('child_reports', ()))}", "        received_controlled_sheets = {row['sheet_ref'] for row in controlled_rows(state.get('child_reports', ()))}\n        from .literature_gel_render import rows_from_reports as gel_rows\n        received_gel_sheets = {row['sheet_ref'] for row in gel_rows(state.get('child_reports', ()))}")
s=s.replace('(received_ratio_sheets | received_controlled_sheets)', '(received_ratio_sheets | received_controlled_sheets | received_gel_sheets)')
s=s.replace('controlled_bindings=controlled_bindings, controlled_assignment=state.get("literature_assignment"))', 'controlled_bindings=controlled_bindings, controlled_assignment=state.get("literature_assignment"),\n                gel_bindings=gel_bindings, gel_assignment=state.get("literature_assignment"))')
s=s.replace('            controlled_bindings=controlled_bindings)', '            controlled_bindings=controlled_bindings, gel_bindings=gel_bindings)')
ast.parse(s);(base/'literature_experimental_prompt.py.draft').write_text(s)
s=(package/'literature_reference_parent_prompt.py').read_text()
s=s.replace('"literature_ratio_source_return_meanings", "literature_controlled_response_return_bindings")', '"literature_ratio_source_return_meanings", "literature_controlled_response_return_bindings",\n        "literature_gel_return_bindings")')
ast.parse(s);(base/'literature_reference_parent_prompt.py.draft').write_text(s)
print('Prepared two more non-production prompt drafts; production unchanged.')
# Exact possessed semantic meanings must not depend on generic working-state pagination.
p=base/'literature_episodes.py.draft';s=p.read_text()
s=s.replace('            result["literature_gel_return_bindings"] = self._gel_bindings(context)', '            result.update(self._gel_display_context(context))')
needle='    def _rate_fact_sources(self):'
addition='''    def _gel_display_context(self, context):
        """Actual possessed meaning records, outside generic working-state pagination."""
        bindings = self._gel_bindings(context)
        records = {}
        for entries in bindings.values():
            for reference, binding in entries.items():
                if binding["category"] != "scientific_meaning":
                    continue
                if binding["record_ref"] != reference or reference not in context.received_record_refs:
                    raise ContractError("gel_semantic_display_record_not_received")
                record = self._require(reference, context.scope, "reference")
                if record.get("id") != reference or record.get("record_type") != "reference":
                    raise ContractError("gel_semantic_display_record_mismatch")
                records[reference] = record
        return {"literature_gel_return_bindings": bindings, "literature_gel_return_records": records}

'''
assert needle in s;s=s.replace(needle,addition+needle,1);ast.parse(s);p.write_text(s)
p=base/'literature_experimental_prompt.py.draft';s=p.read_text()
s=s.replace('    "requested_gel_component_keys", "literature_gel_return_bindings",', '    "requested_gel_component_keys", "literature_gel_return_bindings", "literature_gel_return_records",')
s=s.replace('controlled_assignment=None, gel_bindings=None, gel_assignment=None):', 'controlled_assignment=None, gel_bindings=None, gel_assignment=None, gel_records=None):')
s=s.replace('records=controlled_records, bindings=gel_bindings)', 'records=gel_records, bindings=gel_bindings)')
s=s.replace('controlled_bindings=None, gel_bindings=None):', 'controlled_bindings=None, gel_bindings=None, gel_records=None):')
s=s.replace('gel_received(parts, rows, records or {},', 'gel_received(parts, rows, gel_records or records or {},')
s=s.replace('    gel_bindings = state.get("literature_gel_return_bindings")', '    gel_bindings = state.get("literature_gel_return_bindings")\n    gel_records = {**controlled_records, **state.get("literature_gel_return_records", {})}')
s=s.replace('gel_bindings=gel_bindings, gel_assignment=state.get("literature_assignment"))', 'gel_bindings=gel_bindings, gel_assignment=state.get("literature_assignment"), gel_records=gel_records)')
s=s.replace('controlled_bindings=controlled_bindings, gel_bindings=gel_bindings)', 'controlled_bindings=controlled_bindings, gel_bindings=gel_bindings, gel_records=gel_records)')
ast.parse(s);p.write_text(s)
p=base/'literature_reference_parent_prompt.py.draft';s=p.read_text().replace('        "literature_gel_return_bindings")','        "literature_gel_return_bindings", "literature_gel_return_records")');ast.parse(s);p.write_text(s)
print('Prepared exact possessed semantic display context beyond working-state page; production unchanged.')
