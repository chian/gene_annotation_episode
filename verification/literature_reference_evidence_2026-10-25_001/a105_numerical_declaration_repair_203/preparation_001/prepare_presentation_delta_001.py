"""Prepare presentation edits only; keep the live199 sources unchanged."""
from pathlib import Path
import difflib
import hashlib
out=Path(__file__).resolve().parent
root=Path(__file__).resolve().parents[4]

def save(name, original, proposed):
 (out/(name+'.baseline199')).write_text(original)
 (out/name.replace('.py','.proposed.py')).write_text(proposed)
 (out/name.replace('.py','.unapplied.patch')).write_text(''.join(difflib.unified_diff(original.splitlines(True),proposed.splitlines(True),fromfile='a/gene_annotation_episode/'+name,tofile='b/gene_annotation_episode/'+name)))

name='literature_numerical_return_presentation.py'
original=(root/'gene_annotation_episode'/name).read_text()
assert hashlib.sha256(original.encode()).hexdigest()=='64fa87f5f7a21bcfcb824368d169fe881b7952889751d99802f548de8066e57a'
result=original
start=result.index('MEANINGS = {');end=result.index('\n\n\ndef _copy',start)
result=result[:start]+'''MEANINGS = {source: meaning + ' The host supplies the saved values under the original complete closed type; do not author or alter this recorded field.'
    for source, meaning in RETURN_MEANINGS.items()}


def _declaration_text(source):
    return ('To request this recorded return from a child, choose a top-level field whose declaration '
        'contains only $ref with the exact value episode-fact:' + source
        + '. The host expands that explicit reference to the original complete closed type before commissioning. '
        'Select the needed numerical components through the child assignment. '
        'Keep model-authored interpretations in separate fields with their original constrained meanings.')
''' +result[end:]
start=result.index('def _registered(source):');end=result.index('\n\ndef _compact',start)
result=result[:start]+result[end+2:]
result=result.replace('from .domain import canonical','from .literature_numerical_contracts import RETURN_MEANINGS, is_registered_schema')
result=result.replace('Only exact channel, compiled-assay and ion-discrimination declarations receive this treatment.',
    'Only exact registered A105 numerical declarations receive this treatment.')
result=result.replace("    if canonical(_copy(node)) != canonical(_registered(source)):\n", "    if not is_registered_schema(node):\n")
result=result.replace("    shown = {name: _copy(value) for name, value in node.items() if name != 'items'}\n    shown['description'] = MEANINGS[source]",
    "    shown = {name: _copy(node[name]) for name in ('type', 'x-source', 'minItems', 'maxItems', 'uniqueItems')\n        if name in node}\n    shown['description'] = MEANINGS[source] + ' ' + _declaration_text(source)")
start=result.index('def requested_return_text(result):');end=result.index('\n\n\n__all__',start)
result=result[:start]+'''def requested_return_text(result):
    """Present an exact requested return without exposing its numerical sheet.

    The original lookup retains its complete schema/text for host custody.
    The same explicit fact reference preserves the original requested type.
    """
    source = result.get('source')
    if (result.get('information_kind') != 'return_contract_information_v1' or source not in MEANINGS
            or not is_registered_schema(result.get('report_schema'), source=source)):
        return None
    return MEANINGS[source] + '\\n\\n' + _declaration_text(source)
''' +result[end:]
save(name,original,result)

name='literature_experimental_prompt.py'
original=(root/'gene_annotation_episode'/name).read_text()
assert hashlib.sha256(original.encode()).hexdigest()=='485b92c6d9a532e1a50257f50850e83a9d97019b13c7c1b68b1dbdf18186c0a0'
start=original.index('SAVED_NUMERICAL_RETURN_TASK = ');end=original.index('\n\nEXPERIMENTAL_TASK',start)
result=original[:start]+'''SAVED_NUMERICAL_RETURN_TASK = """When requesting saved numerical experimental components listed as available recorded return sources, choose a top-level return field whose declaration contains only $ref with the exact value episode-fact:<source>, using that source's declared name. The host expands this explicitly selected declaration to the original complete closed type before commissioning; the numerical sheet itself remains with the host. Choose the needed components through the child assignment. Keep bound fact fields out of initial_report_json; the runtime fills them from saved results. Use separate constrained fields for interpretations and unresolved questions, preserving the parent's requested meanings. Do not ask the child to rewrite saved numerical cells as model-authored report values."""
''' + original[end:]
save(name,original,result)

name='literature_reference_parent_prompt.py'
original=(root/'gene_annotation_episode'/name).read_text()
assert hashlib.sha256(original.encode()).hexdigest()=='8e2af54415ca6abee8cc50c91159356cf3ec68f7bd3f90a3c60ef7ca6f87804d'
result=original.replace('from .schema_information_text import render_schema_information\n',
    'from .schema_information_text import render_schema_information\nfrom .literature_numerical_return_presentation import state_view\n')
result=result.replace('    descriptor = _descriptor(state)\n',
    '    state = state_view(state)\n    descriptor = _descriptor(state)\n')
save(name,original,result)
print('Prepared three presentation deltas; live sources unchanged.')
