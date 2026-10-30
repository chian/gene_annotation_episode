"""Controlled prompt rendering only; no paper, provider or scientific state."""
from pathlib import Path
from copy import deepcopy
import hashlib
import json
import sys
import time

OUT = Path(__file__).resolve().parent
BASE = OUT.parent
PIN = BASE / 'a105_kinetic_review_198/pin_001'
sys.dont_write_bytecode = True
sys.path[:0] = [str(PIN), str(PIN / 'tests')]

from gene_annotation_episode.domain import obj, canonical
from gene_annotation_episode.literature_experimental_prompt import render_literature_experimental_prompt
from gene_annotation_episode.literature_kinetic_storage import kinetic_cells_schema, COMPONENTS as KINETIC_COMPONENTS
from gene_annotation_episode.literature_channel_storage import channel_cells_schema
from gene_annotation_episode.literature_compiled_assay_storage import compiled_assay_cells_schema
from gene_annotation_episode.episode_contract_information import return_contract_information, expand_fact_form
from gene_annotation_episode.composition_information import CONTRACT_INFORMATION_PROFILE

cases = []
for source, schema in (
    ('literature_kinetic_cells', kinetic_cells_schema),
    ('literature_channel_cells', channel_cells_schema),
    ('literature_compiled_assay_cells', compiled_assay_cells_schema),
):
    declaration = schema()
    facts = {'literature': {source: {'type': 'array', 'meaning': 'Requested saved numerical evidence.',
                                   'report_schema': declaration}}}
    for profile in (None, CONTRACT_INFORMATION_PROFILE):
        mode = 'legacy' if profile is None else 'profile'
        state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
                 'contract_information_profile': profile, 'requested_form': obj({'numbers': declaration})}
        before = deepcopy(state)
        prompt = render_literature_experimental_prompt(state, 'Examine the assigned source experiment.')
        task = prompt.split('\n\nSTEERING\n')[0]
        name = source + '_' + mode + '_requested_form'
        with (OUT / (name + '.txt')).open('x') as stream:
            stream.write(prompt)
        row = {'case': name, 'TASK_characters': len(task),
               'contains_internal_formula_code_field': 'formula_code' in task,
               'contains_whole_kinetic_component_enum': all(s in task for s in KINETIC_COMPONENTS),
               'host_schema_unchanged': state == before and state['requested_form']['properties']['numbers'] == declaration,
               'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()}
        cases.append(row)
        if profile is not None:
            outcome = return_contract_information(facts_by_role=facts, permitted_child_roles=['literature'],
                                                 role='literature', source=source)
            original = deepcopy(outcome)
            lookup_state = {'literature_experimental_work': {'version': 'literature_experimental_task_v1'},
                            'contract_information_profile': profile}
            prompt = render_literature_experimental_prompt(lookup_state, 'Choose the requested experimental return.',
                                                           lookup_results=[outcome])
            task = prompt.split('\n\nSTEERING\n')[0]
            name = source + '_profile_return_lookup'
            with (OUT / (name + '.txt')).open('x') as stream:
                stream.write(prompt)
            submitted = obj({'chosen': {'$ref': 'episode-fact:' + source}})
            expanded = expand_fact_form(json.dumps(submitted), child_role='literature', facts_by_role=facts,
                                        permitted_child_roles=['literature'])
            cases.append({'case': name, 'TASK_characters': len(task),
                          'contains_internal_formula_code_field': 'formula_code' in task,
                          'contains_whole_kinetic_component_enum': all(s in task for s in KINETIC_COMPONENTS),
                          'explicit_alias_shown': 'episode-fact:' + source in task,
                          'host_outcome_unchanged': outcome == original,
                          'existing_alias_expands_exact_original_type': canonical(expanded['expanded_schema']['properties']['chosen']) == canonical(declaration),
                          'prompt_sha256': hashlib.sha256(prompt.encode()).hexdigest()})

imports = {n: str(Path(m.__file__).resolve()) for n, m in sys.modules.items()
           if getattr(m, '__file__', None) and n.startswith(('gene_annotation_episode', 'method_loop', 'test_'))}
outside = {n: p for n, p in imports.items() if not Path(p).is_relative_to(PIN)}
manifest = json.loads((BASE / 'a105_kinetic_review_198/PIN_001.json').read_text())
changed = [p for p, sha in manifest.items() if hashlib.sha256((PIN / p).read_bytes()).hexdigest() != sha]
result = {'time': time.time(), 'scope': 'Actual public deterministic renderer and return-contract lookup functions on controlled synthetic empty-science state, frozen198 snapshot. No claim of whole assembled runtime reproduction or current199 behavior.',
          'cases': cases, 'imports_outside_pin': outside, 'changed_pinned_files': changed,
          'arbitrary_prompt_size_gate_used': False, 'production_changes': []}
with (OUT / 'ROOT_PROMPT_PROBE_001.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result, indent=2))
raise SystemExit(bool(outside or changed))
