"""Controlled synthetic engineering context measurement; no paper/model calls."""
import asyncio
from copy import deepcopy
from functools import partial
import hashlib
import json
from pathlib import Path
import sys
import tempfile
sys.path[:0] = [str(Path.cwd()), str(Path.cwd()/'tests')]
from gene_annotation_episode.communication import plain
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import Workflow, TypedReportContract
from gene_annotation_episode.domain import obj
from gene_annotation_episode.literature_kinetic_storage import kinetic_cells_schema
from gene_annotation_episode.tools import ToolRegistry
from test_contract_information_runtime_059 import PresentedProvider, populate, run_child
from test_literature_kinetic_storage import setup
from test_runtime import FixtureController
from test_runtime_decision_exchanges import select

def size(value):
    return len((value if isinstance(value,str) else json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)).encode())

class CaptureProvider(PresentedProvider):
    def __init__(self):
        super().__init__([])
        self.instruction_texts=[]
    async def complete(self, episode_id, role, instructions, context, output_schema):
        self.instruction_texts.append(instructions)
        return await super().complete(episode_id,role,instructions,context,output_schema)

def probe(directory, output_directory):
    measurements=[]
    for profile in (None, CONTRACT_INFORMATION_PROFILE):
        for role in ('annotation','literature'):
            path=directory/('legacy' if profile is None else 'compact')/role
            store,seed,args=setup(path/'state')
            provider=CaptureProvider()
            value=Workflow(store,ToolRegistry(store),provider,path/'run','surface-fixture',
                lambda path,initial:FixtureController(str(path),initial,1),
                ScientificFindingProgress(FindingProgressPolicy(1)),
                initial_known_record_refs=list(seed.received_record_refs),
                episode_binding_factories=(partial(LiteratureEpisodes,rate_population=True,
                    contract_information_profile=profile,reference_parent_sources=[args['source_ref']]),),
                decision_protocol='decision_exchange_v1')
            root=value.build('annotation','root','Evaluate supplied synthetic reference evidence',plain(seed.scope))
            try:
                if role=='annotation':
                    empty={name:[] for name in store.reasoning_schema()['required']}
                    provider.script=iter([OSError('surface-captured')])
                    try: asyncio.run(root.run_async(value.context))
                    except OSError as error: assert str(error)=='surface-captured'
                else:
                    child=value.build('literature','case','Evaluate the synthetic reference experiment',plain(seed.scope),
                        parent=root.request.goal,parent_path=root.source.path,
                        contract=TypedReportContract('Fixture source investigation',obj({'saved_parameters':kinetic_cells_schema()}),lambda *_:True),initial={},episode_assignment=plain(seed.assignment))
                    provider.script=iter([OSError('surface-captured')])
                    try: run_child(child,value)
                    except OSError as error: assert str(error)=='surface-captured'
                text=provider.rendered[0]
                task,steering=text.split('\n\nSTEERING\n',1)
                schema=provider.schemas[0]
                parts=task.split('\n\n')
                sections=[]
                for i,part in enumerate(parts):
                    if i and ('|' in part or part.startswith('Schema information')):
                        sections.append({'section':parts[i-1][:140], 'bytes':size(part)})
                measurements.append({'profile':profile,'role':role,'prompt_bytes':size(text),'task_bytes':size(task),
                    'steering_bytes':size('STEERING\n'+steering),'output_schema_compact_json_bytes':size(schema),
                    'output_schema_rpc_json_bytes':len(json.dumps(schema,allow_nan=False).encode()),
                    'developer_instructions_bytes':size(provider.instruction_texts[0]),
                    'native_tool_definitions':None,
                    'byte_meaning':'Prompt and instructions are UTF-8 text bytes; schema compact and provider JSON encodings are measured separately. No token estimate or service context budget is inferred.',
                    'native_tool_meaning':'No native tools are exposed by the provider; actual available operation choices are in outputSchema and TASK.',
                    'task_sections':sorted(sections,key=lambda r:r['bytes'],reverse=True),
                    
                    'literature_operation_count':sum(row['name'].startswith('literature.') for row in value.episode_bindings.for_role('literature').catalog(seed))})
                if profile:
                    (output_directory/f'{role}_task_excerpt.txt').write_text('EXCERPT ONLY: actual recurring TASK is complete; see byte measurements.\n\n'+task[:7500])
            finally:store.close()
    return measurements

if __name__=='__main__':
    directory=Path(__file__).parent
    pin={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path('gene_annotation_episode')/n for n in ('literature_episodes.py','literature_experimental_prompt.py','literature_reference_parent_prompt.py','composition_information.py','runtime.py','providers.py')]}
    with tempfile.TemporaryDirectory(prefix='surface144-') as tmp:
        result=probe(Path(tmp),directory)
    after={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in pin}
    (directory/'measurements002.json').write_text(json.dumps({'pins_before':pin,'pins_after':after,'pinned_files_stable':pin==after,'measurements':result},indent=2))
    print(json.dumps([{k:v for k,v in row.items() if k!='task_sections'} for row in result],indent=2))
