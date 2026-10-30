# A103 source packet 02 — RibK, research draft

Source: [Mashhadi et al., 2008](https://pmc.ncbi.nlm.nih.gov/articles/PMC2293203/), DOI 10.1128/JB.01900-07. Corpus seed: `context_ribk_mj0056_2008`.

## Inspected source measurements and definitions

The complete short article, including the interleaved experimental methods/results and addendum, was read. The context paragraph explicitly lists nine genomes with RibK homologs next to ribB: *Archaeoglobus fulgidus* DSM 4304; *Haloarcula marismortui* ATCC 43049; *Halobacterium* NRC-1; *Methanothermobacter thermautotrophicus* Delta H; *Methanococcus maripaludis* S2; *Methanococcoides burtonii* DSM 6242; *Methanosarcina acetivorans* C2A; *M. mazei* Go1; *Methanopyrus kandleri* AV19. Coordinates, orientation, search scores, complete cohort denominator and negative neighborhoods are not supplied there.

The actual protein was MJ0056 from *Methanocaldococcus jannaschii*, expressed in *E. coli* BL21-CodonPlus(DE3)-RIL and purified for assays. Extract FMN was compared with expression of unrelated enzymes, not with a matched ribK deletion. Endogenous host enzymes remain background contributors. Purified-protein assays measured conversion to FMN and donor preference; these are distinct from gene colocation. The context comparison is among natural genomes, not a protein replacement or coexistence experiment. No wild-type/mutant expression ratio belongs in its A103 cells.

## Conversion into the numerical sheet — proposed analysis

The inspectable list provides `positive_named_genomes = 9`. It also provides `listed_genomes = 9`, so the descriptive fraction **within the selected positive examples** is 9/9 = 1. It does **not** provide an unbiased 100% adjacency rate over archaeal genomes. That selection matters more than the apparent perfect ratio. The full search denominator, eligible genomes with readable neighborhoods, and observed nonadjacent loci remain unknown. The sheet must preserve both the numerical count and this selection boundary.

For a gene-context annotation coordinate, the supported scope is association with a riboflavin-related genomic neighborhood. Context alone does not distinguish kinase activity from another role in the same pathway, and does not distinguish CTP from ATP as donor. The assays must not be multiplied into A103 as a second independent context score. A later candidate with an exact reaction can receive context support for its pathway facet only, with its unmeasured reaction specificity explicit.

The paper's selected list can populate nine observation rows with `spatial_endpoint = reported_next_to`, `spatial_value = 1`, but `distance_bp`, `orientation`, homolog-identification score and assembly version all null. These are nine source assertions, not nine independent evidence units: related genomes and shared ancestral arrangements can be dependent. Without a full cohort and null model their contribution to calibrated general association remains [0,1], with point value unknown. A numerical count is useful even where the annotation coordinate is bounded.

Comparability concerns the same search sensitivity, assembly readability and endpoint definition for positive and background genomes. Isolation concerns whether this arrangement predicts the scoped riboflavin association rather than generic adjacency. The missing matched background and selection denominator must not be replaced by publication reputation or one intuitive relevance grade.

Complementary work that fills the gap: enumerate every eligible genome and all qualifying RibK/RibB homolog pairs, record distance/orientation using one stated rule, retain nonadjacent pairs, and estimate matched background. A current channel-specific context score is a separate, dated dataset measurement; it cannot be reported as the paper's 2008 score or as experimental reaction validation.

## Retrieval and reset provenance

- Web PMC article rendering initially returned a browser challenge; direct public PMC `?pdf=1` returned full HTML. `ribk_primary.html` and `ribk_primary_body.txt` retain the inspected source. Europe PMC fullTextXML returned HTTP 500; publisher/browser alternatives did not provide a usable complete body. No inaccessible content is claimed read.
- The retained corpus packet was inspected in the same paper-specific read.
- A complete authority reset was performed after that inspection and before this interpretation: root `AGENTS.md`/`GOAL.md`, episode/time-estimation/tool-knowledge/task-steering documents, task-steering/evidence-review amendments, both verbatim publication records, full corrected evidence-axis-library amendment, numerical review002, research `AGENTS.md`, active goal attachment, and latest human goal reminder last.
- No assay, homology search, neighborhood reconstruction, production reader or scientific episode was run for this paper packet.
