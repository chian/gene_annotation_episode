# tqDist: bounded primary-method conversion

Source: Sand et al. (2014), *tqDist*, doi:10.1093/bioinformatics/btu157.
[Author-hosted complete two-page paper](https://cs.au.dk/~gerth/papers/bioinformatics14.pdf).
Inspected both pages, sections 1–4 and references. No biological assay or target
protein was studied here: the comparison is two trees with mapped common leaf
identities. Genotype, coexisting constructs and molecular-assay attribution are
not applicable to this methods definition. Tree/copy comparability remains
essential; the metric does not establish it.

The native distance counts differing induced topologies over all three-leaf
subsets for rooted trees, or four-leaf subsets for unrooted trees. In the
paper's nonbinary convention, unresolved/unresolved triplets agree;
resolved/unresolved triplets disagree. Thus raw normalized distance alone
cannot distinguish shared uncertainty from supported matching lineage splits.

Proposed A104 conversion: retain native distance and separate resolved matches,
resolved conflicts, mixed-resolution and doubly unresolved counts. For soft or
unclassified polytomies, report resolved-match/N and bounds that preserve the
unresolved slots, rather than awarding full concordance to two unresolved
trees. This conversion is ours, not the paper's proposed function score.

Full authority reset completed after this read and before conversion, including
the current numerical template and latest human A104 steering last. Receipt:
`AUTHORITY_RESET_PAPER01_001.json`. No software installed or native tree job run.
