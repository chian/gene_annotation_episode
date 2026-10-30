# A108 organism/context result for parent review

The proposed extension answers organism plausibility through **specific
cellular/ecological requirements**, including a useful function that operates
only rarely. It distinguishes whether a compatible organism situation exists
from the fraction of sample opportunities in that situation. These are two
explicit meanings within A108; they are not two independent credit terms.

For each biologically permitted state s, the existing sheet already computes
joint compatibility from its necessary conditions:

    L_s = product_j lower_sj
    U_s = product_j upper_sj

The added organism-capability component is:

    O− = 1 − product_s(1 − L_s)
    O+ = 1 − product_s(1 − U_s)

That means **at least one compatible contextual opportunity exists**. Include
an unresolved remainder for permitted states that have not been examined.
The product is Boolean OR written arithmetically, not an independence model.
One witnessed compatible opportunity gives O=1; a finite negative sample alone
leaves O=[0,1]. A necessary constraint excluding the whole scope can give O=0.

The existing sample branch remains:

    C− = sum_i(w_i * L_i) / sum_i(w_i)
    C+ = sum_i(w_i * U_i) / sum_i(w_i)

Organism predicates enter the same paired rows as local exposure/access. Do
not multiply unpaired marginal fractions. The single proposed A108 contribution
is 100×O for the organism-capability question or 100×C for a defined sample-
coverage question, selected from the biological claim before scoring. Return
both diagnostics when useful, but never add them or choose the larger after
seeing the results. The lower bound is proposed supported credit; upper and
missingness must travel with it. Neither quantity is annotation probability.

| Evidence or checked example | Numerical cells | Meaning and limit |
|---|---|---|
| **Published B. plebeius porphyran case** ([Hehemann 2012](https://doi.org/10.1073/pnas.1211002109)) | Specific diet→intestinal resident route membership [1,1]; actual sample delivery/concentration [0,1] | Gut residence is compatible with using an ingested marine polysaccharide. Marine ancestry is not a necessary marine-habitat requirement. No rarity penalty or inferred 291-strain success fraction. The first interval concerns one route component, not complete annotation support. |
| **Published Cdv case** ([Lindås 2008](https://doi.org/10.1073/pnas.0809467105)) | The named strain's cytokinetic site exists: contextual membership [1,1]. Target endosomal-compartment operand: missing [0,1] from this paper | The organism's own cellular process constrains a homolog's physiological role. Homology to endosomal proteins does not establish endosomes. No organelle absence is invented. |
| **Fully synthetic complete geometry example** | 10/12 accessible episodes; 9/10 of those geometrically compatible; C=(10/12)(9/10)=3/4; O=1 | Capability display 100, sample-coverage display 75. Same evidence, two different meanings, one selected contribution. All widths, bounds and observations are invented. |
| **Synthetic rare opportunity** | One compatible episode of 12: C=1/12; O=1 | Rare occurrence does not reduce contextual capability. |
| **Synthetic negative sample** | 0/12 observed compatible, permitted unexamined states remain: O=[0,1] | No sightings are not proof that the organism cannot provide the context. |
| **Synthetic interval uncertainty** | One width becomes unresolved: C=[2/3,3/4]; O remains 1 because other witnesses survive | Missingness is preserved, not changed to 0.5. |

The exact reader fields are specified separately and all are **UNIMPLEMENTED**.
They identify measured trait values/units, necessary relations, organism and
population/life-stage/compartment scope, compatible/incompatible domains,
uncertainty, alternative routes, unexamined states, sampling denominators,
shared observations and the selected question. A narrow interpretation must
state its precise referent and population and can return unresolved; it cannot
emit a universal relevance grade.

Repeated papers, database mirrors and technical readings do not add witnesses
or sample weight. A104 retains phylogeny/HGT; A105 activity; A106 perturbation;
A107 partners/coexpression; A110 chemical/pathway feasibility; A111 experimental
structure. Their measurements may define contextual dependencies but cannot
receive a second independent A108 experiment score.

Verification: the fixed arithmetic script passed, including exact fractions,
duplicate neutrality, missingness, rarity and paired-versus-marginal behavior.
A separate calculation checked native-unit interval margins and propagated a
whole-scope exclusion through observed and unexamined states. Two main primary
reports were inspected, each followed by the complete authority reset. Native
source counts and exact missing operands are preserved in the case files.

This delivers a proposed numerical repair of the organism/clade gap, with
two contrasting case conversions, a fully filled synthetic calculation and
targeted reader contracts. The existential meaning and question-kind handoff
are the concrete design choices for user feedback. They have not been adopted.
No production reader, prompt, library, score, checklist, current target run or
HPC job was changed. A105 remains first. Existing sheet completion accounting
was not changed.
