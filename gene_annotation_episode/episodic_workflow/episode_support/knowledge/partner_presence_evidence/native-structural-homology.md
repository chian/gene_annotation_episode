# Native structural evidence for A102

Start from the supplied protein sequence or an explicitly selected file subject.
No candidate annotation is required. Identify which coordinates represent that
target. `structure.bind` requires an actual received PDB/mmCIF file, an explicit
chain and model, origin witnesses and construct qualifications. Missing and
ambiguous coordinates remain visible. Mapping a model sequence to its supplied
input is a supporting transformation, not a sequence-homology investigation.

Use `structure.discover` for a bounded explicit panel (at most 32 received
models), or `structure.align` for an explicitly selected pair. Foldseek is pinned
to global TMalign mode 1. Complete Foldseek maps and transforms are graded at
publication; a US-align follow-up is useful only if required structural cells
are missing or an explicit independent comparison is needed. Repeated identical
received US-align comparisons can be reused. Preserve native metric names,
matched extent, normalizations, maps and transform. DALI Z, TM scores and RMSD
are not interchangeable.

Every qualified native result automatically receives its grader and A102 sheet
before the tool returns. `episode.credit` only inspects it. The default native
index is B = [2 n/(L_target+L_reference)]/[1+(RMSD/2 A)^2]. The original supplied
sequence and parent scope remain the denominator. Identical model copies are
controls. Same-sequence model variants require a declared primary; an unresolved
primary is not selected by maximizing the score. Coordinate uncertainty is
retained and is not silently converted to a probability or a weight.

`structure.feature_geometry` measures a declared source-grounded required set
under the existing scaffold transform. It never refits the features. Distinct
physical requirements count once. Missing coordinates or unresolved chemistry
are unknown; established absence or incompatibility needs a witness. F is the
mean 1/(1+(distance/1 A)^2), and E = B F. These values stay separate from native
controller B. `structure.contrast` compares max supporting E with max explicitly
incompatible E in the same scope/profile. Unexamined alternatives are unknown.
A shared fold, transporter fold or complex subunit cannot establish exact
substrate specificity, physiological activity or a functional whole complex.

Attribution is specific to a produced measurement and its intended use.
`structure.align`, `structure.discover` and the existing saved CA-comparison
bridge receive direct model/construct attribution sheets. They do not require
an aggregate A101 score. Native geometry retains its original value and origin.

Use `structure.reference_align` when the measured coordinates belong to Y and
Z but the intended target X is sequence-only. Bind both reference models with
`target_ref=null`. The tool preserves the real Y/Z alignment and automatically
requests the exact missing X/Y correspondence. Receipt of an applicable native
sequence comparison triggers the attachment grader; do not call an assessment
to activate it or rerun the retained alignment. A strong hit to another protein
cannot substitute for X/Y. The qualified index uses mapped Y/Z geometry at X's
original denominator, the local X/Y identity and the selected native distance
profile. Raw Y/Z RMSD stays a measurement on Y/Z. Self controls and unresolved
primary variants cannot acquire credit through transfer.

`structure.reference_traits` evaluates reference residues, regions, motifs,
chemical-role classes and discontinuous sites at corresponding target subparts.
Supply actual definition witnesses and all required reference positions. A
specific native sequence map or target/reference structural map can establish
local correspondence. Region-query coordinates are lifted to the original
target. Native structural maps can be supplemented by existing sequence maps
at omitted sites; conflicting maps leave only the affected sites unresolved.

The trait sheet separates the raw trait match from correspondence-qualified
support. D to E can change exact identity while preserving the declared acidic
residue class. These are sequence-defined role classes, not demonstrations of
charge under particular conditions or of catalysis. Motif allowed-symbol sets
are explicit source-defined requirements. Missing positions remain in the
original denominator and keep the point value unknown with stated bounds.

Geometry traits name an actual retained feature measurement. With real target
coordinates, the grader composes existing native transforms without a site
refit and measures target geometry; amino-acid identity is not inherently a
requirement for shape. Without target geometry, transferred reference shape is
explicitly inferred. Construct changes at a required site prevent presenting
variant coordinates as directly measured target-site geometry.

Evaluated local traits emit mapped feature records and observations whose
subjects are those subparts. Distinct traits can refer to the same site; shared
dependency groups prevent treating its residues as independent votes. A whole
protein function still requires an explicit feature-to-whole interpretation.

`structure.interface_geometry` measures source-defined interchain contact
constraints only for distinct chains in the same coordinate model. Each
required component has its own local attribution. A missing partner link
leaves that interface use unresolved. Coordinate contacts alone establish
neither biological assembly, partner presence nor whole-complex activity.

Attachments are host-derived on publication and receipt, before credit is
projected. `episode.credit` reads already graded sheets. Unrelated valid native
results retain their scores when an individual attachment or trait is missing.

For an execution subtree, a `launch` child may choose the actual local binding
and commission `launch_local` with the unchanged structural job. Its
`a102.native.execute` returns a checked receiving handoff. A `results` child uses
`a102.native.collect` to deliver the requested already graded sources. Handoff
metadata alone grants no structural credit. A `monitor` can inspect selected
real job progress. All ordinary native calls and execution children share the
host admission gate: one local job and one CPU by default, with the actual
per-operation RAM/scratch limits supplied in `resource_context`. A busy outcome
preserves the prepared native handle for retry; it is not an empty comparison.

Both acquired information and missing information belong in shared-parent
communication. Publish actual evidence with `shared.publish_information` and
required facts, provenance and whether work can continue with
`shared.request_information`. The parent chooses how to satisfy a need, can
commission other axes as siblings, and explicitly delivers received evidence.
`shared.read_information` admits selected deliveries; shared metadata alone
does not admit private evidence. Page older metadata with
`shared.list_information`. Every scientific descendant of A102 remains A102.

AlphaFold DB access retrieves existing models. Novel-sequence folding is a
separate explicitly configured remote/API/HPC job. When no such resource is
bound, `structure.model_request` publishes the missing-model need to the shared
parent. External DALI execution likewise requires an explicit deployment.
Reported structural comparisons can be retained separately with
`structure.reported_comparison`; reported geometry about another subject does
not masquerade as freshly executed target evidence.
