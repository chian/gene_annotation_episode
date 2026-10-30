# A107 concise printable handoff

**A107 now has one coherent current numerical proposal for required partner presence and coexpression.** The current sheet incorporates the missing-condition correction and keeps the originally verified complete examples unchanged. It is a proposed support coordinate, not a calibrated probability or an implemented reader/scorer.

For each required partner:

`H=clip(pair_alignment_score/sqrt(self_query_score*self_reference_score),0,1)`;

`G=P*H`, where P is a confirmed genomic 1/1 or genuinely resolved 0/1 observation. Exact versioned molecular identity permits H=1 without inventing an alignment. Missing genomic scope is unknown, not absence.

For each native expression panel:

**`E=H0*D_full*max(0,r_full)^2`**, where H0 maps the target to the expression target, D_full is the integer co-detected condition count divided by all requested conditions, and r_full is the full-panel growth-adjusted correlation. Multiple comparable blocks use the proposed minimum E. Then:

**`s_partner=G*(.5+.5*E)`**;

**`A107=max_over_genuine_alternative_sets(min_over_required_partners(s_partner))`.**

The .5/.5 weighting, positive-r-squared transformation, block minimum and required/alternative min/max are explicit proposed conventions. They are not measured probabilities. A measured nonpositive correlation contributes no positive expression term; the genomic term remains.

| Complete source-data example | Candidate calculation | Result and conditional family interval |
|---|---|---|
| YfgM–PpiD–SecYEG | min(.738626,.836426,.734563,.610556) | **.610555827945**, [.500000,.910103] |
| NlpI–MepS with PBP4 or PBP7 | max(min(.5,.733153),min(.5,.713151)) | **.5**, [.500000,.723892] |
| NlpI–PBP1A–LpoA–PBP4 | min(.768489,.5,.733153) | **.5**, [.500000,.773466] |

These are newly derived statistics from retained PRECISE processed RNA data: 28 cultures reduced to 12 equal condition means. The exact reference loci give P=H=H0=1; all relations have D=12/12. The parent already verified the public-input hashes, reconstructed the means and reproduced all ten associations. This consolidation rechecked their final numerical joins without claiming new primary review or repeating the large dataset reconstruction. Transcript correlation does not establish physical binding, protein stock, stoichiometric sufficiency or causality.

The published comparison cells remain distinct. Götzke's PpiD band is 99% of its own WT; 99/112=.883929 is only a **conditional** extra loading correction because prior normalization is unresolved. Banzhaf's PBP4/NlpI synthesis ratio is 441/389=1.133676, versus MepM/NlpI 341/389=.876607. Those synthesis-per-generation ratios do not measure steady-state partner supply. Neither protein panel is treated as a coexpression correlation. [Götzke 2014](https://doi.org/10.1074/jbc.M113.541672), [Banzhaf 2020](https://doi.org/10.15252/embj.2019102246).

The complete synthetic case supplies the absent nontrivial sequence example: H0=.9; P/Q/R genomic correspondences .8/.75/.9; co-detection 18/20,16/20,20/20; adjusted r=.8,.6,−.4. Their partner values are .60736,.47220,.45000. `(P AND Q) OR (P AND R)` gives **.47220**, with conditional family interval **[.45,.574485863585]**. An optional partner at .86081875 is excluded. A distinct same-scope weaker-positive P block changes the candidate to .45184; a contrary P block changes it to .4 under the stated repeatability minimum. Duplicate reports do not change it.

**Missing-condition correction:** if only 16 of 20 conditions are measured, their r=.6 cannot be blended by 16/20. The four additional conditions can reverse full-panel r. In the checked counterexample, the eventual r is −.879245283019 and the partner score is .375. The old [.4722,.5397] range excluded it. The current pre-completion result is **point null, outer range [.375,.7125]**. Missing correlation is not zero. Paired-expression coverage and growth-covariate coverage have separate counts; known nondetections stay in D's denominator when growth is missing.

The [current sheet](A107_NUMERICAL_SCORING_SHEET_001.md), [exact population crosswalk](A107_EXACT_CELL_CROSSWALK_001.md) and [source/criterion record](A107_SOURCE_AND_COVERAGE_001.md) supply all seven research deliverables. Eighty-seven bounded arithmetic checks passed; the count includes repeated per-relation assertions and is not a count of scientific validations. No production change, target run or HPC work was performed. Remaining choices are explicitly specified but unadopted; actual absent measurements retain nulls and bounds. Final ordered presentation and checklist accounting remain with the parent.
