# W04 prompt content handoff — 2026-10-24

This workload wrote only the ten new `A*.json` entries in
`research/slotted_process_library/publications/2026-10-24-001/entries/` and this
note. It implements investigation prompt text only. The numerical scoring
sheet, the readers that populate that sheet, and W05 credit integration remain
separate work. No historical entry, scoring proposal, source index, production
Python module or scientific run was changed by this workload.

The retained entries are A101–A108, A110 and A111. A109 has no entry. The names
and all 268 instruction-provenance rows were copied unchanged as JSON values
from the matching entries in publication `2026-10-23-002`. Every new entry has
exactly `entry_version`, `id`, `slot`, `name`, `description`,
`investigation_instructions` and `evidence`. The version is
`evidence_axis_instruction_v1`; the slot is `evidence_axis`. Each provenance row
retains exactly `case_group`, `case_id`, `source_url`, `source_locator`,
`observation` and `limit`.

All ten TASK texts were sent to the parent in small batches for inline display.
The implementation remains reviewable; this note does not claim user approval
of unseen prose. The parent requested two wording refinements before writing:
A104 now says that placement in a mixed-function clade **alone** cannot identify
a narrow function, and A110 explicitly examines the other genes or enzymes that
supply substrates, consume products, regenerate cofactors or provide other steps
needed by a proposed chemical route. The final A110 text was sent again with
that paragraph included.

## Controlling requirements, separate from published observations

The complete instructions read for this workload were the local `PLAN.md`, root
`AGENTS.md`, `GOAL.md`, `docs/EPISODE_STRUCTURE.md`,
`docs/TIME_AWARE_ESTIMATION.md`, `docs/TASK_AND_STEERING.md`, and
`docs/AMENDMENTS/EVIDENCE_AXIS_LIBRARY_INSTRUCTIONS_2026-10-23_001.md`.
The old entries' scientific measurements, limits, criteria and provenance were
examined for useful investigation guidance. Their rejected scoring rubrics and
qualitative grades were not copied into the new schema or TASK text. No new
primary-paper reading or scientific calculation was needed for this task.

The following are user requirements, not findings inferred from the retained
papers:

- All axes can begin with supplied sequence, selected file contents or snippets.
  No candidate annotation or publicly searchable name is a prerequisite.
  Partial material stays partial; possible functions emerge during investigation.
- The prompt is the detailed recurring TASK. Scoring sheets and their targeted
  readers are separate responsibilities. No total-confidence grade, scoring
  formula, reader binding, tool inventory, prescribed itinerary, new episode or
  continuation rule was added here.
- A105 concerns measured molecular activity; A106 concerns contribution shown
  through perturbation and restoration. A107 concerns required partners and
  their presence/coexpression. A108 concerns organism/sample plausibility. A110
  retains the chemical and pathway account, including evidence for other needed
  enzymes, separately from A108. A111 uses experimental structural observations
  through sequence **or** structural correspondence.
- The current content handoff quotes the latest A104 direction verbatim:
  “A104 works if the phylogeny of the proposed protein family matches the
  reference evolutionary tree and if it sits within a clade of only that
  function”. The same handoff supplies the conserved-function/organismal-tree
  requirement, limits under frequent horizontal transfer in viral/mobile
  families, possible usefulness of very-local near-relative trees,
  mixed-function limits in rapidly refunctionalizing families such as ion
  transporters, and the very small functional information from an outlier alone.
  These are controlling investigation requirements. The retained source rows do
  not claim to demonstrate all of them.

A105's first three paragraphs are extracted verbatim from the section “Revised
text inserted into TASK” in
`verification/a105_three_parts_review_2026-10-23_001/prompt_insert_003.md`.
One paragraph is appended to express the later non-sequence-only transfer
clarification and distinguish molecular activity from perturbation outputs.
No words were changed in the preserved three paragraphs.

## Source-to-instruction trace

