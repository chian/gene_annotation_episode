# Three independent provider workloads

These coding boundaries consume the frozen ADDITIVE_CONTRACT.md, SHA256
`8535b1be2802406ca70d0ba402f1400f5d7b6b079e4c4c655a62e54ea78e5d7b`, accepted in
ACCEPTANCE_001.md. Original provider shapes, numerical formulas, parser types,
the taxonomy/restricted-split addendum and historical-requirements addendum all
remain applicable. This plan does not change the immutable user goal.

All files below are relative to the existing implementation staging directory:
`verification/tool_graders_bvbrc_phylogeny_implementation_2026-10-24/staging/`.
Only the named new files are owned. Root owns production installation, C4
adapters, registries, library/return wiring and the fixed checklist.

## S: Shared provider fields and common calculation dispatch

Owned files:

- gene_annotation_episode/bvbrc_phylogeny_common_inputs.py
- gene_annotation_episode/bvbrc_phylogeny_common_contracts.py
- gene_annotation_episode/bvbrc_phylogeny_common_grader.py
- tests/test_bvbrc_phylogeny_common.py

Evidence directory: provider-common-verification, adjacent to staging.

Exact public signatures:

```python
extract_common_fields(*, provider: Literal['gene_tree', 'codon_tree'],
    documents: GeneTreeExtractionDocuments | CodonTreeExtractionDocuments,
    inputs: tuple[InputBinding, ...], observed_run: ObservedRun,
    joins: GeneTreeJoins | CodonTreeJoins, assembly: ProviderAssembly,
    parameters: GeneTreeReadParameters | CodonTreeReadParameters
) -> ReadResult[CommonFields]

validate_shared_fields(sheet: dict, *,
    provider: Literal['gene_tree', 'codon_tree']) -> CommonFields

input_member_subject_id(input_binding_id: str, member_id: str) -> str

calculate_common_components(sheet: dict, *,
    provider: Literal['gene_tree', 'codon_tree'],
    parameters: CommonCalculationParameters) -> CommonComponents
```

`extract_common_fields` and `input_member_subject_id` are exported from
common_inputs; `validate_shared_fields` from common_contracts;
`calculate_common_components` from common_grader. Any private helpers stay in
these owned files. No placeholder function or parallel duplicate validator in
the provider workloads.

CommonFields is a closed object with exactly these fields and their accepted
provider-sheet types:

```text
inputs, artifact_refs, observed_run, documents, joins, populations,
native_measurements, support_observations, dependence_groups,
qualifications, missing_requirements, assembly, read_outcomes
```

CommonCalculationParameters has exactly the seven common parameter fields:

```text
alignment_requests, original_coverage_population_ids, tree_requests,
bootstrap_requests, composition_population_ids, taxon_requests, comparisons
```

CommonComponents has exactly the ten common component fields:

```text
alignments, trees, bootstrap, coordinate_maps, original_coverage,
composition, taxonomy, comparisons, missing_requirements, diagnostics
```

This workload validates complete common input shapes and relationships, then
populates the common fields. It retains all original ReaderInput statuses and
diagnostics, validates equal duplicated parsed values, and constructs whole
alignment/tree populations with the exact accepted IDs. It validates actual
input/member/source/row/tip identities and explicitly supplied function/taxon,
transformation, residue, display and organismal joins. No label-order joins,
guessed sequence lengths, database lookup or absent metadata inference.

It flattens actual reader observations/commands into their saved registries,
preserving original requested/observed/source_expected distinctions and setting
conflicts. It constructs native count-only populations without pretending their
empty member arrays are a known empty biological population. It extracts
branch lengths and all evidenced support locations from the declared tree
representations, retaining raw zero/negative/failed tokens, unknown units and
methods, and GeneTree XML converter qualifications. Exact actual run/format
evidence is required for named units/support methods. The complete frozen
source findings and original provider proposal specify those distinctions.

Shared dependence includes exact duplicate final sequences, explicitly shared
original members, and supplied derived/source relationships. Protein/CDS family
dependence is added by the Codon provider. Common population validation checks
closed shapes and references into documents/inputs/source records. Provider-only
family/genome stage and matrix relationships are checked by the Codon provider;
locus-specific inclusion is checked by the Gene provider. Neither validation
step claims to authenticate Store custody; that remains the actual C4 host.

`validate_shared_fields` accepts only the exact complete saved provider-sheet
top-level key set and matching header for the selected provider, validates its
common portion, and returns a detached CommonFields projection. Provider-only
arrays must have their declared array types; their full semantics remain with
their provider validator. This function must not claim to validate the entire
provider sheet. A provider validator calls it before validating its own fields.

Common calculation dispatch invokes the eight installed shared calculators
with their exact declared operands. Validate all source/assignment identities
before filtering assignments for one selected population. Build original member
coverage inputs from actual InputBinding members, InputRowJoin and verified
transformations, retaining unknown lengths/maps and exact original units.
Coordinate width, strand, translation and before/after digest relationships
must be checked, not inferred from similarity. Tree/replicate/comparison joins
retain explicit populations and restricted split definitions. Merge finite
requirements without calling one helper on another family's reason vocabulary.
No parsing, I/O, executable, model, resource choice or score aggregation occurs.

