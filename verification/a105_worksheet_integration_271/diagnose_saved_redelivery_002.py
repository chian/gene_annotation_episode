"""Replay only public receive metadata in a disposable controlled-state copy."""
from pathlib import Path
import json
import shutil
import sys
import traceback
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT))
original = HERE / 'attempt_001/pytest/test_selected_worksheet_links_2/state'
copied = HERE / 'redelivery_receive_diagnostic_002'
shutil.copytree(original, copied)

from gene_annotation_episode.state import Store
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.runtime import _references_in

store = Store(copied)
result = {'scope': 'Explicit controlled fixture only: saved typed form/commission and ordinary receipt metadata.',
    'private_provider_payloads_read': False, 'scientific_readers_or_calculators_called': False,
    'original_state_changed': False, 'copied_state': str(copied.relative_to(ROOT))}
try:
    row = store.db.execute('SELECT * FROM runtime_report_attempts WHERE failure IS NULL ORDER BY rowid DESC LIMIT 1').fetchone()
    episode = store.db.execute('SELECT path,request FROM runtime_episodes WHERE episode_id=?', (row['parent_episode_id'],)).fetchone()
    request = json.loads(episode['request'])
    form, contract = json.loads(row['form']), json.loads(row['contract'])
    schema = contract['measurements']['schema']
    scope = request['message']['scope']
    sources = list(dict.fromkeys(r['evidence_source_ref']
        for field in ('native_parameter', 'precision') for r in form[field]))
    context = BindingContext(row['run_id'], row['parent_episode_id'], 'annotation',
        tuple(map(tuple, json.loads(episode['path']))), scope,
        request['message'].get('episode_assignment', {}), request, tuple(sources))
    host = SimpleNamespace(store=store, run_id=row['run_id'], tools=None)
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, reference_parent_sources=sources)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    stage = 'ordinary_references'
    references = _references_in({}, store.get, forms=[(form, schema)],
        reference_subset=lambda refs: store.reference_subset(refs, scope))
    result['ordinary_reference_count'] = len(references)
    stage = 'binding_received_form_references'
    result['binding_references'] = binding.received_form_references(context, form, schema,
        f"{row['run_id']}:{row['parent_episode_id']}:{row['decision_index']}:typed_form")
    result['status'] = 'receive_binding_passed'
except Exception as error:
    result.update(status='failed', stage=stage, exception_type=type(error).__name__,
        error=str(error), traceback=traceback.format_exc())
finally:
    store.close()
with (HERE / 'REDELIVERY_RECEIVE_DIAGNOSTIC_002.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result, indent=2))
