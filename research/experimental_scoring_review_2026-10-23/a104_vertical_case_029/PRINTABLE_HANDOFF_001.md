# Printable A104 biological example

Song et al., *BMC Biology* (2005), [DOI 10.1186/1741-7007-3-13](https://doi.org/10.1186/1741-7007-3-13), Figure 2 and Table 4:

| Actual source component | Result | Limit |
|---|---|---|
| Displayed Pseudomonas/Azotobacter TyrA members | 5 | Selected published subtree, not every natural member |
| Members explicitly assigned experimental NAD+/PPA+AGN activity in Table 4 | 2 | Author-reported P. aeruginosa and P. stutzeri; original assay identities not rechecked |
| Source-listed characterization coverage | **2/5 = 0.4** | Coverage, not purity or annotation probability |
| Published tree bootstrap resamples | 1,000 | Gene-tree support; not organismal-tree agreement |
| Organismal comparison | 16S rRNA grouping context | Exact branching-order correspondence is not required by the authors; F is unavailable |
| Query placement and outlier distances | Unavailable | No query/placement calculation or branch digitization |

The two reported references have a conserved two-substrate profile. Three other
displayed members remain unverified, and Table S1 contains an unresolved Avin
protein-identifier discrepancy. Thus strict canonical C_f, F, J and O cannot
yet be populated. This is a bounded positive function-conservation example,
not a complete measured A104 score. The source ratio cannot be silently
substituted for the missing factors in `C_f × Σ wFJO`.

Complete source-to-cell conversion, experiment definitions and inspected-source
limits are in SOURCE_TO_CELLS_001.md. The full authority reset and arithmetic are
recorded separately. No scientific tool or annotation job ran; no scorer changed.
