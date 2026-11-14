# Pdx1/Pdx2: conditional partner evidence and the numerical sheet

Original source: Dick et al.2010, DOI10.1111/j.1365-2958.2010.07381.x,
Molecular Microbiology78:980–988. Inspected the first Results section, Figure1
and the full cloning/purification/enzyme-assay Methods. The full article was
available through publisher PDF rendering in the web tool; ordinary PDF download
returned HTTP403. The retained files explicitly contain tool-rendered text and
receipts, not original PDF bytes. TableS1, original instrument traces and other
papers were not inspected. PARENT_RESET_001.json records the completed post-paper
reset before this conversion. Original records remain intact.

## Experimental definitions

Pdx1/Rv2606c and Pdx2/Rv2604c are the two M.tuberculosis proteins. They were
expressed as C-terminal6xHis fusions in BL21-CodonPlus(DE3)-RP using pET21a+,
purified by Ni-NTA and size exclusion. Exact construct boundaries were not
verified from the primer supplement. Expression host and source organism are
different. This is a purified-enzyme system, not a native genomic-presence or
coexpression experiment.

The PLP endpoint uses absorption at414nm. Methods specify50mM Tris-HCl pH8,
37°C,20µM purified Pdx1 and/orPdx2,1mM R5P or Ru5P,1mM DHAP or2mM DL-G3P,
and10mM glutamine or10mM ammonium sulfate. The two-protein optimal molar ratio
is reported1:1. Samples were preincubated30min without C3 phosphosugar.
The PDF text rendering loses micro symbols; the page5 visual establishes µM
protein rather than its erroneous rendered mM. Retained source bytes are not
silently corrected.

The comparison of interest uses R5P/G3P. Pdx1 and Pdx2 coexist in the glutamine
arm. The ammonium-sulfate arm has Pdx1 without Pdx2. Two factors therefore change:
Pdx2 presence and nitrogen reagent. Equal reagent molarities do not make those
chemical sources interchangeable experimental conditions. No physiological
ammonium availability follows from the in-vitro bypass.

## What the measured numbers can populate

| Source quantity | Retained number | Interpretation and missingness |
| --- | ---: | --- |
| Pdx1/Pdx2, glutamine; first Results, p982 | 774±58pmol/min/mg | Reported PLP specific activity; mass-normalization identity unresolved |
| Pdx1, ammonium sulfate; Fig1D caption, p981 | 284±33pmol/min/mg | Reported bypass activity; a different nitrogen condition |
| Ratio of printed values, computed here | 284/774=142/387≈0.3669250646 | Descriptive arithmetic only; not residual activity after controlled omission |
| Same-glutamine Pdx2 omission rate | unknown | Cannot substitute the ammonium arm |
| Pdx2 addback rate | unknown | No third quantitative arm in the inspected material |
| Independent preparation count | unknown | Four repetitions in triplicate are reported; this does not establish12 independent preparations |
| Statistical uncertainty of the reported rates | unknown | Fig1 caption does not define the ± meaning; other figures' SD statements do not fill it |

The glutaminase result is a separate direction and endpoint: Pdx2 activity was
detected only with Pdx1 present. KM1.06mM and kcat0.12s^-1 are reported for the
complex. They do not supply an absent-partner detection limit or reverse the
relationship to a quantified Pdx2 requirement for Pdx1 PLP formation. No zero
rate, infinite activation, bound or likelihood is manufactured from nondetection.
The source attributes activation to complex formation; the activity observation
is kept separate from that mechanistic interpretation.

## Paired extraction fields and numerical components

Each arm must carry its actual subject and partner identities, partner state,
endpoint, rate unit, identity of the normalization denominator, nonpartner
condition factors with coverage, physical measurement identity and the native
value or censoring limit. Reported spread magnitude and kind remain distinct.
Source custody/quotes support these interpretations without proving them.

For W=with-partner, O=omitted-partner and A=addback under matched nonpartner
conditions and a common normalization, the proposed numerical components are
loss=W-O; fractional loss=(W-O)/W; gain=A-O; addback fraction=(A-O)/(W-O);
restored-reference fraction=(A-O)/W. The last equals fractional loss times
addback fraction when the latter is defined. This supplies explicit subtraction,
division and component multiplication without a generic quality grade.

All calculations preserve their original experimental scale and shared operands.
No clipping hides inhibition or overshoot. Fractional loss evaluates dependence
in this assay, not universal essentiality or a causal probability. A matched
omission and addback still need controls for contaminants, active amounts and
other alternatives; matching does not establish effect isolation by itself.
No new arbitrary validity multiplier or final annotation score is adopted.

For the present Pdx pair, the two native cells are populated, and every derived
partner/removal/addback cell is unavailable. Known nitrogen difference is retained
even though the normalization identity and condition completeness are unresolved.
The executable input retains this deliberately incompatible pair to verify that
native information survives without receiving a controlled-removal interpretation.

A separate **synthetic** matched example W100,O20,A90 gives loss80, fractional
loss.8, gain70, addback fraction.875 and restored-reference fraction.7=.8×.875.
If the synthetic omitted arm instead is censored O<=5, W100 and A90, the exact
conditional domains are loss[95,100], fractional loss[.95,1], gain[85,90],
addback fraction[85/95,.9], restored-reference fraction[.85,.9]. These preserve
one shared O. They condition on W/A being exact and are not confidence intervals.
The calculator must not infer a statistical error model from the unknown spreads.

## Targeted investigation instruction proposal

“Establish which molecule's measured activity depends on which partner, for
which endpoint and conditions. Read the actual omission and addback arms.
Check whether removal also changes nitrogen source, substrate, active subject
amount, reporter or normalization. Distinguish protein addback from bypass with
a chemical resource. Retain quantitative rates, detection limits and uncertainty
meanings. If a controlled arm or limit is missing, report that specific gap;
do not turn nondetection into zero or infer a universal required-partner set.”

This is the proposed scientific TASK content, separate from the numerical table
and calculator. It is not yet installed in recurring episode prompts.

## Handoff and implementation boundary

Later A107 use needs a directed requirement tied to a particular function and
nitrogen/resource condition. Mention of a protein,1:1 optimal mixing or positive
complex activity does not by itself establish a universally mandatory partner.
The ammonia bypass is resource evidence relevant to later A110 interpretation;
it is not a second genomic protein partner or an empty partner clause earning1.
No genomic search, coexpression score, target transfer or W05 combination occurs.

PAPER_SELECTION_001.json is an explicitly coordinator-transcribed retained
measurement input. PAPER_ARGUMENTS_001.json supplies source witnesses and no
numeric operands. The new pure calculator and retained-input reader are the
current implementation workload. A native publisher parser, selected storage,
recurring TASK installation, typed episode delivery, reconstruction and actual
model use of these new components remain unfinished. Quantified matched primary
omission/addback evidence remains to be found and examined. Neither this paper
nor synthetic examples close that requirement or a whole evidence axis.
