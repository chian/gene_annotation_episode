# A105 effect isolation: the Aquifex HFP preparation

Research proposal only, after this agent's complete owned post-paper reset. This is one publication with its supplement, not additional completed graders or a completed A105 sheet. No implementation or goal change is made.

The publication establishes sugar-phosphate isomerization in an HFP-containing preparation and identifies E. coli RpiA in that preparation. It does **not** report the matched quantitative contaminant activity needed to partition the observed signal between HFP and RpiA. The correct contribution to A105 is therefore a precise, source-supported limit on molecular attribution while preserving the measured chemistry. A new generic contaminant-rate reader would not fix this case: the current compiler already accepts such a rate.

Source: Hoffpauir and Lamb, *Identification of the phosphatase that catalyzes the essential substrate dephosphorylation step of riboflavin biosynthesis in Aquifex aeolicus*, JBC 2025, [DOI](https://doi.org/10.1016/j.jbc.2025.108443), [original article](https://pmc.ncbi.nlm.nih.gov/articles/PMC12051542/). Original JATS, original DOCX, original image members, acquisition receipts and reading derivatives are retained here. SOURCE_WITNESSES_003.json is the current locator ledger; earlier two locator drafts and explicit corrections remain preserved.

## What was actually compared

HFP is PP17, A. aeolicus protein accession WP_164930753.1 in supplemental Table S1, DOCX paragraphs128–130. IMP is PP11, WP_010881296.1, paragraphs110–112. The retained corpus additionally labels HFP aq_1744/O67630; those identifiers were not freshly sequence-mapped by this workload. No guessed function follows from a gene label.

The proteins were expressed in E. coli BL21(DE3). The initial pET20b constructs had a stop before the vector's C-terminal histidine tag and were untagged. A separate later HFP construct retained a C-terminal His tag. HFP and host proteins coexist within each preparation. HFP and IMP replace one another in the compared pathway vessels, while RibBA, RibD, lumazine synthase and riboflavin synthase coexist with whichever preparation was added. These are not assays of an isolated HFP molecule alone.

| Comparison | Intended question and actual endpoint | Important additional differences and limits |
|---|---|---|
| Initial HFP preparation plus Ru5P versus enzyme-buffer control | Does this preparation change sugar phosphate? 31P-NMR identifies R5P and Ru5P by chemical shifts; reverse-substrate assay approaches the same composition. | An endpoint composition is not an initial rate or identification of the catalyst. The HFP preparation includes host proteins. |
| Initial untagged preparation versus more highly purified His-tagged/heated preparation | Does activity persist after purification intended to remove contaminants? Time to the sugar-phosphate equilibrium becomes much longer. | Construct, chromatography, buffer history, heating and recovered material all change. Heating continues until visible precipitation; remaining target amount, active fraction and contaminant amount are not quantitatively paired. |
| Five other putative phosphatase preparations | Is isomerization unique to the HFP preparation? Four show the R5P peak. | Different proteins/preparations, no calibrated contaminant amounts or matched initial rates. They are not five HFP independent preparations, nor individually demonstrated isomerase-negative proteins. |
| MS of the HFP preparation | Is a named host enzyme present that can explain this chemistry? E. coli RpiA is identified. | Protein identification is complementary to chemistry. Peptide/spectral counts do not calibrate molar amount or catalytic contribution. |
| HFP versus IMP in one-pot pathway | Which preparation permits riboflavin accumulation in this reconstituted system? | IMP removes pathway inputs NADPH and Ru5P. This explains failure of the coupled pathway without establishing that the candidate dephosphorylation reaction is absent. HFP and IMP amounts differ. |

The one-pot mixture contains RibBA7.6µM, RibD10.8µM, lumazine synthase30.9µM, riboflavin synthase33.3µM, GTP1mM, Ru5P0.72mM and NADPH1mM; HFP8.4µM or IMP8.8µM; 55°C for4.5h; triplicate (main Methods, derived text line177). The stated400µL mixture divided into two250µL flasks is a source bookkeeping inconsistency, not repaired here. There is no numerical product-rate comparison in this packet that can be normalized using these amounts alone.

For basic31P-NMR, Methods reports triplicate assays,1.4µM enzyme, Ru5P0.67mM or GTP/NADPH0.5mM,1h incubation; HFP/IMP/buffer at55°C, YigB at37°C. Acquisition is at298K after enzyme removal,512scans, with pure standards and enzyme-buffer controls (line201). Scans are instrumental accumulation, not independent experiments. Independent expression/purification count is unspecified. The reverse-substrate Methods instead prints0.67M (line203); retain that conflict. The13C confirmation is one experiment,1024scans,6.3mM labelled Ru5P and7.6µM HFP preparation. It addresses chemical identity, not independent catalyst attribution.

## Numerical components and exact limits

All arithmetic below is in ARITHMETIC_001.json. These are native quantitative components or carefully scoped descriptive calculations, not an overall reliability score.

| Cell or calculation | Actual value / formula | Role in the A105 sheet and restriction |
|---|---|---|
| Reported endpoint Ru5P fraction |0.397| Native composition of the measured preparation's sugar-phosphate endpoint. |
| Reported endpoint R5P fraction |0.603| Native product identity/composition; cannot be assigned wholly to HFP. |
| Endpoint R5P/Ru5P ratio |60.3/39.7=1.51889| Reexpression of that composition. It is not turnover, specificity, or additional evidence. |
| Sum of the two reported fractions |0.397+0.603=1| Their compositional normalization closes. This does not independently establish quantitative total phosphorus recovery or exclude unmeasured species. |
| Figure S5 printed integral calculation |1.52/(1.00+1.52)=0.603175| Agrees with rounded60.3%. These printed integral labels and percentages describe the same spectrum. No fresh peak integration was executed. |
| Apparent HFP/bulk mass fraction |approximately5/7=0.714286| Methods line161: bulk Bradford7mg/mL; visual gel estimate approximately5mg/mL HFP. Approximate nominal mass normalization only. It is not active fraction or share of measured isomerase activity. |
| Conditional denominator conversion |7/5=1.4| If an actually available rate had been divided by bulk mass and the gel estimate were applicable, dividing by the estimated target mass would multiply that apparent specific activity by1.4. No such rate is supplied here; no corrected activity is populated. |
| Other positive preparations |4/5=0.8| Finite tested-cohort description. No assay false-positive rate, HFP activity probability or population prevalence follows. S7 samples are PP21,PP18,PP14,PP8,PP1; PP21 lacks the second peak in this panel. |
| RpiA identification support |7exclusive unique peptides;15exclusive unique spectra;27total spectra;101/219 residues covered=46.12%| Native reported identification resolution, not enzyme amount or activity contribution. |
| HFP identification support |27exclusive unique peptides;99exclusive unique spectra;1654total spectra;161/203 residues covered=79.31%| Different protein/peptide detection properties preclude interpreting27/1654 as contaminant molar fraction. |
| Author's main-text timing comparison |initial equilibrium<10min versus later>18h; arithmetic bound18×60/10=108| The main prose implies a>108 ratio of completion times. This is not an intrinsic activity ratio: target amount, preparation, conditions and completion criterion are not matched quantitatively. Do not put108 into q, g or a reliability multiplier. |

S5 caption explicitly specifies a10min room-temperature incubation. S6 caption/labels show1h and18h, whereas the main text says>18h. Preserve these source/condition qualifications. The S6 image has no calibrated initial rate or paired quantitative integrated fractions. Peak-height reading cannot provide them.

S2 gel and caption explain a particular detection weakness: RpiA~22,860Da is close to HFP~23,691Da, so it may be hidden under the target band. The faint48–63kDa bands are explicitly **not** the Rpi contaminants. Visible target dominance cannot supply a quantitative contaminant absence bound. S8 is a reported MS identification (Orbitrap Fusion Lumos DDA, Mascot2.8.3, Scaffold5.3.3;95%peptide/99%protein thresholds,minimum2peptides,reported protein-levelFDR~0%). Those reported identification settings are not an actual zero error rate, purity or probability that HFP caused the reaction. None of those software packages was executed here.

## The numerical assembly that is justified, and what is missing

For a **matched additive rate assay**, the existing logical sheet expresses:

`q = observed concentration rate − applicable blank rate`

`r_HFP = q − g`

`a_HFP = (q − g) × (1/k) × (1/E_HFP) × (v/u)`

Here g is the additional contaminating contributor's rate on that same endpoint/scale, k is applicable reporter recovery, E_HFP is the applicable molecular amount, and v/u is the measured nuisance-condition response excluding the intended change. These are physical sums/multipliers, not categorical quality weights. For positive q, `(q−g)/q` could describe the isolated share only if the component model and nonnegative contributions are established. No such fraction is populated in this case.

The paper supplies neither a matched initial-rate q for this isolation comparison nor an isolated/quantitatively bounded contaminant-rate g. It also lacks paired HFP/RpiA amounts and matched nuisance-response data before/after purification. Accordingly r_HFP, a_HFP, their joint uncertainty and an isolated activity share remain **unknown from this source**, not zero. Product composition and the evidence for a host contaminant remain populated. A completed endpoint near reversible equilibrium is especially unsuitable for additive causal partition: catalyst amount changes approach speed without necessarily changing the final composition.

The current `literature_assay_inputs.py` accepts source-bound g; `literature_compiled_assay_inputs.py` ALLOWLIST accepts contaminant_rate and native/raw-replicate rate components with additional_contaminant_contribution. The current compiled calculator already performs q−g and full correction. Its common branch background parameter means same-scale other-contribution rate. Its product-coupling branch explicitly distinguishes molecular attribution from productive coupling. Therefore this source supplies **no evidence that a generic g reader is missing**. Executing existing arithmetic cannot recover an unreported contaminant effect.

There is a genuinely needed **bounded interpretation/extraction relationship**: distinguish (a) a detected candidate contaminant, (b) a preparation perturbation consistent with its contribution, and (c) a measured or quantitatively bounded additional activity eligible for g. Mere agreement of units or MS identity must not upgrade(a)/(b) to(c). Existing generic relationships can retain this distinction, but this workload has not verified a specific deterministic producer that joins gel detectability, MS identification and nonselective preparation changes into these aspect-specific meanings. Paired field/producer proposal is in PAIRED_IO_NUMERICAL_001.md. This is a scoped source-interpretation contribution, not a new overall attribution grade or a second scoring axis.

## Complementary measurements and remaining follow-up

31P/13C chemistry answers which molecules change. Purification challenges the attribution but is not selective; the observed precipitation leaves target loss as a rival explanation for slowing. Other preparations demonstrate a shared-preparation problem. MS identifies a plausible host catalyst and explains why a seemingly clean gel does not exclude it. These measurements attack different weaknesses; none is automatically an independent replicate or an extra numeric confidence multiplier. The paper's cited E. coli RpiA turnover2100s^-1 is a cited literature value, not a freshly read matched55°C calibration, and is not used to produce g.

The informative next question is: **under the same substrate, temperature, buffer and initial-rate window, how much of the measured rate remains when RpiA contribution is selectively changed while recovered HFP amount and activity are controlled?** Search for reported matched fractionation/depletion plus spike-back, orthogonal host preparation, calibrated RpiA amounts/activities, or a genuinely selective perturbation with target preservation measurements. Different hosts or heat treatments still require their own comparability controls. This is an optional source-grounded follow-up, not a claim that these experiments were performed, a mandatory new experiment sequence, or a new computational biology job.

No A106 expansion, other paper, target correspondence, final annotation score or W05 aggregation was undertaken. The source's distinct phosphatase evidence should be assessed on its own chemical/pathway resolution; loss of the extra isomerase attribution does not erase all phosphatase observations or establish exclusive native ARAPDP specificity.
