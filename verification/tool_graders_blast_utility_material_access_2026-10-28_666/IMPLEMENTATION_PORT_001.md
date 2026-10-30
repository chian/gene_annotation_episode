# Selected utility bytes at existing source/material consumers

This is an implementation boundary for the existing requested-artifact rule,
not a goal, scope amendment, prompt, approval step or new access policy.
Root owns this correction. The original goal and utility return contracts stay
unchanged. No numerical sheet or calculator changes.

The demonstrated source path is ScientificProcessEpisodes.execute ->
WorkflowServices.execute_tool -> ToolRegistry._perform -> source_window or
Store.register_material/parse_material/material_read. A utility source reference
does not grant its bundle/auxiliary bytes, but these consumers presently omit
the utility provider's existing retained_reference_access check. A wrapper does
not create that grant. source.locate additionally receives no permitted refs
from scientific execution and therefore cannot work there at present.

Implement WorkflowServices.authenticate_source_byte_operands(context,
tool_name, arguments) -> None. Its five callers are material.from_source,
material.parse, material.read, source.read and source.locate. Resolve only the
actual selected source/artifact using Store metadata; do not open bytes, add
records, acquire files or issue another action. For material.parse/read, use
the selected material's original source. For source.read, factor its existing
representation choice into materials.source_window_selection(source,
representation) -> (artifact_ref, actual_representation, available_representations)
and share that function with source_window. Preserve text fallback, explicit
stdout/stderr selection, errors and return shape. For source.locate use its
existing received_source metadata validator, which has no text fallback.

Use the bound results provider's native_blast_utility_results.
retained_reference_access(context, artifact_ref, 'artifact') on the actual
artifact, including artifacts reached through a different source wrapper.
False rejects with native_blast_utility_source_artifact_not_granted; True or
the existing explicit-grant/ordinary-artifact None result preserves access.
Without a bound provider, an identified utility-bundle source rejects; ordinary
sources retain their existing behavior. Never infer all auxiliary grants from
a source or request a new user approval. Keep the actual original grant owner.

ScientificProcessEpisodes.execute invokes this helper before dispatch, including
before the tool-operation replay cache. Existing structured invalid feedback
handles rejection; no new observation or credit is created. Forward explicit
context.received_record_refs to source.locate as already done for result.blast.hsp.
Do not change tool schemas, instructions or TASK/STEERING templates.

Owned files: episode_services.py, episode_bindings.py protocol,
scientific_process_episodes.py, materials.py, new tests666 and this evidence
directory. Other owners keep their utility contracts/views/publication/returns.

Meaningful checks use the real scientific binding, WorkflowServices, ToolRegistry,
Store and existing utility reference resolver with labeled controlled inputs:
source-only versus explicitly selected bundle bytes, unrelated auxiliary grant,
preexisting material wrapper, read/parse/from_source/locate, original/text and
stdout/stderr choice, denied cached operation replay, ordinary caller material
and ordinary source.locate. Denied operations must not read bytes or register a
wrapper/parse. Preserve old source-window results and selected-operation replay.

All application imports/tests run under bounded529 check127_material_access666,
explicit check005 dependencies, 20 GiB RAM / 4 GiB scratch / zero swap / no wall
cap. No native scientific invocation or acquisition. Preserve failed attempts
and report verification scope exactly. Reread the original objective and entire
OPERATING PRINCIPLES after bioinformatics/external work, then this port before
claiming this correction complete.
