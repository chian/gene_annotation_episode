# A101/A102 root mock and tool-specific attribution

The experimental entry point `evidence_root.create_evidence_root_workflow`
composes the existing A101 and A102 numerical projectors. The published axis
instructions, native graders and individual axis scores remain unchanged.
Other entry points retain their existing policies.

The root recomputes from its own received records. It never adds child-return
scalars. For each supplied target, its explicit progress convention is
`H = product(1 + axis_credit) - 1`. With the first two axes this is
`A101 + A102 + A101*A102`, on a 0–3 scale. An empty future dimension is neutral;
changing the number of axes does not renormalise existing credit. Missing
native evidence earns zero while its unmeasured status remains explicit.
Compute the product per target before averaging by original assigned lengths,
so evidence for different proteins cannot create an interaction.

Every product term is exposed. Its equal division between its participating
axes is an accounting allocation of the existing total, not additional credit.
The interaction is an experimental progress convention, not an independence
claim or a probability of exact function.

`examples/a101_a102_root_mock.py` runs retained real LacY or AtpG inputs using
actual phmmer and US-align, native graders, receipts and shared host admission.
It uses scripted choices and finite engineering horizons, not fresh model
decisions or a claim about optimal stopping. A102 first publishes a need, the
root commissions an A101 sibling, resolves the need from actual received hits,
and commissions an A102 follow-up with the selected structural model and seed
provenance. The first request and later comparison are separate A102
commissions; another axis is never nested beneath A102. The parent has a small
explicit retained model inventory, not an all-database structure search.

Run it with `--case lacy` or `--case atpg`, `--run-directory runs/<run>/<case>`,
and `--usalign <pinned-executable>`. Set bytecode, temporary and cache paths
under that run, along with `GENE_EPISODE_LOCAL_RESOURCE_DIRECTORY` for its
shared host pool. Retained native tools can be installed with the A102 setup
helper. Runtime traces and results belong under `runs/`.

## A103 sibling

The root now also binds A103 gene-context credit. Its context measurements,
per-component and per-region attachments, native jobs and shared-parent needs
are described in [A103_IMPLEMENTATION.md](A103_IMPLEMENTATION.md). The same
offset-product formula applies; a missing A103 result leaves existing earned
credit intact. A105 remains independently implemented and is not reimplemented
by this mock-up.

## Implemented applicability of individual measurements and local traits

The tool-specific attachment layer is implemented. The root's offset-product
formula remains unchanged. Applicability belongs to a particular measurement
and its intended use for a target. An axis-wide A101/A102 multiplier does not
express these requirements. Pair-map agreement remains a useful join
diagnostic; it does not measure sequence divergence or establish that an
observed reference property transfers to the target.

For target X, a comparison measured on Y and Z remains a result about Y and Z.
Using it for X requires the particular X-to-measured-subject link appropriate
to that use. A comparison measured directly on an authenticated X model has a
different attachment contract. Actual operand identities and custody establish
that distinction; a model-authored `direct` flag cannot bypass it.

| Measurement and intended use | Required attachment |
|---|---|
| Structural alignment of an authenticated X model to Z, used to describe their measured fold resemblance | Target/model/construct binding and the native structural correspondence itself. A sequence-homology score is not a prerequisite for this direct structural result. Preserve model origin and uncertainty. |
| Structural similarity or constraint measured on Y and Z, then used for sequence-only target X | An explicit, source-bound X-to-Y attribution path over the relevant domain or region: its actual sequence or other appropriate distance, coverage and correspondence map. Authenticate which sequence/construct supplied Y's coordinates. |
| Pocket, catalytic-residue or ligand-contact property observed on Y, used for a corresponding property of X | The source observation on the actual Y construct, the local X-to-Y residue map and differences, required physical-feature definitions and any target geometry needed by the claim. A whole-protein similarity score cannot replace these local operands. |
| An interface or assembly constraint from a reference complex, used for X and a proposed partner | Correspondence for each participating component and interface region, plus the relevant assembly/state provenance. Claims about partner presence require their own received evidence. |
| An A101 hit used to choose an A102 search or comparator | A recorded parent delivery and actual consumption as a seed. This is useful coordination lineage; it does not itself justify transferring a structural property. |