Malformed structural/identity operands raise stable-code ValueError in saved
validation/calculation. Extraction returns the exact ReadResult; independent
partial artifacts remain usable under their true limitations. Do not turn
missing ordinary scientific metadata into a blanket invalid sheet. A complete
valid topology may coexist with unavailable alignment quantities.

Verify duplicate native labels with distinct qualified members, wrong source
anchors, two files containing member 'q', malformed independent matrix plus
valid tree, negative branches, generic/zero XML support, missing observed
settings, contradictory run evidence, unavailable original coverage, different
function/taxon denominators, retained native examples, and JSON recalculation
with I/O disabled. Verify exported signatures and closed exact returned keys.

## G: GeneTree sheet and grader

Owned new files: gene_annotation_episode/bvbrc_gene_tree_inputs.py,
gene_annotation_episode/bvbrc_gene_tree_grader.py,
tests/test_bvbrc_gene_tree_provider.py. Evidence: gene-provider-verification.

Implement the accepted exact `extract_gene_tree_sheet` signature, plus
`validate_gene_tree_sheet(sheet: dict) -> dict` in inputs and
`calculate_gene_tree(sheet: dict, parameters: dict) -> dict` in grader.

Extraction calls S.extract_common_fields with provider='gene_tree'. It adds the
fixed schema/tool/mode header and exact Locus[] table. Loci come from supplied
LocusBinding, real input/member relationships, primary analysis.locus_ids and
actual stage/transform evidence. No basename or all-gap inference of removal.
Preserve individual and concatenated modes. Enforce exactly one explicit primary
analysis per invocation while retaining all its associated documents and
auxiliary comparison trees. C4 later calls this for every selected analysis.

Validation calls S.validate_shared_fields and then checks the exact GeneTree
fields/locus references, stages and inclusion relationships. Grading validates
the full saved sheet, projects the seven exact common parameter fields, calls
S.calculate_common_components and returns the frozen GeneTreeComponents with
its complete original calculation parameters. No numerical formula duplication.

Verify ordinary and concatenated loci, duplicate headers, supplied sequence
segments, J-to-X/trim/gap-fill transformations, null alignment with usable tree,
unknown observed engine despite requested recipe, converter-inserted XML zeros,
full exact input/output shapes, wrong references and retained two native XML
examples. Do not seed external source records or claim original task custody.
Offline replay must use the saved sheet/parameters without new acquisition.

## C: CodonTree sheet and grader

Owned new files: gene_annotation_episode/bvbrc_codon_tree_inputs.py,
gene_annotation_episode/bvbrc_codon_tree_grader.py,
tests/test_bvbrc_codon_tree_provider.py. Evidence: codon-provider-verification.

Implement the accepted exact `extract_codon_tree_sheet` signature, plus
`validate_codon_tree_sheet(sheet: dict) -> dict` in inputs and
`calculate_codon_tree(sheet: dict, parameters: dict) -> dict` in grader.

Extraction calls S.extract_common_fields with provider='codon_tree' and adds the
fixed header plus Genome[], Family[] and PartitionModel[] tables. Construct them
from the exact accepted requested/group sets, explicit family matrices, retained
membership/statistics/counts, FeatureGenomeJoin, FamilyBlock and ModelAssociation
records. Preserve requested-only genomes, deleted paralogs, missing CDS,
pre-trim versus final state, missing namespace, the native report CDS-count bug,
and separate protein/CDS representations without duplicate biological votes.
No requested-main denominator from a feature union, no final family coordinates
from the four global partitions, and no model sampling map from a random seed.

Validation checks these provider fields after shared validation, including
original matrix/population completeness and actual table/model/source indices.
Grading calls the common dispatcher, then the three existing pure functions in
bvbrc_codon_tree_calculators using exactly the requested populations and saved
HistoricalFrequencyInput. Merge their finite requirements through their own
helper. Preserve the accepted empty/unknown historical-population distinction.
Return the full frozen CodonTreeComponents; do not add a confidence score or
apply the source's family selection thresholds as runtime rules.

Verify actual retained historical membership and nine-row final alignment,
source-derived current table syntax separately, group/main/optional differences,
partial matrices, duplicated features, missing family/genome associations,
protein/CDS dependence, exact partition/model joins, null alignment plus valid
membership/tree, pre-trim/final mismatches, original-coordinate absence, numerical
hand cases and saved-sheet replay. No live job or original-task custody claim.

## Parallel handoffs and closure

G and C can write their provider-specific builders, contracts, fixtures and
tests immediately against S's exact interface. They do not need S's final code
to define their own fields, but complete integration tests must use the actual
S implementation. No fake shared implementation may establish a passing path.
S tests can use full hand-constructed provider-sheet objects with actual shapes;
they need no G/C function implementation to check common arithmetic.

Providers must report a concrete missing interface instead of changing another
workload's code or silently adding a field. Root resolves it additively. Every
workload reads the immutable objective/design-principle block verbatim after
substantial source/native study and before final handoff, then its exact contract.
Keep complete source/native/synthetic/replay distinctions and file hashes.

These pure-provider workloads do not implement C4 dispatch, externally supplied
raw-byte custody, launch/monitor/results library entries, parent projections or
episode integration. Those retained root tasks follow these exact produced
sheets/components. No literature, W05, annotation scoring, root scientific tool,
method_loop, credit, continuation or goal-scope edit is authorized here.
