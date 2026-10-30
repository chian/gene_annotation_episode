# Published case 1: a rare gut function is not a clade contradiction

Source: Hehemann et al. 2012, [PNAS](https://doi.org/10.1073/pnas.1211002109),
retained case `organism_08_porphyran`. Primary text read from the existing
`a104_phylogeny_sheet_012/porphyran_primary_text_001.txt`, lines 1–730 in complete
sequential portions. Main Results, Discussion and Methods were inspected;
supplementary experiments and original graphs were not inspected here. A full
authority reset followed before this conversion.

## Experimental definitions and source operands

The organism is Bacteroides plebeius DSM 17135; the native-strain comparison
changes the sole carbon source. There is no mutant/WT coexpression comparison.
The paper reports porphyran-supported growth and a screen of 291 additional gut
Bacteroidetes. The exact number positive for each polysaccharide is absent from
the main-text account. Three porphyran-grown qPCR cultures were collected at
A600 0.57, 0.56, 0.57; three galactose cultures at 0.41, 0.42, 0.43. These are
harvest densities, not growth-rate replicates or environmental opportunities.
Thirty-five PUL genes were tested and induced; five were not tested. Purified
catalytic domains separately establish enzyme activities. The paper's human
diet discussion does not measure individual dietary intake or gut exposure.

Source locations: Results, “Screening of Gut Bacteria…” and “B. plebeius PUL Is
Activated…”; Fig. 1 caption; Materials and Methods. Homology/ICE history belongs
to A104; activity to A105; expression/partners to A107. None supplies a second
independent A108 experiment.

## Conversion to the organism-context sheet

The relevant contextual question is whether a gut-resident organism can have a
role involving a dietary marine polysaccharide. “The characterized homolog was
marine” is not a necessary requirement that the target organism itself be
marine. Making that an exclusion would discard the very biological situation
examined by this paper. The precise contextual route is dietary material →
intestinal compartment → resident microorganism. The existence of that route
is different from the amount delivered on a particular day.

For an emerged role scoped as **porphyran use by a gut resident when porphyran
arrives in its intestinal compartment**, the proposed A108 cells are:

| Component | Exact referent and denominator | Source-filled operand / result |
|---|---|---|
| Organism habitat architecture | Does this organism inhabit a compartment reached by dietary polysaccharides? One stated organism-context, not 291 literature votes | B. plebeius is the gut-resident study organism. Context event `diet_to_gut_resident_route` is compatible, [1,1], conditional on that exact route interpretation. |
| Marine-organism prerequisite | Is marine residence necessary for the stated role? | No such prerequisite is justified by the role. It is not inserted as a scored requirement. The characterization is a counterexample to a blanket marine-only restriction. |
| Current local porphyran availability | Porphyran at the supplied target's compartment, conditional on the declared role situation | Unknown for an unspecified human sample. No measured numerator, denominator, local concentration or ingestion history; [0,1]. |
| Organism-context contribution | Joint membership of the single demonstrated habitat route, divided by one stated organism-context | O−=O+=1 for this narrow contextual route; it does not score a molecular function or all Bacteroidetes. |
| Full contextual opportunity contribution | The same organism-context combined with local exposure, without inventing exposure data | Joint bounds [0,1]; point=null. The positive organism match is retained, while unknown exposure is not filled by 0.5. |

The source's activity results define a feasible role and a reference context.
They are dependencies, not new independent evidence. The new A108 comparison
is between that reference context and the target's actually supplied organism
and sample context. If the target is merely an unnamed gut sequence with no
organism assignment, the organism-context value also remains [0,1]. A clade label
cannot silently establish the habitat of a particular sample organism.

## Numerical boundary checks and missing operands

The tested-gene coverage is 35/(35+5)=0.875. That is coverage of an expression
measurement, not 87.5% A108 plausibility. The mean harvest density ratio is
[(0.57+0.56+0.57)/3]/[(0.41+0.42+0.43)/3]=85/63=1.34920635.
It cannot be turned into a growth advantage, an effect-isolation factor, or an
ecological relevance score. Comparing transcription at these different harvest
densities requires the A107 analysis to retain the phase/density distinction.

The 291-strain screen is not a denominator for the probability that a sequence
has the proposed function. It is neither a random sample of all gut organisms
nor a measured number of independent human exposure opportunities. No negative
A108 factor is computed from rarity. Exact positive counts and the sampling
design would be needed even for a descriptive prevalence estimate; those are
not needed to establish a demonstrated exception to a categorical exclusion.

Experimental comparability is the same strain with a deliberately changed
carbon source, but background density and substrate preparation differ or need
the supplement. Isolation of the measured effect is separate: whole-culture
growth does not assign causation to one enzyme. Enzyme-specific activity and
genetic contribution remain separate dependencies. A matched dietary delivery
or local substrate observation would fill the missing sample operand. A human
dietary intervention is not claimed.