The attachment policy is selected by **operation, measurement/output type,
actual measured subjects, intended claim and required scope**. Different uses
of the same primitive tool can require different policies. Each policy names
the permitted metric schema, source/version, numerical convention and exact
joins. A tool name or an axis label alone cannot select a transfer rule.

The implementation:

1. Binds actual measured subjects separately from the target to which a result
   is being attributed. Retains native results, model/construct identities,
   coordinate/sequence hashes and region/site identities before interpreting
   them for the target. A homolog model stays a homolog model even when its
   sequence is close to the target.
2. Defines versioned attachment contracts by tool and result/use.
   Each required link names its two subjects, scope, metric, map and original
   evidence references. An A101 dependency means the specific received X/Y
   comparison, not the aggregate A101 score or an arbitrary strong hit.
   Missing inputs become parent-visible needs; the parent commissions any
   external evidence axis as a sibling.
3. Attaches the corresponding deterministic applicability grader on native
   publication or receipt of a required missing operand. Emits a sheet for the
   particular measurement/use with raw distances and units, coverage,
   correspondence, qualifications, missing inputs and the versioned result of
   the selected transfer rule. Reuses existing maps and grades. An unknown link
   leaves that use unresolved while unrelated valid results retain credit.
4. Keeps raw physical measurements unchanged. Where a declared bounded-index
   profile permits it, derive a separate target-attributed score from the raw
   result and its required attachment. For example, transferring a Y/Z fold
   result may use the pair-specific X/Y native correspondence on its declared
   domain; a pocket-specific claim instead requires its source-grounded local
   feature checks. There is no universal distance-to-applicability kernel or
   automatic multiplication of raw RMSD values by similarity weights.
5. Aggregates qualified contributions at their original scopes in the owning
   axis, then passes those axis components to the root's offset product. There
   is no additional whole-A102 attachment gate. Retains upstream attribution
   and shared provenance without counting a reused bridge as fresh independent
   evidence or rewriting closed child histories.
6. Evaluates local trait predicates separately from entity correspondence.
   Residue identity, chemical-role conservation, motifs, regions and geometry
   have different checks. Discontinuous target features and local observations
   retain their exact footprints. Target geometry can use composed native
   transforms without a new fit; reference-only shape stays explicitly
   inferred. A local trait never becomes an automatic whole-protein function.

The supported tools are `structure.bind`, direct `structure.align` and
`structure.discover`, saved CA comparisons, `structure.reference_align`,
`structure.reference_traits`, `structure.feature_geometry`,
`structure.interface_geometry`, `structure.reported_comparison` and
`structure.contrast`. Inspection reuses existing evidence; missing-model
requests are coordination records. There is no axis-wide attachment scalar.

The reference-fold convention maps retained Y/Z geometry through the specific
X/Y comparison and evaluates it at X's original receiving scope. Its geometric
extent is applied once, then local residue identity and the native strength of
that particular comparison qualify the inferred correspondence. Statistical
sequence searches use their existing bit kernel. A retained protein pairwise
alignment can instead supply identity-distance correspondence without an
invented bit statistic. These are versioned indices, not function probabilities.

Local sheets distinguish `trait_match` from correspondence-qualified `score`.
They include required positions, local distance, scope, evidence references,
missing cells and bounds. One D/E substitution can change exact identity while
preserving the requested acidic role. Source-defined motif symbol sets and
geometric constraints have their own evaluations. Missing or conflicting sites
do not disable other valid traits or native fold results. Profile columns
require an actual protein-residue map before they can justify residue transfer.

`examples/tool_attribution_investigation.py` runs a sequence-only LacY target
against measured reference/reference geometry, then receives a real native
A101 result through the shared root. Grading updates at receipt without another
structural alignment. The local property definitions are engineering probes;
they do not assert characterized catalytic sites. The ordinary direct-target
mock remains a separate control. Raw traces and outcomes stay under `runs/`.