Rows below are zero-based `evidence` indices in the matching historical entry
under `research/slotted_process_library/publications/2026-10-23-002/entries/`.
The complete exact source locators, URLs and inspection limits remain in both
the old and new provenance rows. These observations informed instructions;
they are not evidence about the target of a future child, a complete source
review, numerical scores, or general laws established by the listed papers.

| Axis and retained provenance examples | Published observations in those rows | Resulting instruction and limit |
| --- | --- | --- |
| A101, rows 5, 10, 11: HisN/IMPase, TriA/AtzA, YadB | The HisN comparison contains a missing motif and failed complementation despite greater global similarity; TriA/AtzA differ at nine of 475 residues while acting on distinct substrates; YadB lacks the anticodon-binding architecture of GluRS. | Examine function-relevant residues and domain organization alongside the actual alignment. Overall similarity does not settle exact substrate or role. The sequence comparison and source assay remain separate facts. |
| A102, rows 0, 8, 10: Arad3529, MJ0577, EnvC | Arad3529's conserved catalytic residues coexist with altered substrate-contact loops; MJ0577 DALI matches were functionally uninformative; EnvC resembles active LytM but lacks its catalytic zinc machinery. | Preserve the native structural comparison and inspect machinery relevant to a possible function. A fold match or prediction confidence alone does not establish activity. |
| A103, rows 1, 4: BioY, MJ0044 | BioY's genomic relationship with BioMN is nonuniversal, and assay endpoints distinguish transport properties; MJ0044 homologs cluster with pathway genes in some archaea while the target organism lacks that neighborhood. | Preserve actual locus identity, informative alternatives and optional modules. Context can motivate a role without proving exact chemistry or universal partner necessity. |
| A104, rows 0, 1: YjeH, OarX | The YjeH work reports placement in an amino-acid-efflux branch; OarX occupies a clade separate from canonical FabG, with further contextual and negative experimental findings. | Retain actual tree placement and characterization separately. The stronger organismal-congruence, function-conserved-clade, horizontal-transfer, mixed-function and outlier instructions come from the user's current direction, not an invented result of these rows. |
| A105, rows 19, 52, 69: BioC, QueF, YadB | BioC substrate concentrations and activities differ; QueF's product matches authentic preQ1 by HPLC and NMR; both tRNA substrates bind YadB but only the queuosine-containing substrate is glutamylated. | Preserve substrate, concentration, product authentication and endpoint meaning. Binding and conversion are distinct. These examples support the unchanged corrected A105 prompt; they do not replace it with a new scoring proposal. |
| A106, rows 3, 62, 74: EnvC, BioK, HisN | Stable/localized EnvC variants can lose activation and cell-separation outputs; BioK rescue depends on induction and other conditions while insolubility prevents purified assays; a HisN paralog's overexpression rescue does not explain residual native growth. | Examine selective contribution, restoration conditions, expression/stability alternatives and bypass or redundancy. Restoration does not by itself establish the chemical route, and failed complementation is not a purified-enzyme negative. |
| A107, rows 0, 3, 5: Cdv, YneA, Huc | Cell-cycle induction accompanies Cdv division-associated structures; an induced YneA operon contains components that do not independently reproduce YneA's phenotype; Huc/Hhy expression and activity differ by growth phase. | Preserve matched expression conditions and distinguish association from component requirements. These expression/perturbation observations do not prove that every associated gene is an indispensable partner; the required-partner question is the user's axis definition. |
| A108, rows 0, 5, 10: PibD/FlaK access, HpnN, relocated TrxA | Accessibility measurements have membrane, burial and labeling limits; HpnN deletion changes lipid localization with temperature-specific phenotypes; export-related TrxA observations are informative while fractionation alone is inconclusive. | Distinguish observed access and condition-specific setting from prediction or a plausible story. A compatible cellular setting does not establish chemical activity. Transfer retains the assayed organism and membrane-context limits. |
| A110, rows 1, 3, 10, 11: Bcd/Etf, F420 precursor, BioZ, ThyX | A fully coupled Bcd/Etf ratio is extrapolated from measured ratios; F420 maturation requires a reduction/regeneration account that limits broad extrapolation; CaiB experiments address BioZ substrate supply; ThyA plus FolA differs from ThyA-only rescue. | Preserve measured versus extrapolated stoichiometry, carrier regeneration and evidence for other necessary pathway steps. The added paragraph carries the user's request to examine supporting enzyme identities and measurements, without creating a mandatory gene checklist or merging A107. |
| A111, rows 3, 4, 7: TT1927b, Cas1/Cas2, FrsA | TT1927b has a modeled isoprenoid assignment with MS support at a bounded chemical level; Cas2 contact-site variants differ in functional outcome; FrsA ligand identity remains unresolved despite a modeled fit. | Preserve experimental constraints, ligand ambiguity and the distinction between contact geometry and functional necessity. Sequence or structural correspondence maps a source feature to the target; a modeled contact does not become a second independent experiment. |

