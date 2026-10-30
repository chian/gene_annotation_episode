from pathlib import Path
p = Path('gene_annotation_episode/bvbrc_comparative_systems_tool_info.py')
p.write_text(p.read_text().replace('input.kind=exact_artifact', 'input.kind=possessed_artifact'))
p = Path('tests/test_bvbrc_comparative_systems_episode_flow.py')
s = p.read_text()
original = Path('tests/test_bvbrc_proteome_directional_episode_path.py').read_text()
imports = '''
import asyncio
from method_loop.archive import iter_json
from gene_annotation_episode.api_bvbrc_appservice import BVBRCAppServiceService
from gene_annotation_episode.episode_bindings import EpisodeBindingRegistry
from gene_annotation_episode.execution_service_setup import ExecutionServiceFactory
from gene_annotation_episode.numerical import NumericBand, YieldController, YieldEstimate, YieldParameters
from gene_annotation_episode.runtime import Workflow, _compile_form
from gene_annotation_episode.scientific_process_library import ScientificProcessLibrary
from gene_annotation_episode.scientific_process_setup import prepare_scientific_binding
from gene_annotation_episode.tools import ToolRegistry
from bvbrc_minhash_episode_fixture import PUBLICATION
from test_api_bvbrc_appservice import PREFIX, OBJECT_UUID
from test_bvbrc_appservice_inputs import NativeClient
from test_execution_episodes_family import launch_assignment
from test_execution_wiring import child, form
from test_practical_runtime import selected
from test_public_search import Client
'''
body = original[original.index('def test_actual_selected_tool_shared_workflow_native_publication_and_typed_parent_return'):]
a = body.index('    fields = selected_fields()')
b = body.index('    request = assignment[\'request\']')
body = body[:a] + "    selected_selector = result_selector()\n    assignment = api_assignment(query())\n" + body[b:]
body = body.replace('/controlled/proteome/', '/controlled/comparative/').replace('GenomeComparison','ComparativeSystems')
body = body.replace("native('2221')", "(FIXTURES / 'families.json').read_bytes()")
body = body.replace("'bvbrc_proteome', 'adapter_version': '2'", "adapter.ADAPTER_ID, 'adapter_version': adapter.ADAPTER_VERSION")
body = body.replace("'directional-shared-workflow'", "'comparative-shared-workflow'")
a = body.index('        parent_schema =')
b = body.index("        result_schema = form('execution_result_refs')", a)
body = body[:a] + "        parent_schema = parent_form_schema(requested_selection(selected_selector['requested_schema']))\n" + body[b:]
body = body.replace("['directional']", "['native']").replace("'proteome_directional_report'", "'family_summary'")
body = body.replace("case['parameters']['directional_documents'][0]['declared_format']", "declaration()")
body = body.replace('bvbrc.proteome_comparison', 'bvbrc.comparative_systems').replace('DIRECTIONAL_SOURCES','FACT_SOURCES')
body = body.replace('Return the requested exact displayed protein correspondence measurements', 'Return the requested stored ComparativeSystems measurements and their populations')
a = body.index("        assert all(len(rows) == 1")
b = body.index("        assert (archived['units_consumed']", a)
body = body[:a] + '''        assert all(len(rows) == 1 for rows in forwarded.values())
        assert returned['completed']
        selected_values = {row['field']: row['value'] for rows in forwarded.values() for row in rows}
        assert selected_values['occurrences']['values'][0]['value'] == 3
        assert selected_values['occupancy']['values'][0]['output']['value'] == 2 / 3
        assert selected_values['requirements']['values'] == []
        assert len(selected_values['qualification']['values']) == 4
''' + body[b:]
body = body.replace("result_ref = returned['fact4'][0]['source_ref']", "result_ref = next(iter(forwarded.values()))[0]['source_ref']")
p.write_text(s + '\n' + imports + '\n\n' + body)
