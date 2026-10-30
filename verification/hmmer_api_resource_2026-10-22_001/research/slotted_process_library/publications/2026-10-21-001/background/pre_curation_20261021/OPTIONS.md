# Three-slot options

10 annotation distinctions, 19 thought patterns and 13 tool contexts. Counts reflect the current curation, not a target size or a completeness claim.

## Annotation distinctions for the structured credit form

| ID | Option | What its selection contributes |
| --- | --- | --- |
| [A01](DETAILS.md#a01) | Direct molecular operation | Represent what the target itself does: chemical transformation, binding, translocation or physical energy effect; distinguish a downstream consequence. |
| [A02](DETAILS.md#a02) | Molecular target, recognition range and exact feature | Represent which substrate, ligand, ion, macromolecule, sequence site or chemical feature is recognized or acted upon, with bounded exclusions and productive versus nonproductive recognition. |
| [A03](DETAILS.md#a03) | Mode and mechanism of molecular action | Represent how an assigned operation is physically or chemically achieved, at the level actually distinguished by evidence. |
| [A04](DETAILS.md#a04) | Productive requirements and coupled reaction account | Represent cofactors, substrates, electron/nucleotide donors and compatible partners required for productive operation, distinguishing coupled consumption from merely correlated stimulation. |
| [A05](DETAILS.md#a05) | Regulatory input, target and effect | Represent which input changes regulator state/abundance, through what route, and which target experiences activation, repression or another effect. |
| [A06](DETAILS.md#a06) | Contribution within a biological system | Represent a target’s specific responsibility in a multi-component process: execution, activation, cofactor supply, assembly, positioning, reset or another bounded contribution. |
| [A07](DETAILS.md#a07) | Spatial access, export and topology | Represent which compartment, membrane face or local site target/material can access and which export, topology or targeting feature enables the encounter. |
| [A08](DETAILS.md#a08) | Native physiological contribution and its conditions | Represent which cellular/organismal consequence an activity contributes to in biological context, preserving environmental, nutrient, temporal and population conditions. |
| [A09](DETAILS.md#a09) | Conditional necessity, overlap and residual function | Represent whether a target is needed for a named outcome under specified conditions and available alternatives: absolute loss, quantitative impairment, hidden overlap or no detected phenotype. |
| [A10](DETAILS.md#a10) | Functional replacement and route equivalence | Represent whether an alternative replaces the same reaction, one reference activity, a different route to the same product or demand for the missing function. |

Full entry content: [annotation_options.json](annotation_options.json).

## Thought patterns

| ID | Option | What its selection contributes |
| --- | --- | --- |
| [P01](DETAILS.md#p01) | Choose a relevant analogue and bound what transfers | Use similarity to a characterized system to form bounded explanations. Choose which sequence, local structural machinery, domain architecture, genomic context or organismal circumstance makes the reference informative for the disputed property; revise misleading comparators. |
| [P02](DETAILS.md#p02) | Seek cases that break a proposed predictor | Treat an implication as something that can fail. Prefer feature/function discordance: feature without function challenges sufficiency; function without feature challenges necessity. |
| [P03](DETAILS.md#p03) | Discriminate competing inputs by their predicted chemistry | Keep the candidate system explicit while choosing substrates, co-substrates or acceptors that distinguish competing recognition hypotheses. Refine the candidate space using identified products and bounded non-products. |
| [P04](DETAILS.md#p04) | Revise the failed attachment while retaining independent constraints | After a competent negative or contradiction, separate the part of the explanation that failed from independently supported constraints. Reopen alternatives within surviving constraints without either preserving the whole annotation or discarding everything. |
| [P05](DETAILS.md#p05) | Constrain missing-function hypotheses by what the system must accomplish | Use a supported output or requirement to distinguish loss of function, unfamiliar replacement, different route and changed demand. Evaluate candidate similarities and context against these system explanations. |
| [P06](DETAILS.md#p06) | Retain the system output and revise who contributes what | Keep a real aggregate output separate from its attribution. Compare direct chemistry, substrate/cofactor supply, enabling a complex, downstream filtering and production of an observable signal. |
| [P07](DETAILS.md#p07) | Distinguish restoration from bypass, compensation and reduced demand | An improved endpoint can repair the proposed molecular relationship, use another route, reduce demand or change downstream consequences. Compare those explanations before treating rescue as mechanistic equivalence. |
| [P08](DETAILS.md#p08) | Test the missing prerequisite behind conditional function | Investigate which enabling resource or molecular state permits a supported capability to matter. Distinguish that prerequisite from correlated stress, altered protein amount and reporter failure. |
| [P09](DETAILS.md#p09) | Separate physical access from chemical competence | Explain a missing cellular reaction by contrasting inaccessible substrate/partner, absent substrate, failed catalyst and failed reporter delivery. Prefer changes that discriminate the relevant barrier. |
| [P10](DETAILS.md#p10) | Account for the coupled chemical system | Choose an explicit account of matter, electrons, cofactors and energy needed for a conversion. Reopen incomplete boundaries when an isolated reaction is implausible or replacement changes metabolic demand. |
| [P11](DETAILS.md#p11) | Distinguish a possible route from the route actually used | Keep feasibility or measured capacity separate from native use. Contrast ordinary use, conditional backup, side activity and unused capacity without forcing a single-role explanation. |
| [P12](DETAILS.md#p12) | Compare biological consequences over the time that matters | Choose time/phase contrasts distinguishing transient acceleration, repeated function, adaptation and survival. An early benefit or first product need not predict later outcomes. |
| [P13](DETAILS.md#p13) | Resolve an aggregate claim at the biological level that separates explanations | Ask whether pooled change reflects uniform effects, selective subsets or changed mixtures. Choose biologically meaningful units whose contrasts separate those explanations. |
| [P14](DETAILS.md#p14) | Distinguish the transformation from its proxy readout | Treat bands, cofactor changes, substrate loss and downstream signals as compatible with several transformations. Prefer evidence separating intended chemistry from half-reactions, spontaneous conversion or artifacts. |
| [P15](DETAILS.md#p15) | Hold upstream success while investigating downstream failure | Preserve demonstrated recognition, binding, cleavage or delivery when productive output fails. Compare the additional compatibility or coupling explanations rather than repeat upstream positives. |
| [P16](DETAILS.md#p16) | Distinguish direct input action from indirect response and feedback | Environmental responses can arise through direct ligand recognition, cofactor chemistry, changed abundance or system-demand feedback. Choose contrasts distinguishing those routes before assigning a direct sensor or regulatory sign. |
| [P17](DETAILS.md#p17) | Separate linked functions through selective dissociation | Seek comparisons preserving one property while changing another. Use their dissociation to distinguish a required functional relation from amount, delivery, stability or another linked activity. |
| [P18](DETAILS.md#p18) | Reconcile conflict by testing scope-specific explanations | Compare apparently conflicting claims without choosing a paper or averaging them. Ask whether a tested difference in organism, state, assay window, relation or construct explains disagreement; preserve unresolved conflict where no discriminating match exists. |
| [P19](DETAILS.md#p19) | Investigate the route behind residual function | Preserve reproducible output after a focal loss while distinguishing another contributor from incomplete perturbation, imported product or reduced demand. Revise exclusivity without erasing the lost route’s genuine contribution. |

Full entry content: [thought_options.json](thought_options.json).

## Tools

| ID | Option | What its selection contributes |
| --- | --- | --- |
| [T01](DETAILS.md#t01) | Primary-source and retained-material access | Retrieve identified publications and advertised supplements, expose exact source windows, and extract selected tables or images while preserving source identity and inspection scope. |
| [T02](DETAILS.md#t02) | Protein sequence matches and local sequence features | Retrieve exact protein sequences, compare selected homologs or database matches, and expose domain/local-residue differences without converting similarity into substrate, orthology or native-role assignments. |
| [T03](DETAILS.md#t03) | Comparative gene neighborhoods, fusions and presence profiles | Expose gene-order, strand, fusion and component-presence observations across explicitly selected genomes and proteins; count only defined records and retain unknown or incomplete context. |
| [T04](DETAILS.md#t04) | Deposited structure identities, ligands and contact geometry | Retrieve exact deposited structures and metadata, map native chains/residues/ligands, and calculate declared geometric contacts without treating a static model as activity or physiological proof. |
| [T05](DETAILS.md#t05) | Fold, pocket and candidate-ligand model comparisons | Compare supplied structures/models and candidate ligands with declared computational models; return ranked or geometric hypotheses whose tested chemical coverage is explicit. |
| [T06](DETAILS.md#t06) | Reaction identities and chemical accounting | Retrieve chemical/reaction identities and calculate explicit atom, electron, carrier and cofactor ledgers under a declared reaction boundary; leave unmeasured driving forces unknown. |
| [T07](DETAILS.md#t07) | Assay-specific kinetic and signal comparisons | Extract matched assay conditions and numeric estimates, calculate declared ratios or bounds, and expose substrate/partner and readout dependencies without relabeling apparent parameters as direct binding or native flux. |
| [T08](DETAILS.md#t08) | Genotype, component and functional-perturbation tables | Represent actual strain/construct/component contrasts and their measured outcomes, preserving the distinction between a perturbation, its validated molecular effect and the endpoint being compared. |
| [T09](DETAILS.md#t09) | RNA and genomic-signal coordinate windows | Read selected deposited signal tracks against the exact reference feature frame and calculate stated local contrasts; keep processed tracks distinct from raw-read reconstruction and transcript-processing evidence distinct from ordinary abundance. |
| [T10](DETAILS.md#t10) | Mass-spectrometric identity and site-table operations | Expose selected published product, peptide or phosphosite identifications and quantify declared table contrasts while preserving analyte/site identity, replicate structure, normalization, censoring and missingness. |
| [T11](DETAILS.md#t11) | Time, population and ecological-outcome tables | Extract outcome trajectories and condition-stratified growth, survival, reporter or competition measurements; calculate declared comparisons at the resolution actually observed. |
| [T12](DETAILS.md#t12) | Regulatory DNA sites, inputs and measured-output correspondence | Compare exact regulatory DNA sequences and mapped promoters, expose motif matches under a supplied model, and retain separate binding, molecular-input/state and transcription-output records. |
| [T13](DETAILS.md#t13) | Compartment, export and membrane-access feature tables | Expose exact sequence/topology features and source-controlled access/orientation readouts so export, processing, physical access and downstream assembly can be compared as distinct measured properties. |

Full entry content: [tool_options.json](tool_options.json).
