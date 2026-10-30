from pathlib import Path
import difflib,json,hashlib
ROOT=Path('/home/chia/repos/gene_annotation_episode')
DEST=Path(__file__).parent/'draft/gene_annotation_episode'
def change(text,old,new):
 assert text.count(old)==1,old
 return text.replace(old,new)
def write(name,text):
 (DEST/name).write_text(text)
p=ROOT/'gene_annotation_episode/literature_reaction_inputs.py'; s=p.read_text()
s=change(s,'    _keys(data, ("version", "ratio", "budget"), "data_source")\n    if data["version"] != DATA_VERSION:', '''    from .literature_reaction_meanings import DATA_VERSION as MEANINGS_DATA_VERSION
    version = data.get("version") if isinstance(data, dict) else None
    _keys(data, ("version", "ratio", "budget", "meanings") if version == MEANINGS_DATA_VERSION
          else ("version", "ratio", "budget"), "data_source")
    if version not in (DATA_VERSION, MEANINGS_DATA_VERSION):''')
s=change(s,'    return {"version": VERSION, "arguments": deepcopy(arguments),', '''    from .literature_reaction_meanings import (
        DATA_VERSION as MEANINGS_DATA_VERSION, INPUT_VERSION as MEANINGS_INPUT_VERSION, read_meanings,
    )
    meanings = (read_meanings(observations["meanings"], observations, sources)
        if observations is not None and observations["version"] == MEANINGS_DATA_VERSION else None)
    return {"version": VERSION if meanings is None else MEANINGS_INPUT_VERSION,
            "arguments": deepcopy(arguments),''')
s=change(s,'            "calculation_inputs": inputs}', '            "calculation_inputs": inputs,\n            **({"meanings": meanings} if meanings is not None else {})}')
write(p.name,s)
p=ROOT/'gene_annotation_episode/literature_reaction_storage.py'; s=p.read_text()
s=change(s,'\n\nPROVIDER = ', '''
from .literature_reaction_meanings import (
    INPUT_VERSION as MEANINGS_INPUT_VERSION, RECORD_VERSION as MEANINGS_RECORD_VERSION,
    NAMESPACE as MEANINGS_NAMESPACE, BASES, MODEL_FIELDS, RESOURCE_FIELDS, DEMAND_FIELDS,
    direct_references as meaning_direct_references, publish_meanings, semantic_metadata,
    binding_references,
)


PROVIDER = ''')
s=change(s,'    def _provenance(self, context, reference):', '''    def semantic_projection(self):
        return LiteratureReactionSemanticProjection(self.store, self.run_id)

    def cells_schema(self):
        return reaction_cells_schema()

    def _row_metadata(self, saved):
        return _metadata(saved["extraction"], saved["sheet"])

    def validate_empty_return_family(self, context):
        if context.run_id != self.run_id:
            raise ContractError("literature_run_mismatch")
        versions = set()
        for row in self.store.db.execute(f"SELECT outcome FROM {self.operations_table} "
                "WHERE run_id=? AND episode_id=?", (self.run_id, context.episode_id)):
            outcome = json.loads(row["outcome"])
            if outcome.get("status") == "completed":
                source = self.store.get(outcome["result"]["sheet_ref"])
                if source.get("provider") == self.provider:
                    versions.add(source.get("version"))
        if self.record_version not in versions and versions & {
                "literature_reaction_record_v2", MEANINGS_RECORD_VERSION}:
            raise ContractError("literature_reaction_projection_version_mismatch")

    def _provenance(self, context, reference):''')
s=change(s,'        extraction = read_reaction_inputs(args, read_source=read_source)\n', '        extraction = read_reaction_inputs(args, read_source=read_source)\n        direct = meaning_direct_references(extraction, direct)\n')
s=change(s,'        payload = {"version": self.record_version,', '''        record_version = (MEANINGS_RECORD_VERSION if extraction["version"] == MEANINGS_INPUT_VERSION
                          else self.record_version)
        payload = {"version": record_version,''')
s=change(s,'            payload["experimental_bindings"] = bindings\n', '''            payload["experimental_bindings"] = bindings
            semantic_bindings = (publish_meanings(extraction, publish)
                if record_version == MEANINGS_RECORD_VERSION else None)
            if semantic_bindings is not None:
                payload["semantic_bindings"] = semantic_bindings
            metadata = _metadata(extraction, sheet)
            if semantic_bindings is not None:
                metadata = semantic_metadata(metadata, semantic_bindings,
                    extraction["calculation_inputs"], sheet)
''')
s=change(s,'"version": self.record_version, "retrieved_at": None, "parent_source_refs": parents}', '"version": record_version, "retrieved_at": None, "parent_source_refs": parents}')
s=change(s,'*(reference for reference in bindings.values() if reference)])),', '''*(reference for reference in bindings.values() if reference),
                    *(binding_references(semantic_bindings) if semantic_bindings is not None else [])])),''')
s=change(s,'                    **_metadata(extraction, sheet)}, "feedback": None}', '                    **metadata}, "feedback": None}')
s=change(s,'    def read(self, sheet_ref):\n        saved = super().read(sheet_ref)', '''    def read(self, sheet_ref):
        if (self.record_version != MEANINGS_RECORD_VERSION
                and self.store.get(sheet_ref).get("version") == MEANINGS_RECORD_VERSION):
            return self.semantic_projection().read(sheet_ref)
        saved = super().read(sheet_ref)''')
