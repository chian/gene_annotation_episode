# Selected scientific images and reasoned visual observations

An Episode can select the ordinary tool `image.view` with a registered
`source_ref`, optional zero-based `frame` (default0), and optional
`colour_conversion` (`preserve`, default; or explicit `rgb`). This is one own
action. It does not choose another frame, apply a scientific interpretation or
assign an annotation. Original source bytes remain immutable.

The adapter uses Pillow to decode the selected frame and retain a PNG display
artifact. Pixel axes are stored axes: there is no automatic EXIF rotation,
resizing or contrast adjustment. Preserve mode verifies the actual native PNG
round trip; an unrepresentable source receives representation feedback instead
of silently clamping pixels. An explicit RGB conversion is recorded and can
lose information. Native format/mode, selected frame/count, saved mode,
dimensions, transformation and software version accompany the actual artifacts.

`image_view` is a tool-authored typed provenance record, separate from a
biological subject or observation. Its display source points to the actual PNG;
input source and original/display artifact references preserve custody. Sources
have optional typed `parent_source_refs`, so a selected PDF page or repeated
view retains forward lineage through actual earlier sources. Exact semantic
records and raw artifacts remain available on disk. The same registered byte
artifact can retain an earlier opaque MIME label: actual decoding establishes
PNG representation, without rewriting first-capture metadata.

Only the completed `image.view` adapter publishes the host wrapper
`visual_inputs`. The next decision receives that same id-bearing view in
`visual_evidence`; its ID is included in the actual report interpretation basis.
An artifact resolver verifies the recorded selection and content hash, then
supplies a native Codex `localImage` input alongside the normal text context.
No arbitrary model path, nested provider JSON or child report selects an
attachment. The existing decision call performs the interpretation; there is
no second model, summary composer or native model-side tool call.

The existing request journal records exact text/image inputs before dispatch.
Recovery reloads the already-completed selection from disk and resolves that
same artifact, without acquiring/rendering again or creating another own-action
observation. After another selected operation, no earlier image is automatically
attached to subsequent decisions. Native active conversations retain their
normal conversation history; closed Episode provider workers are released as
before. A deliberate new image.view is available when earlier pixels matter.

For an actual visual interpretation, the model can submit an observation with:

```json
{"source_ref":"source_<the actual display source>","anchor":null,
 "visual_anchor":{"view_ref":"image_view_<the actual view>",
                  "image_artifact_ref":"artifact_<the actual PNG>",
                  "region":{"x":0,"y":0,"width":400,"height":300}}}
```

These example IDs are placeholders; ordinary forms require actual registered
references. Region coordinates are native selected-PNG pixels, top-left origin,
half-open `[x,x+width) × [y,y+height)`. The Store verifies view/source/PNG
relationships and geometric bounds. It marks a model visual observation as
`origin=reasoning`, preserving its difference from a literal quote extraction or
a native assay measurement. Source subjects still identify the actual assayed
construct/sample; conditions and source names can be anchored to actual article
text. A picture of a reference protein does not become an experiment on a
submitted target. No judgment of biological quality is enforced by the adapter.

The existing assessment applicability, extent and softened-hypervolume
projection remain unchanged. Viewing or recording an interpretation alone does
not create annotation credit. A recorded visual interpretation can support or
weaken a subsequent current annotation through that existing projection.
Text observations still require exact literal byte anchors. Invalid independent
visual rows receive precise feedback without erasing valid other contributions.

The Codex binding was checked against installed cli0.163.0 generated
`v2/TurnStartParams.json` and the official
[app-server documentation](https://learn.chatgpt.com/docs/app-server).
One actual gpt-6-sol/medium call identified a synthetic red triangle and blue
circle supplied as pixels; its request/events/response are retained in
`validation/staging/image_evidence_next/validation/calibration/native-image-transport/`.
This establishes selected-image transport, not biological accuracy, end-to-end
annotation, useful child iteration or scientific completion.