Native alignment, structural, genomic, tree, expression, assay, perturbation and
chemical measurements keep their actual units, denominators and uncertainty in
the investigation guidance. This is not a definition of numerical scoring cells
or their aggregation. Provenance that appears under multiple axes remains the
same historical experiment or observation, not independent replication.
Historical labels such as A109 inside an unchanged provenance limit remain
historical text; they create neither a new option nor model-facing TASK content.

## Checks actually run

Using `.venv/bin/python`, a local check loaded the ten new and ten historical
entries and established:

- The retained ID set is exactly A101–A108, A110 and A111; there is no A109 entry.
- Every entry and provenance row has the agreed exact field set and version.
- Every name and every one of the 268 provenance rows is equal to its historical
  source value, including row order, observation text and limits.
- Every TASK starts from supplied material without requiring a candidate; the
  full corrected A105 insert is an exact prefix followed only by its addition.
- All ten entries pass the new `validate_instruction_entry` function, and its
  validated records are detached from their inputs.
- All ten `instruction_view` outputs contain exactly ID, name, publication
  status and unchanged investigation instructions; source provenance and old
  scoring/grade fields do not appear in that view.

The initial wording-presence assertion looked only for “is required” and failed
on A105's intentionally preserved “is not required”. The check was corrected
to recognize the preserved wording; A105 itself was not changed. The complete
corrected check passed. This was a verification-script issue, not a scientific
or entry-schema failure.

The content worker did not run the catalog freeze/reopen, provider turns or
actual child construction. Those are parent/implementation-worker integration
checks under the shared plan. No configured model call, live scientific
investigation, new paper retrieval, numerical sheet population or reader test
was performed by this workload.

## Remaining concerns and boundaries

No content-schema problem remains in this workload's checks. Scientific wording
still admits running user correction; passing validation does not establish
approval of every phrase. The user-defined A104 restrictions and the later A110
pathway-enzyme requirement must stay visible when the full recurring TASK is
rendered. The renderer must preserve the entire A105 insert and all other
selected instructions at initial decision, update, lookup and reconstruction.
That behavior is not proved by content validation alone.

The inherited provenance contains its original partial-reading, composite-case,
heterologous-system and other limits. It was copied without upgrading those
limits or claiming new verification. In particular, the retained A104 and A107
examples illustrate narrower observations than every rule in their TASK texts;
the additional boundaries are explicitly user requirements above. No universal
functional-transfer thresholds, total-confidence grades, scoring components,
reader implementation or W05 credit behavior follow from publishing these
instructions. Full W04 remains separate from completion of its prompt part.

Final description adjustment: at the parent’s request, A107, A108 and A110 use
“Evidence that…”, “Compatibility of…” and “Chemical and pathway consistency…”
discovery descriptions. Their existing new descriptions already used
“Investigate…” rather than the historical “Score…” wording. Only the three
new descriptions changed; names, TASK text and provenance did not. All ten final
entries were revalidated after this adjustment. Entry bytes are ready for
publication assembly.