s=change(s,'saved["direct_input_source_refs"] != _direct_references(args)', 'saved["direct_input_source_refs"] != meaning_direct_references(extraction, _direct_references(args))')
s=change(s,'            saved = self.read(reference)\n            for name in components:', '''            saved = self.read(reference)
            if saved["version"] != self.record_version:
                raise ContractError("literature_reaction_projection_version_mismatch")
            for name in components:''')
s=change(s,'                    **_metadata(saved["extraction"], saved["sheet"])})\n        validate_schema(rows, reaction_cells_schema())', '                    **self._row_metadata(saved)})\n        validate_schema(rows, self.cells_schema())')
s=change(s,'        validate_schema(cells, reaction_cells_schema())','        validate_schema(cells, self.cells_schema())')
s=s[:s.index('\n\n__all__ =')]+(Path(__file__).parent/'STORAGE_ADDITION_001.txt').read_text()
write(p.name,s)
p=ROOT/'gene_annotation_episode/literature_reaction_prompt.py';s=p.read_text()
s=change(s,'For resource claims identify', '''For the actual claim and each genuine alternative, preserve its source-supported reaction or functional meaning, prediction scale, and whether the prediction is reported, inferred, conditional or unresolved. Keep each resource's substance/property, biological setting, period, compartment and coefficient meaning linked to that same resource and to the actual output or demand basis. Identify what the demand measures. Missing descriptions do not erase conditional quantitative results. Names or stoichiometric expectations alone do not establish measured product identity, consumption, coupling or physiological availability.

For resource claims identify''')
write(p.name,s)
p=ROOT/'gene_annotation_episode/literature_episodes.py';s=p.read_text()
s=change(s,'                         "literature_reaction_storage.py", "literature_reaction_prompt.py",','''                         "literature_reaction_storage.py", "literature_reaction_prompt.py",
                         "literature_reaction_meanings.py", "literature_reaction_meanings_render.py",''')
s=change(s,'        from .literature_reaction_storage import reaction_cells_schema','        from .literature_reaction_storage import reaction_cells_schema, reaction_semantic_cells_schema')
s=change(s,'                "report_schema": reaction_cells_schema()},','''                "report_schema": reaction_cells_schema()},
            "literature_reaction_semantic_cells": {"type": "array", "meaning":
                "The same saved reference reaction/resource components with source-supported claim and alternative identities, named predictions and exact comparison membership. Resource meanings preserve supply basis, coefficient-to-demand linkage, period and compartment. Missing descriptions add no numerical gate. These are conditional source comparisons and fixed-consumption constraints, not extra assays, physiological sufficiency, target correspondence or annotation credit.",
                "report_schema": reaction_semantic_cells_schema()},''')
s=change(s,'                 REACTION_COMPONENTS, self.services.literature_reaction_repository),','''                 REACTION_COMPONENTS, self.services.literature_reaction_repository),
                ("literature_reaction_semantic_cells", "requested_reaction_components", REACTION_PROVIDER,
                 REACTION_COMPONENTS, self.services.literature_reaction_repository().semantic_projection),''')
s=change(s,'                    if namespace in {"literature_context_cells", "literature_context_semantic_cells"}:','''                    if namespace in {"literature_reaction_cells", "literature_reaction_semantic_cells"}:
                        if row.get("version") not in {"literature_reaction_record_v2", "literature_reaction_record_v3"}:
                            raise ContractError("literature_reaction_projection_version_mismatch")
                        if row.get("version") != adapter.record_version:
                            continue
                    if namespace in {"literature_context_cells", "literature_context_semantic_cells"}:''')
s=change(s,'                    if (namespace in {"literature_context_cells", "literature_context_semantic_cells"}','''                    if (namespace in {"literature_reaction_cells", "literature_reaction_semantic_cells"}
                            and not rows and context.assignment.get(requested_field) not in ([], ())):
                        repository().validate_empty_return_family(context)
                    if (namespace in {"literature_context_cells", "literature_context_semantic_cells"}''')
write(p.name,s)
p=ROOT/'gene_annotation_episode/literature_experimental_prompt.py';s=p.read_text()
s=change(s,'        _context_definitions(parts, content, records=controlled_records)','''        _context_definitions(parts, content, records=controlled_records)
        from .literature_reaction_meanings_render import render_meanings as reaction_meanings
        reaction_meanings(parts, content, controlled_records, section=_section, table=_table)''')
s=change(s,'"Admitted requested reaction components")','"Admitted requested reaction components", controlled_records=records)')
write(p.name,s)
rows=[]; patch=[]
for p in sorted(DEST.glob('*.py')):
 original=ROOT/'gene_annotation_episode'/p.name
 before=original.read_text() if original.exists() else ''
 after=p.read_text()
 patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/gene_annotation_episode/'+p.name,tofile='b/gene_annotation_episode/'+p.name))
 rows.append({'file':p.name,'original_sha256':hashlib.sha256(before.encode()).hexdigest() if original.exists() else None,'draft_sha256':hashlib.sha256(after.encode()).hexdigest()})
(Path(__file__).parent/'PROPOSED_PATCH_001.diff').write_text(''.join(patch))
(Path(__file__).parent/'DRAFT_MANIFEST_001.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({'files':len(rows),'patch_lines':len(patch)}))
