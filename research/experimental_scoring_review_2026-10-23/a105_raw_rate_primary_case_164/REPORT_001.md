# Case164: source-native BbPK activity contrasts

This one-paper case supplies individual reported activity values, not merely means. It does **not** establish raw-reader binding in LiteratureEpisodes, independent enzyme preparations, calibrated product-specific rates, or A105 adequacy. All work is confined to this new case directory; no production, test, goal, historical-pin, amendment or live-state file was edited. The broader goal retains exactly A101–A107, A110, A111; this case addresses only reference A105 evidence, with no target transfer or W05 aggregation.

Primary source: Yang et al., *Construction of an artificial phosphoketolase pathway that efficiently catabolizes multiple carbon sources to acetyl-CoA*, [PLOS Biology article](https://journals.plos.org/plosbiology/article?id=10.1371/journal.pbio.3002285), DOI10.1371/journal.pbio.3002285. Actual underlying values: [S1 Data](https://journals.plos.org/plosbiology/article/file?type=supplementary&id=10.1371/journal.pbio.3002285.s034), Sheet1, Fig2B block. Supporting summaries: [S1 Table](https://journals.plos.org/plosbiology/article/file?type=supplementary&id=10.1371/journal.pbio.3002285.s025). Originals, exact URLs, sizes and SHA256 are in `custody.json`.

## Experimental definitions and limits

The studied subject is the paper's BbPK, labelled “Actinobacteria Bifidobacterium,” cloned into pET-28a via NdeI/XhoI, expressed in E. coli BL21(DE3), and purified by nickel affinity chromatography. The source packet does not establish the particular species/strain or sequence-to-raw-column mapping; S9 gene labels PK1–PK11 are not themselves that mapping. Exact retained tag/construct boundaries and preparation identities remain unknown. No mutation is selected here. Separate D-EUS, L-EUS and DHA reactions contain the same nominal BbPK construct. Substrates replace one another between arms; D- and L-EUS are not a co-mingled substrate pool. Helper enzymes coexist with BbPK if the coupled assay is used.

The intended primary change is D- versus L-erythrulose at nominally matched substrate concentration. A second contrast changes D-erythrulose to DHA. Both contrasts reuse the same D-EUS readings. These are two comparisons of three source groups, not six independent experiments.

Fig2B/S1Data report catalytic activity in U/mg. The article describes (i) short-chain coupled assays measuring NADPH at340nm, with AckA, hexokinase and glucose-6-phosphate dehydrogenase, and (ii) direct endpoint assays converting AcP to acetate for HPLC and chromogenic AcP detection. The Fig2B workbook block does not explicitly bind its individual values to one method, time window, preparation, blank or calibration record. The multi-species coupled-method paragraph specifies200μL,0.25mg/mL PK,10mM substrate,pH7.5,37°C; a separate PK/mutant paragraph specifies100μL and approximately0.5mg/mL PK. The direct D/L protocol specifies200μL,1mg/mL PK,10mM substrate,pH7.4,37°C,0.5h. Do not silently attach one protocol's denominator to the raw rate cells.

The direct D/L protocol does establish a nominal protein mass0.200mL×1mg/mL=0.200mg and exposure0.5h×60=30min for each arm, hence a common normalization denominator0.200mg×30min=6mg·min. Its nominal D/L protein-dose ratio is1 and exposure ratio is1. These are quantitative comparability components for that described direct experiment, conditional on executing the stated protocol; they do not establish equal active enzyme, identical preparation, accuracy, or a numerical comparability grade for the workbook rates.

## Paired extraction fields and populated numerical cells

Extract source subject/construct, substrate arm, source-labelled parallel observation, exact XLSX numeric lexeme, unit header, endpoint/normalization meaning, preparation/grouping/pairing knowledge, method-binding evidence and uncertainty meaning **together**. `EXTRACTION_001.json` retains nine individual observations, their source labels and exact cell locations. Source labels “Parallel1–3” support documented source-scoped observation record identities. Coordinates identify representations; they do not independently identify physical experiments. No globally unique laboratory ID is required. No preparation ID or independence is inferred.

All following values are calculated from reported cells, in native U/mg. They are not new experiments or probabilities.

| Substrate | Source individual cells | Values (U/mg) | Descriptive mean | Descriptive sample SD | SD/mean |
|---|---|---|---:|---:|---:|
|D-EUS|J16:J18|0.53756666666666675;0.50628666666666677;0.46956666666666674|0.5044733333|0.03403624735|0.06746887317|
|L-EUS|J12:J14|0.17920666666666668;0.20300666666666667;0.18464666666666665|0.1889533333|0.01247078720|0.06599929717|
|DHA|J8:J10|0.15880666666666665;0.15064666666666665;0.16084666666666667|0.1567666667|0.005397332675|0.03442908361|

Mean=sum(the three labelled reported values)/3. Sample SD=sqrt(sum((value−mean)^2)/(3−1)). CV=sampleSD/mean. The denominator3 is the number of separately reported parallel measurements, **not** an independent preparation count. Variability describes these source readings, not population sampling uncertainty. If actual nested units later become available, average readings within each unit before equally weighting unit means; do not substitute this flat descriptive SD for between-unit SD.

With D-EUS as reference, the existing sheet's numerical contrast meanings give:

| Component | D-EUS versus L-EUS | D-EUS versus DHA | Meaning |
|---|---:|---:|---|
|reference−test|0.3155200000 U/mg|0.3477066667 U/mg|reported activity separation|
|test/reference|0.3745556422|0.3107531287|retained source activity at this specified alternative substrate|
|1−test/reference|0.6254443578|0.6892468713|fractional decrease in that reported endpoint|
|reference/test|2.669830293|3.217988518|inverse activity ratio; same operands, no extra independent evidence|

The stereoisomer contrast addresses a functional distinction; both arms have positive reported activity. It does not establish exclusive stereospecificity, kcat/Km, physiological substrate use, saturation or product-pure catalysis. Different substrate matrices may alter reporter/coupling response, so the ratios remain **reported-activity contrasts** pending matrix-specific validation. They are not final reliability or annotation scores. Native U/mg differences and dimensionless ratios do not require canonical conversion when the common source convention is preserved. No explicit source definition of U was found; conversion to μmol/min/mg remains unknown.

S1Table H8 reports0.1890±0.0125 and H9 reports0.5045±0.0340, matching the corresponding raw means/spreads after rounding. H7 reports0.1569±0.0054, whereas the raw DHA mean rounds to0.1568. Preserve the discrepancy0.0001333333 U/mg between the printed central value and raw mean. The table's ± type is not declared in the examined table; arithmetic agreement does not establish SD. FigS17's SD,n=3 caption cannot be transferred to Fig2B by proximity.

## What each evidence component needs

| Meaning in numerical sheet | Extracted operands / current numeric result | Limit / missing operand |
|---|---|---|
|Experimental comparability outside changed substrate|Direct-protocol dose0.2mg, time30min, denominator6mg·min in each arm; dose and time ratios1|Raw-sheet method binding, actual amounts, active fraction and common preparation unknown. No arbitrary fraction-of-matching-fields score.|
|Signal and consistency|Means, SD,CV and specified contrasts above|Only within reported parallels. Between-preparation SD,count,SE and confidence intervals unavailable.|
|Effect isolation|No-PK control is explicitly described for separate S3 HPLC activity test|No numerical matched blank rates for selected raw cells; no source-quantified contaminant contribution, inactive-enzyme control or isolation fraction. No exact-zero blank from a flat-looking trace.|
|Validity / reliability|BCA protein assay uses BSA standard; AcP detection and HPLC protocols described|Standard nominal/observed values, calibration recovery,linearity,LOD/LOQ,hydrolysis recovery and substrate-matrix effects absent for selected readings. No numerical validity multiplier.|
|Endpoint/function specificity|S3 supports acetate after AcP decomposition; S5 GC-MS compares derivatized coproducts to standards|These are complementary chemical-identity evidence; no quantitative rate linkage to nine selected readings, exact mass-error score or new preparation count. Acetate alone may include non-AcP background; coupled NADPH requires validated coupling attribution.|
|Shared / dependent / complementary evidence|D-EUS J16:J18 reused in both contrasts; S1Table and Fig2B repeat the source results|Do not sum ratios, inverse ratios and table/figure representations as independent evidence. S3/S5 address different weaknesses; biological independence is not demonstrated.|

For a **proposed**, source-native corrected contrast under validated linear coupling, explicit combination can be:

Q_L/Q_D = ((μ_L−b_L)/(μ_D−b_D)) × (g_D/g_L) × (f_L/f_D).

Here μ is reported mean in U/mg; b is matched no-PK background expressed with the same mass normalization and native unit; g is measured dimensionless reporter recovery/gain in the particular substrate matrix; f is the dimensionless fraction of corrected response attributable to the intended product-forming process. f must not duplicate a correction already in g. Each operand needs an experimental source and positive nonzero denominators. This combines subtraction for background and multiplicative calibration/isolation corrections; it is not an adopted generic reliability formula. Only μ is populated here. b,g,f remain unknown, so no corrected Q ratio is populated and unknown is not replaced by1.

For the **separate described direct endpoint experiment**, a useful future controlled rate is (measured acetate amount−matched background amount)/(6mg·min), with any validated quantitative recovery correction applied explicitly. Product amounts and recovery are absent here. This formula clarifies exactly what the nominal comparability denominator can and cannot establish.

## Targeted reader proposal and implementation gaps

A later selected publisher-XLSX reader should verify original workbook digest, Sheet1, Fig2B A1, native unit C2, subject J3, substrate C7/C11/C15 and source observation labels C8:C10/C12:C14/C16:C18, then select the nine J cells. Preserve numeric lexemes, cell type, formula/cache distinction, original file/member identities and labels. Return source-labelled observation identities derived from those meanings. Preserve unknown scientific grouping separately. Do not derive a new physical measurement identity merely from a cell address, matching values or row order. Request exact protocol/endpoint bindings with source witnesses; return unknown when not established. `EXTRACTION_001.json` is a research proposal, not a production typed record.

Current raw CSV/TSV reader requires exact headers including sampling_unit,observation_id and canonical rate unit. The publisher workbook has none of that prepared layout. A documented source Parallel label can support an observation record identity; lack of a globally unique lab ID is **not** a missing-source requirement. Underlying scientific sampling-unit grouping is unknown. A reporting-level flat summary should remain available without fabricating biological units. A targeted XLSX adapter and an explicit unknown-grouping/descriptive path remain implementation work. Current aliases reject symbolic U/mg; supporting same-source native-unit arithmetic is an implementation gap. Absence of a source U definition is a separate missing input **for physical conversion**, not grounds to discard native-unit results.

No actual LiteratureEpisodes execution, raw-reader publication, durable typed return or reconstruction was run by this case. Existing complete contracts were read; sibling fresh163 work was not assumed implemented or accepted. No model/provider request,response,conversation or log was inspected. No new prompt was installed, no biological suite or original experiment rerun, and no OCR/digitization was used.

`calculate_001.py` computes exact-source Decimal arithmetic and checks mean/variance independently with Fraction. `verify_arithmetic_001.py` independently checks17 mean/SD/CV/contrast results using fsum/statistics; all17 passed. This verifies arithmetic, not scientific extraction truth or assay validity. Full successful read/reset provenance and repaired truncation attempts are in `READ_PROVENANCE_001.json`. The user/parent must review concrete extraction instructions and numbers in conversation before broad replication; no production approval gate is introduced.
