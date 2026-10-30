# Full option content

These are research library entries. Illustrative structured values do not replace the current credit schema. Tool contracts marked as specifications are not callable runtime APIs.

## Annotation distinctions for the structured credit form

<a id="a01"></a>
### A01: Direct molecular operation

- **description:** Represent what the target itself does: chemical transformation, binding, translocation or physical energy effect; distinguish a downstream consequence.
- **claim scope:** A specified protein/complex acting on material in a stated preparation and condition; the operation may remain unresolved while a narrower binding claim is retained.
- **distinctions:** 
  - Fold/motif resemblance versus demonstrated operation.
  - Binding versus productive chemical conversion.
  - Target-executed step versus spontaneous or partner-executed consequence.
  - Model-substrate activity versus solved native function.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **operation kind:** 
      - covalent_transformation
      - noncovalent_binding
      - translocation
      - physical_energy_dissipation
      - unresolved
    - **operation owner:** 
      - target
      - other_component
      - unresolved
    - **transformation examples:** 
      - nitrile_reduction
      - phosphorylation
      - decarboxylation
      - model_ester_hydrolysis
    - **binding without demonstrated conversion:** 
      - True
      - False
      - not_assessed
  - **required typed references:** 
    - target_entity_ref
    - material_ref
    - condition_ref
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - A positive assay does not establish primary native role.
  - An incomplete preparation or inappropriate condition does not establish universal inactivity.
  - A downstream product does not identify each enzyme-executed step.
- **follow up lane ids:** 
  - F01
  - F02
  - F03
- **boundary:** A02 specifies material/features selected; A03 specifies how action works; A06 specifies system responsibility. These are independently representable.

Source observations: E-A01-01, E-A01-02, E-A01-03, E-A01-04, E-A01-05 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="a02"></a>
### A02: Molecular target, recognition range and exact feature

- **description:** Represent which substrate, ligand, ion, macromolecule, sequence site or chemical feature is recognized or acted upon, with bounded exclusions and productive versus nonproductive recognition.
- **claim scope:** The operation recipient at warranted resolution: molecule, carrier/polymer context, residue/nucleotide and atom, stereoisomer/anomer or tested panel.
- **distinctions:** 
  - Same operation, different substrate/ligand range.
  - Binding versus productive modification.
  - Free metabolite versus carrier/polymer-bound target.
  - Protein-level activity versus exact residue, nucleotide, atom or stereochemical assignment.
  - Affinity for one target versus discrimination against alternatives.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **target context:** 
      - free_small_molecule
      - protein_site
      - RNA_site
      - DNA_site
      - carrier_bound_metabolite
      - ion
      - unresolved
    - **target relation:** 
      - bound
      - productively_transformed
      - no_detected_activity_under_test
      - unresolved
    - **target resolution:** 
      - molecule
      - polymer_or_carrier
      - residue_or_nucleotide
      - specific_atom_or_stereoisomer
      - unresolved
    - **range statement:** 
      - tested_target_only
      - bounded_tested_panel
      - multiple_tested_targets
      - untested_family_prediction
  - **required typed references:** 
    - target_entity_ref
    - substrate_or_site_ref
    - numbering_or_sequence_ref
    - tested_alternative_refs
    - condition_ref
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - No-detection in a panel is not universal exclusivity.
  - Km, competition IC50 and Kd are different measurements.
  - Protein substrate assignment does not establish every altered phosphosite.
  - Homolog contacts, ligand complexes and best hits alone do not establish native specificity.
- **follow up lane ids:** 
  - F01
  - F03
- **boundary:** This is what is selected. A01 is the operation, A05 the regulatory effect, and A08 native physiological significance. Exact modification sites are explicit here, not buried under a generic activity label.

Source observations: E-A02-01, E-A02-02, E-A02-03, E-A02-04, E-A02-05, E-A02-06, E-A02-07, E-A02-08 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="a03"></a>
### A03: Mode and mechanism of molecular action

- **description:** Represent how an assigned operation is physically or chemically achieved, at the level actually distinguished by evidence.
- **claim scope:** A mechanism proposition attached to an operation/condition: transport mode, reaction direction, intermediate or structural route.
- **distinctions:** 
  - Passive channel versus carrier/active transport.
  - Reduction-capable fold versus direction realized with cellular partners.
  - Structural model versus independently constrained route.
  - Shared broad chemistry versus changed product/intermediate or mechanism.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **mechanism resolution:** 
      - operation_only
      - physical_mode
      - intermediate_or_route
      - detailed_mechanism_unresolved
    - **physical mode examples:** 
      - passive_channel
      - proton_coupled_transport
      - partner_driven_oxidation
      - coupled_redox
    - **mechanism relation:** 
      - directly_discriminated_in_tested_system
      - consistent_model
      - conflicting_models
      - unresolved
    - **reaction direction:** 
      - forward_in_stated_system
      - reverse_in_stated_system
      - both_tested
      - unresolved
  - **required typed references:** 
    - operation_ref
    - mechanism_or_model_ref
    - system_and_condition_ref
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - Static contacts or topology do not establish a complete dynamic cycle.
  - Artificial acceptors do not establish native direction.
  - A homolog mechanism is not automatically the target mechanism.
- **follow up lane ids:** 
  - F01
  - F02
  - F04
- **boundary:** A04 states requirements/consumption; A07 states where materials can meet. Either can constrain a mechanism without proving it.

Source observations: E-A03-01, E-A03-02, E-A03-03, E-A03-04, E-A03-05 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="a04"></a>
### A04: Productive requirements and coupled reaction account

- **description:** Represent cofactors, substrates, electron/nucleotide donors and compatible partners required for productive operation, distinguishing coupled consumption from merely correlated stimulation.
- **claim scope:** A productive reaction or repeated operation in a stated system, keeping incomplete preparation, single event, sustained turnover and coupled readout distinct.
- **distinctions:** 
  - Incomplete preparation versus cofactor-restored activity.
  - Regulatory stimulation versus consumed coupled substrate.
  - Upstream capacity versus downstream partner-admitted specificity.
  - Single event or ATP hydrolysis versus sustained productive operation.
  - Artificial donor substitution versus identified native supply.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **requirement role:** 
      - consumed_substrate
      - electron_donor_or_acceptor
      - catalytic_cofactor
      - compatible_protein_partner
      - regeneration_or_reset_input
      - unresolved
    - **dependency:** 
      - required_under_test
      - rate_or_affinity_modifier
      - dispensable_under_test
      - unresolved
    - **coupled output:** 
      - single_event
      - sustained_turnover
      - multiple_coupled_products
      - unresolved
    - **reaction account:** 
      - measured_stoichiometry_with_bounds
      - conditional_accounting_model
      - incomplete
  - **required typed references:** 
    - reaction_ref
    - required_entity_refs
    - condition_and_preparation_ref
    - measurement_or_stoichiometry_refs
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - Required assay reagent does not identify native partner.
  - Coupled precursor preference is not isolated upstream specificity.
  - Feasibility/balance does not establish native flux or proton translocation.
  - Ideal extrapolated stoichiometry is not a measured uncertain ratio.
- **follow up lane ids:** 
  - F02
  - F03
  - F05
- **boundary:** A03 addresses mechanism. A04 records requirements/accounting. A05 is an input-to-regulatory-effect relation, not inferred merely from a substrate requirement.

Source observations: E-A04-01, E-A04-02, E-A04-03, E-A04-04, E-A04-05, E-A04-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="a05"></a>
### A05: Regulatory input, target and effect

- **description:** Represent which input changes regulator state/abundance, through what route, and which target experiences activation, repression or another effect.
- **claim scope:** A directed relation with input, state, target, sign and condition. Enzyme/protein regulation and transcription are included; occupancy can be recorded without productive control.
- **distinctions:** 
  - Environmental response versus direct sensing, cofactor chemistry, feedback or abundance.
  - Target binding versus productive regulation.
  - Shared DNA-site class versus target-dependent activation/repression.
  - Cofactor occupancy/redox versus total protein.
  - Reversible activity change versus altered transcription/degradation.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **input route:** 
      - direct_ligand_binding
      - cofactor_state_change
      - indirect_metabolic_or_assembly_feedback
      - regulator_abundance_change
      - unresolved
    - **regulated state:** 
      - apo_or_cofactor_ligated
      - oxidation_state
      - allosteric_state
      - abundance
      - unresolved
    - **target relation:** 
      - binding_only
      - activation
      - repression
      - reversible_activity_inhibition
      - unresolved
    - **regulatory level:** 
      - transcription
      - protein_activity
      - protein_turnover
      - unresolved
  - **required typed references:** 
    - input_or_condition_ref
    - regulator_ref
    - state_measurement_ref
    - target_or_promoter_ref
    - output_measurement_ref
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - Motif/footprint does not specify regulatory sign.
  - Ligand-responsive phenotype does not establish direct sensing.
  - Total protein change does not establish per-molecule activity.
  - Assay recovery is not a measured intracellular state trajectory.
- **follow up lane ids:** 
  - F01
  - F03
  - F05
- **boundary:** A02 carries DNA/ligand recognition specificity. A05 carries productive input-to-target effect. A06 may establish regulatory participation without resolving the full relation.

Source observations: E-A05-01, E-A05-02, E-A05-03, E-A05-04, E-A05-05, E-A05-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="a06"></a>
### A06: Contribution within a biological system

- **description:** Represent a target’s specific responsibility in a multi-component process: execution, activation, cofactor supply, assembly, positioning, reset or another bounded contribution.
- **claim scope:** A causal contribution to a named cellular/biochemical system, distinct from whole-system output and association alone.
- **distinctions:** 
  - Required component versus performer of headline chemistry.
  - Enzyme-like fold versus activation of another catalyst.
  - Pairwise binding versus simultaneous scaffolding/productive assembly.
  - ATPase versus reset enabling repeated product formation.
  - A real phenotype versus an unresolved physical connector.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **system contribution:** 
      - direct_product_chemistry
      - activation_of_other_catalyst
      - cofactor_supply
      - assembly_or_target_positioning
      - reset_for_repeated_operation
      - substrate_access
      - RNA_processing_accessory
      - unresolved
    - **contribution resolution:** 
      - association_only
      - defined_component_requirement
      - specific_contribution_discriminated
      - unresolved
    - **catalytic capacity explains system role:** 
      - yes_under_test
      - not_required_for_tested_role
      - not_established
  - **required typed references:** 
    - target_entity_ref
    - system_or_process_ref
    - partner_refs
    - specific_output_ref
    - perturbation_and_control_refs
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - Association/co-migration does not establish direct chemistry or stable membership.
  - A family-site expectation does not prove the target mutant catalytically null.
  - One endpoint does not establish every stage of system operation.
  - Participation can be supported while the connector is unresolved.
- **follow up lane ids:** 
  - F02
  - F03
  - F04
  - F05
- **boundary:** A01 describes direct operation; A06 its system responsibility. A08 gives physiological consequences and A09 necessity given alternatives.

Source observations: E-A06-01, E-A06-02, E-A06-03, E-A06-04, E-A06-05, E-A06-06, E-A06-07 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="a07"></a>
### A07: Spatial access, export and topology

- **description:** Represent which compartment, membrane face or local site target/material can access and which export, topology or targeting feature enables the encounter.
- **claim scope:** A target/material/partner location relation; export, orientation, local concentration, assembly and bulk fractionation remain separate.
- **distinctions:** 
  - Cellular presence versus access to required face.
  - Membrane association versus transmembrane topology.
  - Export versus targeting versus activity.
  - Prediction versus controlled accessibility evidence.
  - Processed substrate versus native assembly compatibility.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **spatial relation:** 
      - same_compartment_access
      - opposite_face_or_sequestered
      - exported
      - locally_targeted
      - membrane_associated_only
      - unresolved
    - **location resolution:** 
      - bulk_fraction
      - compartment
      - membrane_face
      - specific_cellular_site
      - unresolved
    - **access feature:** 
      - export_signal
      - membrane_topology
      - targeting_domain
      - transport_step
      - unresolved
    - **assembly after access:** 
      - observed_under_test
      - not_observed_under_test
      - not_assessed
  - **required typed references:** 
    - target_or_material_ref
    - compartment_or_face_ref
    - feature_and_numbering_ref
    - integrity_or_orientation_control_refs
    - condition_ref
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - Fractionation does not prove integral topology.
  - Inaccessible labeling may reflect burial.
  - Heterologous membrane topology is not automatically native.
  - Processing is not assembly; absent expression is not an assembly-specific negative.
- **follow up lane ids:** 
  - F03
  - F04
- **boundary:** This is spatial opportunity. A01/A03 specify operation/mode, A06 system role, and A09 whether localization is required at the tested expression level.

Source observations: E-A07-01, E-A07-02, E-A07-03, E-A07-04, E-A07-05 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="a08"></a>
### A08: Native physiological contribution and its conditions

- **description:** Represent which cellular/organismal consequence an activity contributes to in biological context, preserving environmental, nutrient, temporal and population conditions.
- **claim scope:** A gene/activity in a stated strain, environment, phase and outcome, with coexisting roles retained; measured capacity need not be dominant native function.
- **distinctions:** 
  - Capacity/induction versus native contribution.
  - Immediate regrowth versus long-term survival or competition.
  - Bulk mean versus population-state distributions.
  - Nutrient use versus detoxification, fitness or protection.
  - Additional conditional role versus erasing prior valid roles.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **physiological contribution examples:** 
      - nutrient_acquisition
      - metabolite_damage_prevention
      - stress_adaptation
      - sustained_starvation_survival
      - competitive_fitness
      - photoprotection
      - unresolved
    - **role relation:** 
      - native_contribution_under_stated_conditions
      - capacity_only
      - additional_conditional_role
      - native_role_unresolved
    - **outcome type:** 
      - growth_rate_or_yield
      - survival
      - competitive_abundance
      - population_state_distribution
      - molecular_homeostasis
    - **effect:** 
      - increases
      - decreases
      - no_detected_effect_in_test
      - heterogeneous_or_tradeoff
      - unresolved
  - **required typed references:** 
    - target_entity_ref
    - strain_and_background_ref
    - environment_and_nutrient_refs
    - time_or_phase_ref
    - population_and_outcome_refs
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - One model/time window is not universal role.
  - Reporter is not flux; population association is not lineage-tracked fate.
  - No early growth defect does not exclude later survival contribution.
  - Side activity/heterologous rescue does not establish primary native flux.
- **follow up lane ids:** 
  - F01
  - F03
  - F05
- **boundary:** A08 gives biological consequence. A06 assigns system responsibility, A09 dependence given alternatives. Shared context fields are scope, not another library slot.

Source observations: E-A08-01, E-A08-02, E-A08-03, E-A08-04, E-A08-05, E-A08-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="a09"></a>
### A09: Conditional necessity, overlap and residual function

- **description:** Represent whether a target is needed for a named outcome under specified conditions and available alternatives: absolute loss, quantitative impairment, hidden overlap or no detected phenotype.
- **claim scope:** Necessity attaches to function, assay and background, not a context-free essential-gene label. It can remain unresolved after deletion failure or overexpression rescue.
- **distinctions:** 
  - Single-gene dispensability versus required combined function.
  - Residual output versus complete tested loss.
  - Supplemented growth versus endogenous supply.
  - Failed deletion recovery versus demonstrated essentiality.
  - No phenotype versus no native contribution.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **necessity:** 
      - required_for_detectable_tested_output
      - required_for_full_tested_output
      - dispensable_with_available_alternative
      - no_detected_defect_in_tested_condition
      - unresolved
    - **alternative relation:** 
      - paralog_overlap
      - distinct_route_overlap
      - medium_or_host_supply
      - suspected_but_unassigned
      - none_tested
    - **residual output:** 
      - detected
      - below_test_detection
      - not_measured
    - **perturbation scope:** 
      - single_component
      - combined_components
      - depletion
      - deletion_not_recovered
  - **required typed references:** 
    - target_entity_ref
    - function_and_outcome_ref
    - background_ref
    - available_alternative_refs
    - medium_or_host_supply_refs
    - assay_and_detection_ref
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - No recovered deletion is not essentiality proof.
  - Negative rescue can reflect expression/stability/compatibility.
  - Residual growth does not identify a backup enzyme.
  - Overlap in one condition does not prove complete equivalence.
- **follow up lane ids:** 
  - F03
  - F04
  - F05
- **boundary:** A09 records dependence given alternatives. A10 identifies what the alternative supplies. Neither rescue nor necessity alone assigns exact chemistry.

Source observations: E-A09-01, E-A09-02, E-A09-03, E-A09-04, E-A09-05, E-A09-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="a10"></a>
### A10: Functional replacement and route equivalence

- **description:** Represent whether an alternative replaces the same reaction, one reference activity, a different route to the same product or demand for the missing function.
- **claim scope:** A reference-function/route relationship with restored outcome, unfilled activities and changed resource demands explicit.
- **distinctions:** 
  - Same product versus same reaction.
  - One activity versus whole multifunctional reference.
  - Catalytic repair versus salvage/demand-reducing suppression.
  - One-condition rescue versus complete native interchangeability.
  - Equivalent product versus changed recycling/donor demands.
- **example structured values:** 
  - **status:** illustrative_only_not_an_adopted_schema
  - **fields:** 
    - **replacement relation:** 
      - same_reaction
      - subset_of_reference_activities
      - different_route_same_output
      - demand_reducing_bypass
      - partial_context_specific_substitution
      - unresolved
    - **restored outcome:** 
      - specified_molecular_product
      - growth_under_test
      - native_process_under_test
      - subset_only
    - **unfilled demand:** 
      - known_remaining_activity
      - new_recycling_requirement
      - remaining_external_supply
      - none_demonstrated
      - unresolved
    - **equivalence scope:** 
      - tested_condition_only
      - multiple_tested_conditions
      - unresolved
  - **required typed references:** 
    - reference_function_or_route_ref
    - alternative_entity_or_route_ref
    - restored_outcome_ref
    - remaining_requirement_refs
    - condition_and_background_ref
    - observation_refs
  - **meaning:** Finite examples of declared values/reference types, not a complete ontology, numerical credit scale, adopted scoring axis or claim of existing runtime compatibility.
- **not established:** 
  - Rescue does not establish the same reaction/all reference activities.
  - No annotated known-family enzyme does not establish absent function.
  - Bookkeeping equivalence depends on stated boundaries/donor assumptions.
  - Heterologous substitution does not establish primary native role.
- **follow up lane ids:** 
  - F02
  - F05
- **boundary:** A09 asks whether an alternative makes a target dispensable; A10 asks what contribution it provides; A04 gives the resulting requirements. This is a relation to annotate, not a prescribed comparison procedure.

Source observations: E-A10-01, E-A10-02, E-A10-03, E-A10-04, E-A10-05 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

## Thought patterns

<a id="p01"></a>
### P01: Choose a relevant analogue and bound what transfers

- **description:** Use similarity to a characterized system to form bounded explanations. Choose which sequence, local structural machinery, domain architecture, genomic context or organismal circumstance makes the reference informative for the disputed property; revise misleading comparators.
- **use when:** A nearest hit, fold, motif or similar biological context suggests an annotation, but exact chemistry, recognition or role remains open.
- **live alternatives:** 
  - A relevant shared relationship supports transfer of the disputed property.
  - Only a partial core is shared; recognition, partners or role differ.
  - The comparator or short match is uninformative for this question.
- **decision guidance:** 
  - Prefer references that separate plausible alternatives, not simply the most familiar name or highest global score. Alignments, structures and context searches are ways to inspect a chosen relationship.
  - When a comparison is weak, consider a biologically better reference before treating it as evidence against all relationship.
  - Keep catalytic compatibility, target recognition and native role as separate transfer claims; absent catalytic machinery can overturn an inherited chemistry.
- **outcome contingencies:** 
  - 
    - **if observed:** Relevant machinery corresponds but specificity differs
    - **then consider:** Retain the supported relationship and investigate the differing recognition or contextual features.
  - 
    - **if observed:** Expected catalytic machinery is incompatible
    - **then consider:** Reopen chemistry and preserve only the relationship actually supported.
  - 
    - **if observed:** No informative correspondence is found
    - **then consider:** Keep function unresolved; absence of an informative match is not absence of function.
- **boundary:** Analogy interpretation is the thought; executing a similarity search is a tool operation. P02 deliberately seeks a counterexample to an explicit predictor; P03 compares rival inputs to a fixed system. Raw scores are not automatically significance.

Source observations: E-P01-01, E-P01-02, E-P01-03, E-P01-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p02"></a>
### P02: Seek cases that break a proposed predictor

- **description:** Treat an implication as something that can fail. Prefer feature/function discordance: feature without function challenges sufficiency; function without feature challenges necessity.
- **use when:** An annotation is extended using a residue, motif, similarity rank, genomic partner or contact as a predictor.
- **live alternatives:** 
  - The feature is sufficient, necessary, both or merely correlated in the relevant domain.
  - Discordance is a real exception.
  - Apparent discordance reflects incomplete measurement or an inapplicable assay.
- **decision guidance:** 
  - Name the feature-to-function implication before selecting a comparison. Seek informative discordance rather than additional concordant relatives.
  - Keep blank genomic fields, assay limits and failed complementation distinct; none can silently become another kind of negative.
  - Compare alternative recognition or contextual explanations after an exception, without treating a post-hoc explanation as a validated replacement rule.
- **outcome contingencies:** 
  - 
    - **if observed:** Feature-positive/function-negative is established
    - **then consider:** Narrow sufficiency without automatically rejecting necessity.
  - 
    - **if observed:** Feature-negative/function-positive is established
    - **then consider:** Narrow necessity while retaining uncertainty about alternative mechanisms.
  - 
    - **if observed:** The supposed negative is unmeasured or inapplicable
    - **then consider:** Retain unresolved status and seek an informative comparator.
- **boundary:** Counterexamples can defeat broad claims without measuring classifier accuracy. P17 additionally requires selective causal perturbations; P02 can use natural relatives or retained system functions.

Source observations: E-P02-01, E-P02-02, E-P02-03, E-P02-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p03"></a>
### P03: Discriminate competing inputs by their predicted chemistry

- **description:** Keep the candidate system explicit while choosing substrates, co-substrates or acceptors that distinguish competing recognition hypotheses. Refine the candidate space using identified products and bounded non-products.
- **use when:** Several chemically plausible inputs remain and another family match will not distinguish them.
- **live alternatives:** 
  - Candidate inputs differ at a recognized chemical feature.
  - A side reaction is being mistaken for the preferred reaction.
  - Apparent specificity belongs to another preparation component or coupled partner.
- **decision guidance:** 
  - Choose contrasts changing the feature on which the hypotheses disagree, including close analogues and plausible pathway inputs.
  - Positives may motivate adjacent candidates omitted from the initial library; unavailable compounds remain untested.
  - Interpret the profile at the level of the assayed preparation with conditions and product identity retained; component attribution may need P06.
- **outcome contingencies:** 
  - 
    - **if observed:** A coherent product pattern supports one recognition hypothesis
    - **then consider:** Narrow the tested profile and choose an informative untested boundary.
  - 
    - **if observed:** An attractive input fails under competent conditions
    - **then consider:** Revise input recognition without discarding every supported catalytic relationship.
  - 
    - **if observed:** Comparative kinetics or products are missing
    - **then consider:** Report bounded capacity rather than rank untested native inputs.
- **boundary:** This chooses a discriminating comparison, not an assay sequence. It does not establish native use (P11) or isolate a component in a coupled system (P06).

Source observations: E-P03-01, E-P03-02, E-P03-03, E-P03-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p04"></a>
### P04: Revise the failed attachment while retaining independent constraints

- **description:** After a competent negative or contradiction, separate the part of the explanation that failed from independently supported constraints. Reopen alternatives within surviving constraints without either preserving the whole annotation or discarding everything.
- **use when:** A reaction or familiar-function assignment fails while pathway placement or another biological association remains supported.
- **live alternatives:** 
  - The reaction was wrong but independent placement survives.
  - The association itself was misleading.
  - The test was not competent to evaluate the proposed function.
- **decision guidance:** 
  - Identify independent support for each part of the old explanation before deciding what survives.
  - Use surviving branch boundaries, required chemistry and distribution to construct a limited alternative set.
  - Preserve association-only wording when no exact replacement reaction is established.
- **outcome contingencies:** 
  - 
    - **if observed:** Reaction fails but independent placement survives
    - **then consider:** Investigate a different compatible transformation.
  - 
    - **if observed:** A new identified product establishes an alternative
    - **then consider:** Replace the failed reaction while retaining unresolved mechanism/native-use questions.
  - 
    - **if observed:** No alternative is established
    - **then consider:** Return the supported association and explicit unresolved claims.
- **boundary:** Nothing survives merely because it was in an old annotation. Failed expression/retrieval is not a negative activity result. P01 handles analogue transfer; P05 begins from a system requirement rather than a failed assignment.

Source observations: E-P04-01, E-P04-02, E-P04-03, E-P04-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p05"></a>
### P05: Constrain missing-function hypotheses by what the system must accomplish

- **description:** Use a supported output or requirement to distinguish loss of function, unfamiliar replacement, different route and changed demand. Evaluate candidate similarities and context against these system explanations.
- **use when:** A familiar enzyme is missing or a required conversion has no assigned protein despite evidence that the output exists or is needed.
- **live alternatives:** 
  - Capability is absent or supplied environmentally.
  - An unfamiliar protein supplies the same contribution.
  - A different route reaches the output or bypasses the requirement.
  - The presumed system requirement is wrong here.
- **decision guidance:** 
  - Specify the required input/output or demand before choosing families.
  - Prefer distribution, domain combinations and context distinguishing explanations, including pathway-negative organisms when available.
  - Allow an alternative to change the reaction boundary; replacement need not copy every activity of the familiar protein.
- **outcome contingencies:** 
  - 
    - **if observed:** Candidate tracks the contribution and functional evidence agrees
    - **then consider:** Support the demonstrated contribution; association alone remains a candidate assignment.
  - 
    - **if observed:** Output persists without the familiar route
    - **then consider:** Retain replacement and bypass alternatives.
  - 
    - **if observed:** Only a missing label or textbook gap exists
    - **then consider:** Keep completion provisional instead of assigning a gene to fill a diagram.
- **boundary:** This is system abduction, not a gene-search task or one-gene-per-step rule. P19 starts from residual output after perturbation; P04 starts from a failed assignment.

Source observations: E-P05-01, E-P05-02, E-P05-03, E-P05-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p06"></a>
### P06: Retain the system output and revise who contributes what

- **description:** Keep a real aggregate output separate from its attribution. Compare direct chemistry, substrate/cofactor supply, enabling a complex, downstream filtering and production of an observable signal.
- **use when:** A mixture, complex or cellular endpoint is being used to assign the intended component a molecular job.
- **live alternatives:** 
  - The nominated component performs the transformation.
  - It enables or supplies another contributor.
  - A partner or contaminant creates/filters the signal.
  - The output is real but its source remains unresolved.
- **decision guidance:** 
  - Choose a comparison separating the live contributor assignments while preserving relevant system competence.
  - Independent preparation, selective partner changes, defined systems or positive structural roles can update attribution; no layout is mandatory.
  - Keep the genuine output after attribution fails, and seek a positive contribution rather than an empty scaffold label.
- **outcome contingencies:** 
  - 
    - **if observed:** Changing a downstream partner changes apparent upstream specificity
    - **then consider:** Bound the result to the coupled pair.
  - 
    - **if observed:** Activity follows an identified host protein instead of the intended construct
    - **then consider:** Reassign the activity while leaving the original candidate unresolved.
  - 
    - **if observed:** Positive evidence separates catalytic and enabling roles
    - **then consider:** Assign bounded distinct contributions; unvalidated catalytic-null labels cannot prove dispensability.
- **boundary:** Attribution is a scientific uncertainty, not routine provenance. It does not choose energy accounts (P10), identify a proxy product (P14) or establish contact necessity (P02/P17).

Source observations: E-P06-01, E-P06-02, E-P06-03, E-P06-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p07"></a>
### P07: Distinguish restoration from bypass, compensation and reduced demand

- **description:** An improved endpoint can repair the proposed molecular relationship, use another route, reduce demand or change downstream consequences. Compare those explanations before treating rescue as mechanistic equivalence.
- **use when:** Complementation, suppressors, adaptive recovery or supplementation improve an endpoint after a focal loss.
- **live alternatives:** 
  - The original molecular contribution is restored.
  - Another route reaches the endpoint.
  - Demand for the contribution is reduced.
  - Only a downstream consequence improves.
- **decision guidance:** 
  - Name the molecular defect rescue is supposed to repair, then seek a comparison separating repair from endpoint compensation.
  - Multi-step bypass, reintroduced lost functions and separate molecular readouts can distinguish the alternatives.
  - Restrict equivalence to the contribution/conditions restored; donor expression does not establish ordinary native role.
- **outcome contingencies:** 
  - 
    - **if observed:** Endpoint recovers while proposed catalytic defect persists
    - **then consider:** Retain compensation or bypass rather than claim molecular repair.
  - 
    - **if observed:** Replacement bypasses several steps or changes cofactor demand
    - **then consider:** Assign the alternative route instead of copying the missing-enzyme name.
  - 
    - **if observed:** Only some outcomes are restored
    - **then consider:** Represent partial/conditional substitution.
- **boundary:** Rescue is the outcome, not the thought pattern. P06 asks who supplies an output; P07 asks what relationship the improving intervention restores. Positive complementation need not identify isolated chemistry.

Source observations: E-P07-01, E-P07-02, E-P07-03, E-P07-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p08"></a>
### P08: Test the missing prerequisite behind conditional function

- **description:** Investigate which enabling resource or molecular state permits a supported capability to matter. Distinguish that prerequisite from correlated stress, altered protein amount and reporter failure.
- **use when:** A preparation is inactive or a gene dispensable in one setting despite evidence for a contribution elsewhere.
- **live alternatives:** 
  - A missing cofactor, partner, nutrient, acceptor or resource context enables the function.
  - The capability is absent or irrelevant.
  - The condition changes abundance, another route or reporter competence instead.
- **decision guidance:** 
  - Choose a motivated prerequisite for which the competing explanations predict different outcomes; arbitrary condition variation is insufficient.
  - Contrast focal genotype/protein state across independently varied prerequisite states with identity and competence controls.
  - A successful addition needs molecular/identity evidence before being called direct catalysis or sensing.
- **outcome contingencies:** 
  - 
    - **if observed:** Independent resource-generating changes alter both resource and genotype-specific benefit
    - **then consider:** Support resource-conditioned contribution.
  - 
    - **if observed:** Cofactor-complete preparation gains identified activity
    - **then consider:** Do not use incomplete preparation as functional falsification; keep native delivery unknown.
  - 
    - **if observed:** Only abundance or reporter competence changes
    - **then consider:** Retain indirect alternatives.
- **boundary:** Resource identity is a biological parameter, not another slot. No wet-lab availability or mandatory experiment is implied. P11 asks whether a capability is used; P12 addresses duration/outcome changes.

Source observations: E-P08-01, E-P08-02, E-P08-03, E-P08-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p09"></a>
### P09: Separate physical access from chemical competence

- **description:** Explain a missing cellular reaction by contrasting inaccessible substrate/partner, absent substrate, failed catalyst and failed reporter delivery. Prefer changes that discriminate the relevant barrier.
- **use when:** Isolated capability disagrees with cellular function or a compartment-specific readout disappears.
- **live alternatives:** 
  - Catalyst is competent but cannot contact its substrate/partner.
  - Substrate is missing or sequestered on the wrong side.
  - Reporter fails to reach/detect available substrate.
  - Catalyst itself is defective.
- **decision guidance:** 
  - Name the barrier and entities whose contact is disputed; fractionation alone cannot settle it.
  - Different barriers/targeting regions are separate alternatives; global disruption does not identify every native route.
  - Relocation or targeting contrasts can test whether partner/compartment access changes the supported outcome.
- **outcome contingencies:** 
  - 
    - **if observed:** Removing one barrier fails but exposing across another restores the readout
    - **then consider:** Narrow the access explanation while retaining reporter controls.
  - 
    - **if observed:** Export/cleavage succeeds but native output fails
    - **then consider:** Only upstream access is established; downstream compatibility can become P15.
  - 
    - **if observed:** Only prediction or growth is available
    - **then consider:** Keep access provisional; neither establishes direct flux or orientation.
- **boundary:** This is not a topology-prediction task and does not infer transport from membrane association. Access and chemical transformation remain different relations.

Source observations: E-P09-01, E-P09-02, E-P09-03, E-P09-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p10"></a>
### P10: Account for the coupled chemical system

- **description:** Choose an explicit account of matter, electrons, cofactors and energy needed for a conversion. Reopen incomplete boundaries when an isolated reaction is implausible or replacement changes metabolic demand.
- **use when:** Output conflicts with a redox/stoichiometric account, or routes with the same product may require different support.
- **live alternatives:** 
  - A consumed partner or favorable coupled reaction is missing.
  - Partial uncoupling or another conversion alters the account.
  - Same output hides changed input/cofactor recycling demand.
  - Chemistry remains unsupported under stated assumptions.
- **decision guidance:** 
  - Choose the boundary and track relevant atoms/electrons/cofactors before calculating.
  - Kinetic activation does not supply missing thermodynamic driving force.
  - Keep measured balances distinct from ideal fully coupled ratios and preserve unknown potentials/recovery.
  - Use route-specific demands to identify which biological comparison distinguishes apparent output equivalence.
- **outcome contingencies:** 
  - 
    - **if observed:** A coupled account resolves the isolated energy deficit
    - **then consider:** Retain feasibility under assumptions; occurrence requires separate evidence (P11).
  - 
    - **if observed:** Measured ratio differs from the ideal
    - **then consider:** Preserve measurement and consider uncoupling/incomplete recovery.
  - 
    - **if observed:** Replacement changes a recycled product/cofactor
    - **then consider:** Expose the changed demand instead of asserting full interchangeability.
- **boundary:** The episode chooses the account; arithmetic tools do not choose coupled chemistry. Standard-potential feasibility is not cellular free energy or native flux. No credit weights are supplied.

Source observations: E-P10-01, E-P10-02, E-P10-03, E-P10-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p11"></a>
### P11: Distinguish a possible route from the route actually used

- **description:** Keep feasibility or measured capacity separate from native use. Contrast ordinary use, conditional backup, side activity and unused capacity without forcing a single-role explanation.
- **use when:** A reaction, model, structure or environmental gene detection is being promoted to main native role or actual flux.
- **live alternatives:** 
  - Capacity supplies the proposed native contribution.
  - It supplies a conditional backup/secondary role.
  - It is side activity or possible chemistry without demonstrated use.
  - Another route supplies the native output.
- **decision guidance:** 
  - Select observations with different expected consequences for native use and mere capacity: endogenous products, demand-specific perturbations or competing routes.
  - Retain genuine earlier side activity when a better native role appears; compatible conditional roles need not be exclusive.
  - Compare plausible exposure/kinetics without inventing concentrations or native substrates.
- **outcome contingencies:** 
  - 
    - **if observed:** Independent native observations agree
    - **then consider:** Support use under those conditions, not total flux or exclusivity.
  - 
    - **if observed:** Only overexpression/high-dose/artificial activity is positive
    - **then consider:** Retain bounded capacity with ordinary responsibility unresolved.
  - 
    - **if observed:** A stronger native explanation is established
    - **then consider:** Revise priority/scope without deleting genuine prior chemistry.
- **boundary:** This supplies a discriminating question, not an acceptance gate. P08 tests prerequisites and P10 feasibility; a stronger library label cannot replace native evidence.

Source observations: E-P11-01, E-P11-02, E-P11-03, E-P11-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p12"></a>
### P12: Compare biological consequences over the time that matters

- **description:** Choose time/phase contrasts distinguishing transient acceleration, repeated function, adaptation and survival. An early benefit or first product need not predict later outcomes.
- **use when:** Interpretation depends on when an effect appears, how long function is needed or whether operation must repeat.
- **live alternatives:** 
  - Effect is durably beneficial.
  - Early acceleration carries a later maintenance/survival cost.
  - First event succeeds but repeated operation fails.
  - Original observation window missed the relevant phase.
- **decision guidance:** 
  - Choose intervals from biological alternatives rather than a universal cadence.
  - Keep lag, growth, viability and repeated turnover as distinct outcomes.
  - Preserve differing early/late conclusions and investigate explanations that predict both.
- **outcome contingencies:** 
  - 
    - **if observed:** Recovery improves but later survival falls
    - **then consider:** Represent both outcomes in their windows.
  - 
    - **if observed:** One product forms but repeated turnover fails
    - **then consider:** Narrow the missing contribution toward sustained operation.
  - 
    - **if observed:** A later phase exposes a phenotype
    - **then consider:** Restrict the early nonphenotype without pretending it observed the later result.
- **boundary:** Timing is always metadata; this pattern makes temporal explanation the scientific competition. It supplies no execution timers or stopping rule. P08 concerns prerequisites rather than duration alone.

Source observations: E-P12-01, E-P12-02, E-P12-03, E-P12-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p13"></a>
### P13: Resolve an aggregate claim at the biological level that separates explanations

- **description:** Ask whether pooled change reflects uniform effects, selective subsets or changed mixtures. Choose biologically meaningful units whose contrasts separate those explanations.
- **use when:** A population, protein or process label pools outcomes with potentially different biological meanings.
- **live alternatives:** 
  - Units change similarly.
  - A subset changes while others retain function.
  - Mixture/baseline changes rather than each unit’s response.
  - Missing/censored/differently normalized measurements leave quantification open.
- **decision guidance:** 
  - Choose resolution from the competing biological explanations, not just because finer data exist.
  - Compare affected/retained units while preserving baseline versus response and readout definition.
  - When needed resolution was not measured, qualify the aggregate claim rather than impute cell fates, occupancy or missing values.
- **outcome contingencies:** 
  - 
    - **if observed:** Retained units contradict uniform loss
    - **then consider:** Bound dependence to the affected subset.
  - 
    - **if observed:** Distributions differ beyond a simple average shift
    - **then consider:** Retain heterogeneous-state explanations; fate needs independent evidence.
  - 
    - **if observed:** Site/condition records do not support pooling
    - **then consider:** Return separate records; missing ratios are not zero abundance.
- **boundary:** Record identity/normalization is always required. This pattern is selected when biological heterogeneity changes the explanation; a changed phosphosite does not establish direct catalysis.

Source observations: E-P13-01, E-P13-02, E-P13-03, E-P13-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p14"></a>
### P14: Distinguish the transformation from its proxy readout

- **description:** Treat bands, cofactor changes, substrate loss and downstream signals as compatible with several transformations. Prefer evidence separating intended chemistry from half-reactions, spontaneous conversion or artifacts.
- **use when:** A proxy is naming a reaction without establishing what actually changed.
- **live alternatives:** 
  - Proxy reflects identified intended product.
  - A half-reaction/alternative creates the same proxy.
  - A spontaneous downstream step follows different enzyme chemistry.
  - Disappearance/migration changes without productive conversion.
- **decision guidance:** 
  - Name rival transformations before selecting product, labeling, temporal or chemical-competence evidence.
  - Keep genuine partial chemistry when full product is absent.
  - Structural plausibility can guide discrimination but cannot identify the chemistry alone.
- **outcome contingencies:** 
  - 
    - **if observed:** Identified products/labeled atoms distinguish the event
    - **then consider:** Assign that transformation at tested scope.
  - 
    - **if observed:** Proxy persists without expected product
    - **then consider:** Reopen partial/alternative chemistry.
  - 
    - **if observed:** Only disappearance or band shift is observed
    - **then consider:** Record it specifically; productive synthesis stays open.
- **boundary:** P14 asks what occurred; P06 asks who caused an established output. It is not routine record validation and does not assume new experiments are available.

Source observations: E-P14-01, E-P14-02, E-P14-03, E-P14-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p15"></a>
### P15: Hold upstream success while investigating downstream failure

- **description:** Preserve demonstrated recognition, binding, cleavage or delivery when productive output fails. Compare the additional compatibility or coupling explanations rather than repeat upstream positives.
- **use when:** Binding/processing is being treated as sufficient for catalysis, assembly, regulation or organismal output.
- **live alternatives:** 
  - Upstream engagement is sufficient here.
  - Another structural/chemical/partner constraint blocks progression.
  - Upstream readout differs or was misidentified.
  - Downstream measurement is incompetent.
- **decision guidance:** 
  - Seek contrasts with upstream competence but differing downstream outcomes.
  - Separate unexpressed constructs from expressed/processed variants.
  - If progression remains unexplained, return separated outcomes instead of inventing a mechanism.
- **outcome contingencies:** 
  - 
    - **if observed:** Both substrates bind but only one converts
    - **then consider:** Narrow productive recognition beyond binding.
  - 
    - **if observed:** Expressed processed variant fails assembly
    - **then consider:** Support an additional compatibility requirement without assigning its mechanism.
  - 
    - **if observed:** Only upstream event is known
    - **then consider:** Leave final role unresolved.
- **boundary:** No recognize→process→assemble itinerary follows; inquiry can start at the failed endpoint. P17 tests a selectively perturbed required relation; P15 can preserve a downstream unknown without causal isolation.

Source observations: E-P15-01, E-P15-02, E-P15-03, E-P15-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p16"></a>
### P16: Distinguish direct input action from indirect response and feedback

- **description:** Environmental responses can arise through direct ligand recognition, cofactor chemistry, changed abundance or system-demand feedback. Choose contrasts distinguishing those routes before assigning a direct sensor or regulatory sign.
- **use when:** Induction, binding or physiology is being treated as proof of direct signal recognition.
- **live alternatives:** 
  - Input binds the regulator.
  - Input changes a cofactor/state without selective ligand binding.
  - Partner demand/feedback mediates the response.
  - Abundance or another regulator explains it.
- **decision guidance:** 
  - Keep signal, molecular state, amount, DNA recognition and productive regulation distinct.
  - Choose contrasts controlling the relevant alternatives, including target classes and feedback demand.
  - Direct binding addresses recognition; promoter binding alone proves neither signal binding nor transcriptional sign.
- **outcome contingencies:** 
  - 
    - **if observed:** Purified protein binds input with informative controls
    - **then consider:** Support assay-specific binding without claiming the whole native mechanism.
  - 
    - **if observed:** State controls distinguish cofactor chemistry from feedback
    - **then consider:** Retain compatible supported routes; do not call a chemical input a selective ligand.
  - 
    - **if observed:** Response is known but direct action untested
    - **then consider:** Report response with sensing route unresolved.
- **boundary:** This concerns input-to-response explanations rather than general attribution. Motif scanning does not predict regulatory sign; not every regulator must be a direct metabolite sensor.

Source observations: E-P16-01, E-P16-02, E-P16-03, E-P16-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p17"></a>
### P17: Separate linked functions through selective dissociation

- **description:** Seek comparisons preserving one property while changing another. Use their dissociation to distinguish a required functional relation from amount, delivery, stability or another linked activity.
- **use when:** A mutant phenotype is assigned to one molecular function despite several potentially affected properties.
- **live alternatives:** 
  - Named function is required.
  - Amount/localization/assembly/another function explains the effect.
  - Distinct connections jointly contribute but can reside on different molecules.
  - The measured activity and native role dissociate.
- **decision guidance:** 
  - Prefer positive evidence that alternative properties survive; a failed construct is not automatically selective.
  - Reciprocal/complementary contrasts are informative when their predicted results differ, without requiring them universally.
  - Keep incomplete perturbation validation as a limit rather than claiming a specific null from its label.
- **outcome contingencies:** 
  - 
    - **if observed:** Function fails despite retained amount/delivery
    - **then consider:** Exclude simple instability/mislocalization without inventing direct binding.
  - 
    - **if observed:** Complementary defects restore function but same-defect controls do not
    - **then consider:** Support joint contribution of distinct connections.
  - 
    - **if observed:** Endpoint survives a supposed catalytic-null mutation without null validation
    - **then consider:** Do not infer catalytic dispensability from the label.
- **boundary:** This is an inference pattern, not mutagenesis instructions. P02 tests predictors and can use natural variation; P17 adds causal perturbation selectivity. Ordinary suppressors are not reciprocal separation-of-function evidence.

Source observations: E-P17-01, E-P17-02, E-P17-03, E-P17-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p18"></a>
### P18: Reconcile conflict by testing scope-specific explanations

- **description:** Compare apparently conflicting claims without choosing a paper or averaging them. Ask whether a tested difference in organism, state, assay window, relation or construct explains disagreement; preserve unresolved conflict where no discriminating match exists.
- **use when:** Studies or assays appear to support incompatible assignments or dependencies.
- **live alternatives:** 
  - Results genuinely conflict under comparable conditions.
  - Both hold in different states/organisms/windows.
  - A proxy has been given a stronger interpretation.
  - A specific construct or record error explains a result.
- **decision guidance:** 
  - State the contradictory relation and the matching conditions needed for a true contradiction.
  - Seek evidence testing the proposed explanation, not just metadata differences.
  - Plausible scope differences are not resolutions until a discriminating comparison exists.
- **outcome contingencies:** 
  - 
    - **if observed:** A corrected construct/condition is linked to the discrepancy
    - **then consider:** Revise only the interpretation supported by the correction.
  - 
    - **if observed:** Scope explanation remains untested
    - **then consider:** Retain conflict and the missing comparison.
  - 
    - **if observed:** Records concern different outputs/phases
    - **then consider:** Restrict claims without calling them equivalent replications.
- **boundary:** Provenance is always required; P18 is selected when explaining conflict is the scientific problem. No rewriting observations or saved credit is authorized.

Source observations: E-P18-01, E-P18-02, E-P18-03, E-P18-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="p19"></a>
### P19: Investigate the route behind residual function

- **description:** Preserve reproducible output after a focal loss while distinguishing another contributor from incomplete perturbation, imported product or reduced demand. Revise exclusivity without erasing the lost route’s genuine contribution.
- **use when:** Knockout/depletion leaves growth, product or activity unaccounted for by the current explanation.
- **live alternatives:** 
  - Another contributor supplies residual output.
  - Perturbation is incomplete or a suppressor restores original activity.
  - Environmental supply or bypass reduces demand.
  - Residual readout is an artifact or different output.
- **decision guidance:** 
  - Choose a contrast within the residual-function background separating an alternative contributor from remaining original activity or supply.
  - Restoration/independent activity can clarify attribution without settling every native route/cofactor.
  - Combined perturbations are recorded evidence or candidate work, not an automatic requirement for new experiments.
- **outcome contingencies:** 
  - 
    - **if observed:** Additional loss removes residual output and restoration recovers it
    - **then consider:** Support overlap at measured scope, not universal exclusivity.
  - 
    - **if observed:** Output depends on supply or unremoved activity
    - **then consider:** Restrict redundancy to the actual bypass/perturbation.
  - 
    - **if observed:** Residual route cannot be assigned
    - **then consider:** Return retained function with its source unknown.
- **boundary:** P05 starts from a missing assignment, P07 asks what rescue restores, and P19 starts from output that never disappeared. Combined-gene evidence does not isolate every member.

Source observations: E-P19-01, E-P19-02, E-P19-03, E-P19-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

## Tools

<a id="t01"></a>
### T01: Primary-source and retained-material access

- **description:** Retrieve identified publications and advertised supplements, expose exact source windows, and extract selected tables or images while preserving source identity and inspection scope.
- **capability operations:** 
  - 
    - **operation:** Search a publication collection
    - **inputs:** 
      - **literal query:** string; chosen Europe PMC syntax
      - **page:** size plus cursor
    - **outputs:** 
      - **records:** source IDs, titles, metadata and continuation; no scientific conclusion
    - **implementation status:** repository_catalog_defined
    - **confirmed repository callables:** 
      - public.literature.search
    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Acquire a selected article or advertised supplement
    - **inputs:** 
      - **pmcid:** actual PMC identifier
      - **version or asset ref:** identifier returned by the corresponding listing
    - **outputs:** 
      - **source:** retained original bytes, representation identity and digest
      - **projection:** ordered article text where available; may omit XML tables
    - **implementation status:** repository_catalog_defined
    - **confirmed repository callables:** 
      - public.literature.read
      - public.pmc.versions
      - public.pmc.files
      - public.pmc.asset
    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Expose a selected source representation
    - **inputs:** 
      - **source ref:** registered source
      - **selection:** UTF-8 byte window, physical PDF page, image frame, archive member, or XLSX sheet and row window
    - **outputs:** 
      - **material:** exact selected text, pixels, rows or member bytes
      - **provenance:** original coordinates and representation-specific identity; formulas and cached values distinguished
    - **implementation status:** repository_catalog_defined
    - **confirmed repository callables:** 
      - source.read
      - source.pdf.info
      - source.pdf.text
      - source.pdf.page
      - image.view
      - source.archive.members
      - source.archive.extract
      - source.xlsx.sheets
      - source.xlsx.rows
    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - gene_annotation_episode/tools.py:ToolRegistry.catalog; gene_annotation_episode/knowledge/index.json entries publication-access and source-reading
  - **research operations performed:** 
    - All 142 case groups have an explicit source-inspection scope in case_records.json; 134 relevant-primary-section groups and 8 abstract/summary groups. Specific JSON/XML/PDF/XLSX reads are retained in the corpus; they were not all calls through the repository registry.
  - **capability specifications not confirmed as repository callables:** 
    - A dedicated source-local scientific passage-ranking tool and dedicated XML-table API were not found in the inspected catalog; existing source windows remain available.
  - **author experiments are source evidence only:** 
    - All reported biological experiments remain author work; downloading and viewing their records does not repeat them.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - An access failure or projection omission is not biological absence.
  - A publication, its XML, PDF and supplement can represent the same observation; access does not create independent evidence.
  - PDF extraction has no confirmed OCR in the inspected manual; viewing pixels is separate from rendering.
- **observed uses:** 
  - 
    - **case group:** context_oarx_thiamin_2024
    - **use:** Actual XLSX and EMBL retrieval exposed 87 OarX rows, 22 FmnO entries and 65 blanks; row/strain identities remained separate.
    - **execution scope:** Read-only retained-source parsing; no new comparative-genome search or assay.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** cellular_yhcB
    - **use:** Actual supplement-row extraction distinguished negative rodZ/mrcB transposon fitness from positive fabF and selected suppressor candidates.
    - **execution scope:** Processed published rows, not new fitness experiments or raw-read reanalysis.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** yeag
    - **use:** The 2021 supplementary workbook retained individual phosphosite ratios, missing values and replicate identities that the article summary did not expose.
    - **execution scope:** Six selected source rows were parsed; not a complete raw-MS replication.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** BC0371_Song_2007
    - **use:** Primary abstract and deposited 2P88 identity permitted only a bounded account of modeling/assay convergence.
    - **execution scope:** Complete primary Methods/Results not inspected; no serial dependence between docking and assays invented.
    - **use status:** research_read_only_operation_performed

Source observations: E-T01-01, E-T01-02, E-T01-03, E-T01-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t02"></a>
### T02: Protein sequence matches and local sequence features

- **description:** Retrieve exact protein sequences, compare selected homologs or database matches, and expose domain/local-residue differences without converting similarity into substrate, orthology or native-role assignments.
- **capability operations:** 
  - 
    - **operation:** Retrieve a selected sequence or reference page
    - **inputs:** 
      - **query or accession:** literal UniProt query/accession or selected NCBI protein/nuccore accession
      - **interval:** optional explicitly selected nucleotide interval
    - **outputs:** 
      - **reference:** source-bound sequence, native annotation assertions, features and acquisition metadata
    - **implementation status:** repository_catalog_defined
    - **confirmed repository callables:** 
      - public.uniprot.search
      - public.uniprot.record
      - public.ncbi.search
      - public.ncbi.sequence
    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Run an explicitly selected sequence comparison
    - **inputs:** 
      - **query reference:** two actual registered sequence operands
      - **molecule mode:** Select molecule=protein|dna|rna and mode=local|global using the actual sequence.align schema; these fields do not apply automatically to other callables.
    - **outputs:** 
      - **alignment:** native alignment and score with separate operand coordinates
      - **selected sites:** substitutions, gaps, insertions and unexamined positions
    - **implementation status:** repository_catalog_defined
    - **confirmed repository callables:** 
      - sequence.align
      - sequence.sites
    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Search a selected protein reference collection
    - **inputs:** 
      - **query:** actual protein operand
      - **search model:** Choose one advertised callable/program/database combination and its exact schema; HMMER phmmer/hmmscan and BLAST programs do not share one interchangeable parameter set.
    - **outputs:** 
      - **hits:** native hit/domain/HSP rows and search identity; not assigned functions
    - **implementation status:** repository_catalog_defined
    - **confirmed repository callables:** 
      - public.hmmer.databases
      - public.hmmer.search
      - public.hmmer.collect
      - public.hmmer.page
      - public.blast.search
      - public.blast.collect
    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Inspect a declared local sequence rule
    - **inputs:** 
      - **sequences:** identified sequences/alignment
      - **rule:** explicit motif or position correspondence and coordinate convention
    - **outputs:** 
      - **observations:** exact match/nonmatch sites, lengths and gaps; no learned biological specificity rule
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - gene_annotation_episode/tools.py:catalog definitions for sequence.align/sites, public.uniprot.*, public.ncbi.*, public.hmmer.*, public.blast.*; detached homology.* implementation is separately caller bound
  - **research operations performed:** 
    - sequence/hemk-homology-reference-sequences-20261021.json, hemk-pairwise-comparisons.json and hemk-prmb-proteome-comparison.json: fresh source sequences, motif checks, pairwise comparisons and local proteome score search; no BLAST E-values computed.
  - **capability specifications not confirmed as repository callables:** 
    - A generally registered multiple-sequence-alignment, phylogenetic-tree builder or learned specificity classifier was not confirmed by this catalog inspection.
  - **author experiments are source evidence only:** 
    - Protein substrate screens and variant complementation in the examples are published evidence, not executable operations supplied here.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - A best match, conserved catalytic motif or high global identity does not identify exclusive substrates.
  - A custom local score search has its actual score model and database scope; do not label its scores BLAST statistics.
  - Negative complementation is not automatically absence of purified activity.
- **observed uses:** 
  - 
    - **case group:** hemk_prmc
    - **use:** Actual PrmB/HemK versus DNA-methyltransferase sequence comparisons showed why a shared NPPY feature does not select a nucleic-acid substrate.
    - **execution scope:** Retained read-only comparisons with published outcomes known; no new enzyme assay.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** seq_hisn_impase_discrimination
    - **use:** Reported motif 5 and experimentally tested homologs separated HisN-like activity better than overall similarity.
    - **execution scope:** Author sequence analysis and complementation; our later selected-table arithmetic is not a new classifier benchmark.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** seq_triA_atzA_near_identity
    - **use:** Nine differences among 475 residues coexist with distinct tested deamination/dechlorination profiles.
    - **execution scope:** Author substrate panels, not a universally sufficient nine-residue specificity rule.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** seq_yadB_gluQRS_ecoli
    - **use:** Missing anticodon-binding architecture constrained transfer from GluRS to YadB.
    - **execution scope:** Exact Q34 substrate modification came from author matched-tRNA assays, not sequence comparison.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** pa0142
    - **use:** A guanine-deaminase-related subgroup with altered pocket residues motivated candidate selection.
    - **execution scope:** Authors validated 8-oxoguanine chemistry; the structure was a homolog, not PA0142.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T02-01, E-T02-02, E-T02-03, E-T02-04, E-T02-05 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t03"></a>
### T03: Comparative gene neighborhoods, fusions and presence profiles

- **description:** Expose gene-order, strand, fusion and component-presence observations across explicitly selected genomes and proteins; count only defined records and retain unknown or incomplete context.
- **capability operations:** 
  - 
    - **operation:** Acquire and inspect selected genome features
    - **inputs:** 
      - **reference accession:** exact NCBI nucleotide record
      - **selector:** locus tag, protein ID or coordinate with coordinate frame
      - **window:** explicit left/right base span
    - **outputs:** 
      - **features:** native labels, coordinates, strands and partial-boundary markers; source assertions preserved
    - **implementation status:** repository_catalog_defined
    - **confirmed repository callables:** 
      - public.ncbi.sequence
      - reference.neighborhood
      - material.annotations
    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Tabulate selected component profiles
    - **inputs:** 
      - **rows:** explicit organism/genome identities
      - **components:** declared genes/domains/fusions
      - **cells:** reported or search-derived presence/absence/unknown with method and completeness
    - **outputs:** 
      - **matrix:** source-bound component profile
      - **counts:** selected-row counts and intersections; unknown not coerced to absent
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Build a new comparative profile or gene tree
    - **inputs:** 
      - **proteins genomes:** chosen versions and organism sampling
      - **homology model:** specified search/domain rule
      - **tree model:** explicit alignment, substitution and support settings if used
    - **outputs:** 
      - **candidate profile:** matches and unresolved cases
      - **candidate tree:** topology and support with exact method
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - gene_annotation_episode/tools.py:reference.neighborhood, public.ncbi.sequence and material.annotations definitions
  - **research operations performed:** 
    - context/oarx-profile-probe.json and oarx_actual_routes.json: exact published component rows and CP022614.1 CDS/regulatory coordinates inspected; no full phylogenetic reconstruction.
    - chemistry/raw/bcd_genome_probe_summary.json: published subunit identities checked against a current genome record; supports identity, not a second biochemical causal route.
  - **capability specifications not confirmed as repository callables:** 
    - New cross-genome profile assembly, fusion detection and phylogenetic inference need explicit data and implementations; the catalog does not establish a turnkey comparative-genomics agent.
  - **author experiments are source evidence only:** 
    - Knockout growth, product reconstitution and substrate tests used to validate profile suggestions are author experiments.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - Blank source cells can be unknown; native missing genes require the actual search/completeness scope.
  - Gene adjacency supports association, not the specific catalytic reaction, donor, order or universal requirement.
  - Source taxon/strain and experimental strain must retain separate identities.
- **observed uses:** 
  - 
    - **case group:** context_oarx_thiamin_2024
    - **use:** The actual OarX/FmnO profile and selected neighborhoods limited a universal paired-enzyme hypothesis.
    - **execution scope:** 87 published rows were counted; no de-novo genome survey or native activity assignment.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** context_archaeal_shikimate_kinase_2001
    - **use:** Cross-organism neighborhoods separated two GHMP-like paralogs and pathway-bearing from pathway-lacking comparisons.
    - **execution scope:** Authors genome analysis; historical WIT IDs retained without invented modern mappings.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** context_poxa_yjek_efp_2010_2011
    - **use:** EF-P residue/component distribution and paralog neighborhoods tied YjeK to EF-P modification rather than the catabolic LAM partner.
    - **execution scope:** Context did not decide the two possible chemical orders; later author substrate tests did.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** replacement_queH
    - **use:** Inverse QueG/DUF208 distribution, pathway neighborhoods and QueA fusions exposed replacement candidates.
    - **execution scope:** Published comparative profiles and cellular rescue; purified productive QueH reaction remained unestablished.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** context_bioy_optional_module_2007
    - **use:** Only a subset of BioY neighborhoods link BioMN, motivating optional-module distinctions.
    - **execution scope:** Authors transport kinetics, not module counts, established affinity effects.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** yjef_nnr
    - **use:** Fusion related the epimerase and dehydratase problem but did not transfer the ATP donor from eukaryotic homologs.
    - **execution scope:** The ADP dependence was author biochemical evidence, not an implication of fusion.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T03-01, E-T03-02, E-T03-03, E-T03-04, E-T03-05, E-T03-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t04"></a>
### T04: Deposited structure identities, ligands and contact geometry

- **description:** Retrieve exact deposited structures and metadata, map native chains/residues/ligands, and calculate declared geometric contacts without treating a static model as activity or physiological proof.
- **capability operations:** 
  - 
    - **operation:** Retrieve a selected structure record and coordinates
    - **inputs:** 
      - **entry:** exact PDB accession
      - **representation:** entry/entity/ligand metadata or specific coordinate file and assembly
    - **outputs:** 
      - **record:** deposited identities, source numbering, ligand labels and file digest
      - **coordinates:** selected model/assembly atom coordinates
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Extract annotated contacts or compute declared distances
    - **inputs:** 
      - **structure:** identified coordinate or PDBe contact record
      - **atom selection:** explicit model, chains, residue numbers, atom groups and symmetry policy
      - **metric:** specified Euclidean distance/contact cutoff
    - **outputs:** 
      - **pairs:** atom/residue pairs and distances with coordinate provenance
      - **coverage:** selected atoms and missing residues; not energetic or binding inference
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - No dedicated PDB/PDBe retrieval or coordinate-distance callable was confirmed in the inspected repository catalog.
  - **research operations performed:** 
    - causal/cas2/raw/coordinate_comparisons.json and analyze_coordinates.py: actual 5DS4/5DS5 nearest-heavy-atom calculations with Biopython 1.88.
    - structure TM0936/MJ0577 traces: actual PDBe binding-site records.
    - replacement/raw/7LC5-coordinate-probe.json and causal EnvC traces: current deposited identities/ligands and selected coordinate relationships inspected.
  - **capability specifications not confirmed as repository callables:** 
    - General structure retrieval and geometry are capability specifications for runtime integration; retained scripts do not create registered episode callables.
  - **author experiments are source evidence only:** 
    - Crystallography, cryo-EM, mutagenesis and binding assays belong to the cited authors.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - PDB entry labels can differ from manuscript mappings; preserve actual files and discrepancies.
  - Close contact does not prove necessity, affinity, chemistry or physiological encounter.
  - A homolog structure is not the target structure; modeled ligand identity is not necessarily an identified metabolite.
- **observed uses:** 
  - 
    - **case group:** causal_cas2_spacer_acquisition
    - **use:** Actual donor-DNA and Cas1 interface distances separated Cas2 R16/R78, R18 and E9 geometry while preserving E9 proximity to some DNA.
    - **execution scope:** Static related deposited models; no catalytic-null proof, new binding assay or energetic inference.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** TM0936_Hermann_2007
    - **use:** Actual PDBe 1P1M/2PLM and 1K70 records exposed metal and ligand-contact sets used for a bounded comparison.
    - **execution scope:** Record comparison, not an independently computed sequence alignment or fresh docking.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** MJ0577_Zarembinski_1998
    - **use:** Actual1MJH contact records confirmed bound ATP contacts while authors found no appreciable ATPase activity without extract.
    - **execution scope:** Contact does not identify the unknown activating component or prove standalone ATPase.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** causal_envC_activation
    - **use:** Actual deposited ligand records and source Table 1 checks separated a LytM-like fold from its missing catalytic Zn and retained localized defective variants.
    - **execution scope:** The structure contains K; no-Zn must not be misstated as no-metal; no fresh alignment or binding assay.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** replacement_queH
    - **use:** The 7LC5 probe localized metal-associated features without converting oQ disappearance into a demonstrated Q product.
    - **execution scope:** No productive purified reaction, cofactor assignment or raw-spectrum reanalysis newly established.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** spec_frsa_disputed_pdc_native_unknown
    - **use:** A nearly identical fold and uncertain bound density did not resolve disputed decarboxylation or native substrate.
    - **execution scope:** Ligand modeled as hexanoate remained uncertain; later surrogate esterase assays did not establish native substrate.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T04-01, E-T04-02, E-T04-03, E-T04-04, E-T04-05, E-T04-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t05"></a>
### T05: Fold, pocket and candidate-ligand model comparisons

- **description:** Compare supplied structures/models and candidate ligands with declared computational models; return ranked or geometric hypotheses whose tested chemical coverage is explicit.
- **capability operations:** 
  - 
    - **operation:** Search or superpose selected folds and local pockets
    - **inputs:** 
      - **query structure:** identified experimental structure or explicitly labeled model
      - **reference collection:** chosen structures and release
      - **method:** named structural alignment/local pocket model and parameters
    - **outputs:** 
      - **matches:** ranked structural matches, aligned residues and coverage
      - **geometry:** superposition or local-site differences with confidence limits
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Score declared ligand candidates in explicit model states
    - **inputs:** 
      - **receptor:** selected structure/model, protonation, metal/cofactor and loop states
      - **ligands:** enumerated chemical identities/stereoisomers and preparation
      - **scoring model:** named docking/conformational method and parameters
    - **outputs:** 
      - **poses:** candidate poses and model-dependent scores
      - **search scope:** included and excluded chemical classes; failed preparations retained
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - No executable DALI, Foldseek, structural-superposition, receptor-modeling or docking callable was confirmed in the inspected repository catalog.
  - **research operations performed:** 
    - Primary authors computational results were inspected. No fresh fold search, homology model, docking, molecular dynamics or structure refinement was run in this 142-group research.
  - **capability specifications not confirmed as repository callables:** 
    - All operations in this option require an explicitly supplied implementation and resource/data binding before execution.
  - **author experiments are source evidence only:** 
    - Ligand-bound crystallography and biochemical substrate panels remain source evidence, not provided assays.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - A score ranks the submitted chemical library under a model; missing compounds were not tested and scores are not activity probabilities.
  - Changing loops, receptor state or a metal model changes the computational hypothesis.
  - Fold similarity may yield no useful function distinction; model agreement does not replace native-role evidence.
- **observed uses:** 
  - 
    - **case group:** Arad3529_Fan_2013
    - **use:** Authors remodeled two loops and changed substrate candidates before validating pterin deamination.
    - **execution scope:** No fresh model/docking here; full substrate profile not independently reproduced.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** Lmo2620_Bh0225_Xiang_2012
    - **use:** A second phosphate-binding region pointed to phosphorylated lactones missing from the initial docking library.
    - **execution scope:** Author modeling/structure/assays; unsynthesized larger lactones are untested, not negative.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** HpbD_Zhao_2013
    - **use:** A neighboring binding-protein model refined generic N-substituted-amino-acid candidates to betaines.
    - **execution scope:** Author computation; physiological pathway was validated separately in a tractable related organism.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** DUF1537_Zhang_2016
    - **use:** Uninformative structural-search hits and later activity-guided complexes show that a fold-search output may have little discriminatory value.
    - **execution scope:** No new structural search; modeled ternary geometry remained a model.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** BC1793_Hitchcock_2013
    - **use:** An inserted modeled loop defeated transfer of an apparently aligned SAH-recognition arginine.
    - **execution scope:** No fresh model; measured activity negatives and modeled explanation are separate.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** BC0371_Song_2007
    - **use:** Reported homology-model docking and assay results supported a different racemase substrate class than the nearest characterized homolog.
    - **execution scope:** Abstract and deposited structure identity only; complete Methods/Results and search ordering not inspected.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T05-01, E-T05-02, E-T05-03, E-T05-04, E-T05-05, E-T05-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t06"></a>
### T06: Reaction identities and chemical accounting

- **description:** Retrieve chemical/reaction identities and calculate explicit atom, electron, carrier and cofactor ledgers under a declared reaction boundary; leave unmeasured driving forces unknown.
- **capability operations:** 
  - 
    - **operation:** Retrieve selected chemical or reaction records
    - **inputs:** 
      - **identifier or query:** explicit Rhea accession/query or ChEBI accession/text
      - **page limit:** chosen page/limit where supported
    - **outputs:** 
      - **source record:** native equation sides/direction or chemical structures/relations with source identities
    - **implementation status:** repository_catalog_defined
    - **confirmed repository callables:** 
      - public.rhea.search
      - public.rhea.reaction
      - public.chebi.search
      - public.chebi.compound
    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Calculate a declared reaction or route ledger
    - **inputs:** 
      - **reactions:** specified stoichiometric species, charges, carrier forms and direction
      - **boundary:** included reactions and excluded precursor/regeneration steps
      - **optional measurements:** reported potentials/concentrations with units and uncertainty
    - **outputs:** 
      - **ledger:** element/electron/carrier changes and residual imbalance
      - **derived values:** arithmetic or conditional energy relation with assumptions and unknown terms
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Propagate declared isotope labels through a supplied reaction map
    - **inputs:** 
      - **labels:** positions and enrichment from identified source measurements
      - **map:** explicit atom correspondence and alternative routes
    - **outputs:** 
      - **predicted patterns:** conditional atom-label predictions
      - **comparison:** observed versus predicted labels without inventing flux estimates
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - gene_annotation_episode/tools.py:public.rhea.* and public.chebi.* catalog definitions; no registered general stoichiometric/thermodynamic calculator confirmed.
  - **research operations performed:** 
    - chemistry/raw/bcd_redox_arithmetic.json: descriptive arithmetic using paper potentials and stated boundary.
    - replacement/raw/route_bookkeeping_probe.json: BioZ/BioC and ThyX/ThyA route ledgers and growth-ratio arithmetic; not flux simulation.
  - **capability specifications not confirmed as repository callables:** 
    - General ledger/isotope tools are capability specifications; new flux models, measured intracellular concentrations and membrane energetics are not supplied.
  - **author experiments are source evidence only:** 
    - Product identification, isotope-feeding and electron-transfer assays are source evidence from authors.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - Balanced or conditionally favorable chemistry does not show that a target performs it.
  - Keep NADH versus NADPH and chemical reducing equivalents distinct; excluded precursor costs remain excluded.
  - Observed approximate stoichiometry and idealized fully coupled reaction are different outputs.
- **observed uses:** 
  - 
    - **case group:** chem_bcd_etf
    - **use:** Actual arithmetic separated observed 2.2 NADH/1.4 crotonyl-CoA per H2 from idealized fully coupled 2:1:1 stoichiometry and its energetic interpretation.
    - **execution scope:** Read-only calculation with stated assumptions; no new redox measurement.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** replacement_bioZ
    - **use:** Actual ledgers showed C5 + C3 minus CO2 to C7 and different included reduction counts across routes.
    - **execution scope:** Four versus two reducing steps is not automatically four versus two NADPH; upstream substrate costs excluded.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** replacement_thyX
    - **use:** Actual ledger contrasted ThyA production of DHF with ThyX return of THF and explicit donor-dependent net comparisons.
    - **execution scope:** The ThyA-plus-FolA comparison only matches the chosen NADPH boundary; no universal efficiency conclusion.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** chem_ubiuv_oxygen_donor
    - **use:** Authors position-specific 18O transfer constrained the prephenate oxygen-donor claim.
    - **execution scope:** No fresh atom-map or isotopologue fitting; isolated hydroxylation and electron acceptor remained unestablished.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** chem_mvh_hdr
    - **use:** Authors limiting-substrate and equilibrium comparisons constrained coupled heterodisulfide/ferredoxin chemistry.
    - **execution scope:** Analytical uncertainty and viologen bypass preserved; no raw data reanalysis.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** pxpABC_oxoproline_disposal
    - **use:** Thermodynamic concern over ATP-independent chemistry motivated distinguishing the reconstituted ATP-dependent system.
    - **execution scope:** Published reconstitution, not a new energy measurement or substituted reaction rule.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T06-01, E-T06-02, E-T06-03, E-T06-04, E-T06-05, E-T06-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t07"></a>
### T07: Assay-specific kinetic and signal comparisons

- **description:** Extract matched assay conditions and numeric estimates, calculate declared ratios or bounds, and expose substrate/partner and readout dependencies without relabeling apparent parameters as direct binding or native flux.
- **capability operations:** 
  - 
    - **operation:** Tabulate reported assay measurements
    - **inputs:** 
      - **measurements:** identified rates, Km/Kd/IC50, signals and nondetection thresholds
      - **context:** substrates, partner proteins, concentrations, metal/cofactor, assay direction and units
    - **outputs:** 
      - **table:** measurement values with censoring, units, conditions and source locations
      - **comparability:** declared matched dimensions and recorded differences; no automatic scientific verdict
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Compute a selected ratio, difference, or simple model prediction
    - **inputs:** 
      - **values:** source-bound numeric estimates, inequalities and units
      - **expression:** explicit arithmetic or declared one-parameter prediction
      - **uncertainty:** reported support or unavailable status
    - **outputs:** 
      - **derived result:** value or lower/upper bound with expression
      - **limitations:** censoring and unsupported statistical/kinetic claims
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Fit supplied time-course or saturation data
    - **inputs:** 
      - **points:** actual raw/processed values, replicates and units
      - **model:** declared rate equation/error model and fitting settings
    - **outputs:** 
      - **fit:** estimates, residuals and uncertainty under that model
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - Existing source readers expose input tables. No general registered kinetic-fitting or assay-comparison callable confirmed.
  - **research operations performed:** 
    - comparison/counterexample_calculations.json: selected deaminase censoring bounds and HisN source-table rank comparisons.
    - specificity/detailed_traces.json: selected YihU mutant apparent-efficiency arithmetic.
    - root/regulatory_specificity/raw/iscr_comparison_probe.json: published oligo/affinity/competition arithmetic; no raw-curve refit.
  - **capability specifications not confirmed as repository callables:** 
    - New curve fitting requires actual points and an explicit implementation. A Kd/Km/IC50 table does not supply raw observations or statistical support.
  - **author experiments are source evidence only:** 
    - Substrate screening, binding assays, reconstitution, inhibition and kinetic measurement are author-only experiments here.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - Km is not a bindingKd; competitionIC50 is not automaticallyKd.
  - Censored undetected activity is a bound at the actual assay conditions, not zero.
  - Coupled-readout specificity can belong to the partner/reporter; noncognate substrate conditions and fixed cosubstrate saturation matter.
- **observed uses:** 
  - 
    - **case group:** TM0936_Hermann_2007
    - **use:** Selected contrasting deaminase-table values yielded only censored selectivity bounds, defeating a single-residue specificity transfer.
    - **execution scope:** Actual arithmetic; no new kinetics, model fitting or broad classifier benchmark.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** spec_yihu_native_sulfonate
    - **use:** Actual mutant comparisons separated sulfosugar substrate effects from a uniform active-protein-loss explanation under its stated model.
    - **execution scope:** Apparent efficiencies at fixed cosubstrates; not binding energies, raw fits or native flux.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** reg_iscR_state_target_specificity
    - **use:** Actual ratio and oligo calculations separated preserved affinity at one site from expanded target recognition, and retained competition lower bounds.
    - **execution scope:** No new affinity assay; rounded central values and IC50 censoring retained.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** chem_f420_precursor_partner
    - **use:** Changing the downstream CofD/FbiA partner changed apparent precursor preference despite unchanged upstream enzyme.
    - **execution scope:** Author reconstitutions; no new spectra, crystallographic refinement or flux measurements.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** chem_hydabc
    - **use:** Dithionite carryover and donor-generating enzymes could short-circuit a coupled assay dependence.
    - **execution scope:** Authors controls; no new gas-chromatography analysis.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** spec_cysq_pap_not_imp
    - **use:** Sensitive source assays discriminated PAP hydrolysis from much weaker IMP/FBP activity while retaining substrate-instability limits.
    - **execution scope:** Author kinetics; no raw fits or fresh substrate measurements.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T07-01, E-T07-02, E-T07-03, E-T07-04, E-T07-05, E-T07-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t08"></a>
### T08: Genotype, component and functional-perturbation tables

- **description:** Represent actual strain/construct/component contrasts and their measured outcomes, preserving the distinction between a perturbation, its validated molecular effect and the endpoint being compared.
- **capability operations:** 
  - 
    - **operation:** Extract a genotype/component-by-condition outcome matrix
    - **inputs:** 
      - **records:** identified published or supplied observations
      - **row identity:** strain, exact alleles/constructs, component mixture and condition
      - **outcome:** declared endpoint, units, source support and unknown status
    - **outputs:** 
      - **matrix:** separate genotype, molecular validation, localization/expression, endpoint and rescue fields
      - **comparisons:** requested matched contrasts and unresolved confounders
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Select rows satisfying a declared control rule
    - **inputs:** 
      - **matrix:** source-bound rows
      - **predicate:** explicit conjunction over recorded fields, e.g. stable AND localized AND separation-defective
    - **outputs:** 
      - **selection:** matching original row IDs and measured values
      - **unknowns:** rows excluded because a field is unmeasured, not assumed negative
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Tabulate pairwise versus joint-complex evidence
    - **inputs:** 
      - **components:** identified protein/DNA/RNA species
      - **observations:** pairwise, simultaneous, reconstituted and dependency records with assay conditions
    - **outputs:** 
      - **relations:** typed measured interactions/dependencies and explicit untested combinations
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - Source readers are repository-defined. No registered genetic-interaction, epistasis or complex-attribution agent is supplied by these operations.
  - **research operations performed:** 
    - causal EnvC Table 1 parse selected five stable/localized/function-defective variants among 20 rows.
    - cellular/yhcB_direct_observations.json extracted source-table and processed fitness/suppressor rows.
    - spatial/archaeal_processing/investigation.json contains declared small-panel rule audits, not a validated genome classifier.
  - **capability specifications not confirmed as repository callables:** 
    - General typed contrast-matrix construction and interaction querying remain capability specifications for runtime.
  - **author experiments are source evidence only:** 
    - Deletion, complementation, suppressor selection, purified mixtures, fluorescence reporters, co-IP and interaction measurements are all author experiments here.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - A mutant called catalytic in another species is not a validated catalytic-null mutant in the target assay.
  - Overexpression rescue can establish capacity in that construct, not normal native contribution or direct chemistry.
  - Pairwise binding does not establish simultaneous occupancy; endpoint rescue does not by itself locate the causal route.
- **observed uses:** 
  - 
    - **case group:** causal_envC_activation
    - **use:** Actual Table 1 selection preserved mutants with stable localization yet lost separation/activation, rather than conflating all failures.
    - **execution scope:** No new mutagenesis or binding assay; fold similarity alone did not assign peptidase chemistry.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** causal_cas2_spacer_acquisition
    - **use:** Source contrasts separated E9-tolerant acquisition/integration from assembly-disrupting variants and Cas1 catalytic dependence.
    - **execution scope:** No direct E. coli E9 nuclease-null demonstration; author biological assays.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** causal_nlpI_scaffolding
    - **use:** Published preformed partner-complex controls distinguished simultaneous assemblies from pairwise interactions.
    - **execution scope:** No new pull-down or physiological proof of every proposed ternary arrangement.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** spec_suhb_catalysis_vs_rrna
    - **use:** Active heterologous IMPases failed rescue while inactive native D87N retained rescue, bounding the catalysis-to-function transfer.
    - **execution scope:** This 2000 finding was primary-abstract-only here; later Nus/RNA results were inspected more fully.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** organism_03_tau_ssu
    - **use:** Complementation depended on copy number and uptake route, so a failed high-copy rescue did not negate the transporter role.
    - **execution scope:** Author growth/uptake comparisons; no new transport experiment.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** replacement_bioK
    - **use:** Temperature, induction and insolubility separated cellular rescue from unavailable purified chemistry.
    - **execution scope:** No purified BioK activity claimed.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** organism_10_hpnn
    - **use:** Removing hopanoid synthesis suppressed a mislocalization-associated phenotype, separating harmful location from simple absence.
    - **execution scope:** Author lipid/growth data; no new localization measurements.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T08-01, E-T08-02, E-T08-03, E-T08-04, E-T08-05, E-T08-06, E-T08-07 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t09"></a>
### T09: RNA and genomic-signal coordinate windows

- **description:** Read selected deposited signal tracks against the exact reference feature frame and calculate stated local contrasts; keep processed tracks distinct from raw-read reconstruction and transcript-processing evidence distinct from ordinary abundance.
- **capability operations:** 
  - 
    - **operation:** Retrieve selected study metadata and track files
    - **inputs:** 
      - **study:** exact accession and sample/file IDs
      - **selection:** specific processed tracks and reference feature version
    - **outputs:** 
      - **files:** identified track/reference bytes and sample metadata
      - **coverage:** available processed versus missing/raw files
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Summarize a declared genomic window
    - **inputs:** 
      - **track:** identified bedGraph/wig-like or explicit coordinate signal table
      - **reference:** exact accession/version, strand and coordinate convention
      - **window:** explicit genomic intervals and statistic
    - **outputs:** 
      - **values:** per-position/interval values and declared local summary
      - **comparison:** selected sample contrasts with reference and normalization provenance
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Reconstruct a new RNA profile from reads
    - **inputs:** 
      - **reads:** actual FASTQ files and sample designs
      - **reference model:** chosen mapping/processing method and parameters
    - **outputs:** 
      - **profile:** processed coverage/ends/counts with normalization and uncertainty under that pipeline
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - public.ncbi.search/sequence and reference.neighborhood can provide selected source/reference context. The catalog defines generic reads.map, but that does not establish an RNA-seq/Rend-seq analysis pipeline or GEO acquisition adapter.
  - **research operations performed:** 
    - cellular/ylbF_probe_provenance.json and ylbF_rendseq_control_observations.json:76-file GSE108295 processed-track archive and exact reference table; selected cggR/gapA,glnR/glnA,rpoB,rnpB windows examined.
    - organism GcsR trace: GSE76522 metadata only; no read reprocessing.
  - **capability specifications not confirmed as repository callables:** 
    - New RNA-seq/Rend-seq mapping, processing-site inference, differential analysis and formal replication statistics were not performed or established as registered tools.
  - **author experiments are source evidence only:** 
    - RNA purification, sequencing, Northern assays and reporter measurements are author experiments/data generation.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - A processed end signal is not ordinary gene-expression abundance and its normalization is source-specific.
  - No window or reference remapping without explicit accession/coordinate correspondence.
  - Metadata-only access or an accession listing supplies no new biological signal.
- **observed uses:** 
  - 
    - **case group:** cellular_y_complex
    - **use:** Actual processed-track inspection found the cggR/gapA 5-prime signal strongly reduced in Y-complex deletions while a distinct rnpB control retained signal.
    - **execution scope:** Selected known windows, no raw realignment, new processing-site discovery or formal replication analysis.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** cellular_ybeY
    - **use:** Published swapped-subunit and rRNA-terminus evidence distinguished a 30S-associated degradation route from general ribosome impairment.
    - **execution scope:** Author experiments; no raw sequencing profile or ribosome data reanalysis.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** cellular_yqfG
    - **use:** Published end-specific controls restricted the phenotype to 16S 3-prime maturation among tested ends.
    - **execution scope:** No newly computed RNA profile; linked homolog does not independently validate all E. coli claims.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** spec_suhb_catalysis_vs_rrna
    - **use:** Reporter antitermination and endogenous RNAP-occupancy results differed in scope, limiting reliance on an ordinary reporter alone.
    - **execution scope:** E-MTAB-4240 was identified, not newly fetched/reanalyzed; ordinary counts do not establish rRNA maturation.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** organism_04_gcsr
    - **use:** Actual metadata established four RNA-seq samples, two per genotype, while source Results described a narrower clean-deletion regulatory effect.
    - **execution scope:** Metadata inspection only for the deposition; no raw or processed RNA-seq reanalysis.
    - **use status:** research_read_only_operation_performed

Source observations: E-T09-01, E-T09-02, E-T09-03, E-T09-04, E-T09-05 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t10"></a>
### T10: Mass-spectrometric identity and site-table operations

- **description:** Expose selected published product, peptide or phosphosite identifications and quantify declared table contrasts while preserving analyte/site identity, replicate structure, normalization, censoring and missingness.
- **capability operations:** 
  - 
    - **operation:** Extract analyte/site-resolved source rows
    - **inputs:** 
      - **source:** actual table/workbook or supplied identification file
      - **selector:** exact analyte, peptide/site, protein and sample keys
      - **metadata:** column meanings, units, ratios, normalization and missingness definitions
    - **outputs:** 
      - **rows:** native cells with site/analyte identity and replicate/sample correspondence
      - **missingness:** unmeasured, censored and observed values kept separate
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Compute a declared table transformation
    - **inputs:** 
      - **values:** selected source intensities/ratios/log values
      - **expression:** explicit ratio, log difference, exponentiation or mass difference
      - **comparability:** stated reference/channel/replicate relation
    - **outputs:** 
      - **result:** descriptive derived values with exact inputs
      - **scope:** response-ratio, abundance or occupancy meaning only when source warrants it
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Analyze raw spectra against selected identities
    - **inputs:** 
      - **spectra:** actual raw/open spectral data and acquisition metadata
      - **search or fit model:** declared peptide/metabolite library, modification list, scoring and error model
    - **outputs:** 
      - **candidate identifications:** matches, ambiguity and support under that model
      - **quantification:** pipeline-specific estimates with controls and uncertainty
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - source.xlsx.sheets/rows and generic source readers are repository-defined; no raw-MS search/quantification engine confirmed.
  - **research operations performed:** 
    - organism/yeag/trace.json: six selected 2021 phosphosite rows decoded directly from the workbook; selected response-ratio calculations reproduced.
    - cellular YhcB source work extracted processed phenotype/genetic rows, not raw MS.
  - **capability specifications not confirmed as repository callables:** 
    - Raw proteomics/metabolomics identification, isotope fitting, occupancy correction and new compound identification require files and software not supplied by this catalog.
  - **author experiments are source evidence only:** 
    - LC-MS/NMR/product synthesis, native activity purification and phosphorylation assays are authors evidence; no sample or spectral acquisition is available here.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - Nonzero intensity with missing ratio is not analyte absence or zero effect.
  - A normalized ratio is not automatically absolute abundance, occupancy fraction or protein-abundance-corrected phosphorylation.
  - Analyte disappearance without identified product does not establish the proposed productive reaction.
- **observed uses:** 
  - 
    - **case group:** yeag
    - **use:** Actual AceA/Hfq/YjhQ source rows exposed response-ratio meaning and asymmetric replicate coverage; AceA S398 retained a nonzero mutant intensity despite missing ratios.
    - **execution scope:** Six selected source rows; no raw spectra, significance testing or exact causal phosphorylation-site assignment.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** spec_aquifex_hfp_coupling_contamination
    - **use:** Authors peptideMS attributed recurrent isomerase activity across preparations to host RpiA rather than the candidate HFP.
    - **execution scope:** Underlying spectra not reanalyzed; no new contaminant identification.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** chem_f420_precursor_partner
    - **use:** Different chemically identified pathway products prevented treating all coupled signals as mature F420.
    - **execution scope:** Author LC-MS and structures; no raw spectrum fitting.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** replacement_queH
    - **use:** A later in-vitro assay lost oQ without detecting Q, limiting the productive-reductase claim.
    - **execution scope:** No newly analyzed spectra or demonstrated purified Q synthesis.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** seq_queFL_archaeosine
    - **use:** Free preQ0 and preQ0-tRNA could both form adducts, while productive archaeosine synthesis depended on the tRNA-bound substrate.
    - **execution scope:** Author product/substrate assays; no raw tRNA modification reanalysis.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** organism_17_ybts
    - **use:** Author metabolite identity and copper-loading comparisons constrained the protective role beyond an unspecified siderophore label.
    - **execution scope:** No new patient/sample analysis or purified YbtS catalysis.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T10-01, E-T10-02, E-T10-03, E-T10-04, E-T10-05, E-T10-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t11"></a>
### T11: Time, population and ecological-outcome tables

- **description:** Extract outcome trajectories and condition-stratified growth, survival, reporter or competition measurements; calculate declared comparisons at the resolution actually observed.
- **capability operations:** 
  - 
    - **operation:** Build a time/condition/outcome table
    - **inputs:** 
      - **observations:** identified source trajectories, distributions or summary measurements
      - **dimensions:** strain, medium, host/community state, time, population resolution and endpoint
      - **provenance:** sample/replicate IDs, units and proxy definition
    - **outputs:** 
      - **table:** separate lag, growth, survival, uptake, signal and competitive outcomes
      - **coverage:** time windows and cell/population resolution actually observed
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Calculate a specified temporal or condition contrast
    - **inputs:** 
      - **table:** selected source rows or actual point data
      - **contrast:** explicit time window, ratio/difference or group selection
      - **uncertainty:** reported variation or unknown status
    - **outputs:** 
      - **summary:** descriptive conditional comparison
      - **limits:** unobserved intervals, pooling and non-equivalent endpoints
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Reanalyze actual single-cell trajectories or flow events
    - **inputs:** 
      - **data:** actual events/images/lineages plus gates or tracking model
      - **analysis:** explicit gating, trajectory and calibration settings
    - **outputs:** 
      - **distribution:** pipeline-defined per-cell/trajectory summaries with errors
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - Source access/readers are defined. No dedicated flow-cytometry, lineage, animal-study, ecological-competition or time-series analysis callable confirmed.
  - **research operations performed:** 
    - replacement/raw/route_bookkeeping_probe.json includes source ThyX/ThyA growth ratios; no curve fitting.
    - YeaG source inquiry compared recovery and delayed CFU outcomes; no FCS/lineage reanalysis.
  - **capability specifications not confirmed as repository callables:** 
    - New growth-curve digitization/fitting, flow-event analysis, animal-data reanalysis and population lineage inference are unexecuted capabilities needing actual data and implementations.
  - **author experiments are source evidence only:** 
    - Timed culture, CFU, microscopy, flow cytometry, host perturbation and microbial-community experiments are author experiments.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - Faster immediate regrowth need not mean greater long-term survival.
  - A reporter proxy is not direct metabolic flux; population heterogeneity is not tracked lineage fate.
  - No phenotype at one medium/time/host condition is not universal dispensability; competition and single-strain growth differ.
- **observed uses:** 
  - 
    - **case group:** yeag
    - **use:** Early induction, shorter 24-hour recovery lag and later 72-hour-and-beyond CFU loss expose distinct outcomes rather than one beneficial/defective label.
    - **execution scope:** Published data inspected; no new flow events, single-cell fates or survival experiments.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** organism_20_isia
    - **use:** The mutant initially grew quickly but later bleached under severe iron deficiency/high light, with different outcomes under low light or iron repletion.
    - **execution scope:** Author time/condition comparisons, not new fluorescence-lifetime or growth analysis.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** organism_18_dsdapm
    - **use:** A six-hour urine nonphenotype coexisted with a 96-hour catheter-associated-host fitness deficit.
    - **execution scope:** Different endpoint/context retained; no new animal or ex-vivo analysis.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** organism_07_xyg
    - **use:** Dietary competition benefit disappeared when alternative polysaccharides were available.
    - **execution scope:** Author tested diets; no universal claim about ordinary human diets.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** organism_01_ttr
    - **use:** Tetrathionate respiration benefited intestinal competition under inflammation with source and host-oxidase controls.
    - **execution scope:** Host mechanism is author work; actual live record query established locus identity only.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** replacement_lysU
    - **use:** 1990 temperature-conditioned defect and later lack of a tested growth difference must retain strain/assay differences.
    - **execution scope:** 1990 primary abstract only; conflicting conditions not experimentally reconciled.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T11-01, E-T11-02, E-T11-03, E-T11-04, E-T11-05, E-T11-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t12"></a>
### T12: Regulatory DNA sites, inputs and measured-output correspondence

- **description:** Compare exact regulatory DNA sequences and mapped promoters, expose motif matches under a supplied model, and retain separate binding, molecular-input/state and transcription-output records.
- **capability operations:** 
  - 
    - **operation:** Compare selected operator or promoter sequences
    - **inputs:** 
      - **sequences:** identified oligonucleotides or genomic intervals with strand/coordinates
      - **correspondence:** declared common reference and positional convention
    - **outputs:** 
      - **differences:** exact substitutions, indels and motif-position correspondence
      - **scope:** selected sites only, without an inferred regulon
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Scan supplied sequences with an explicit motif model
    - **inputs:** 
      - **motif:** supplied PWM/PSSM and alphabet
      - **sequences:** actual FASTA and background model
      - **parameters:** explicit score/significance/multiple-testing settings
    - **outputs:** 
      - **matches:** positions, strands, model scores and conditional p/qvalues
      - **provenance:** motif, sequence and background identity
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Join source records at exact target/condition identities
    - **inputs:** 
      - **records:** separate binding, reporter/transcript, abundance and protein-state observations
      - **keys:** actual target/promoter variant, protein state, sample and assay condition
    - **outputs:** 
      - **table:** measured links and unmatched observations; activation/repression only when directly recorded
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - sequence.align/sites, public.ncbi.sequence and reference.neighborhood provide general sequence/feature primitives. No FIMO or regulator-inference callable confirmed in repository catalog.
  - **research operations performed:** 
    - root/regulatory_specificity/raw/iscr_comparison_probe.json: seven published 30-mer oligos compared at exact positions; selected source competition ratios calculated.
  - **capability specifications not confirmed as repository callables:** 
    - FIMO was identified from official documentation as a motif+FASTA scanner, but it was not executed and its installation/registry binding was not established. New regulon reconstruction is not supplied.
  - **author experiments are source evidence only:** 
    - DNA-binding, footprinting, reporter, redox-treatment and metal/cofactor measurements remain author experiments.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - A motif match supplies a model-based candidate site, not regulatory direction or a productive cellular effect.
  - A bound site can have no detected output in tested conditions; affinity at one site does not measure exclusion of other targets.
  - An environmental treatment can act through a cofactor/feedback route; it does not establish direct ligand binding to the regulator.
- **observed uses:** 
  - 
    - **case group:** reg_iscR_state_target_specificity
    - **use:** Actual oligo and source comparisons separated altered target recognition, preserved single-site affinity, nonfunctional footprinted sites and promoter-specific output.
    - **execution scope:** No new motif scan, regulon, intracellular state quantification or binding assay.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** context_rbkr_regulator_kinase_2017
    - **use:** Conserved upstream sites and binding linked a dual kinase/regulator to riboflavin genes, while operator positions only suggested activation.
    - **execution scope:** Authors comparative and binding work; no motif scan repeated.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** organism_16_malr
    - **use:** Measured promoter binding did not change when maltose was added, despite MalR-dependent nutrient expression/growth.
    - **execution scope:** Author tests; no direct maltose-binding conclusion or new reporter assay.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** pxpT_pxpR_access_and_sensing
    - **use:** Binding to 5-OP and promoter-site perturbations contributed different measured links in a repressive regulatory route.
    - **execution scope:** Author ITC/reporters; raw binding data not obtained; growth did not directly measure purified transport.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T12-01, E-T12-02, E-T12-03, E-T12-04 in [OPTION_SOURCES.md](OPTION_SOURCES.md).

<a id="t13"></a>
### T13: Compartment, export and membrane-access feature tables

- **description:** Expose exact sequence/topology features and source-controlled access/orientation readouts so export, processing, physical access and downstream assembly can be compared as distinct measured properties.
- **capability operations:** 
  - 
    - **operation:** Inspect declared signal or transmembrane sequence features
    - **inputs:** 
      - **sequence:** identified protein with native numbering
      - **features:** explicit source feature annotations or declared local motif/length rule
      - **alignment:** optional exact correspondence for truncations/hybrids
    - **outputs:** 
      - **feature table:** residue windows, charge/motif/leader lengths and rule matches
      - **limits:** unmeasured or ambiguous features retained
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Predict topology or export signals under a supplied model
    - **inputs:** 
      - **sequences:** actual selected protein sequences
      - **predictor:** named implementation/version/model and organism settings
    - **outputs:** 
      - **predictions:** segment/signal positions, orientation and model confidence where provided
    - **implementation status:** capability_specification
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
  - 
    - **operation:** Tabulate membrane-access and processing observations
    - **inputs:** 
      - **source observations:** identified reporter accessibility, processing band, fractionation, leakage/orientation controls and assembly/output records
      - **keys:** construct, compartment treatment, temperature and membrane preparation
    - **outputs:** 
      - **table:** separate access/processing/assembly/output fields and exact controls
      - **unknowns:** unmapped cleavage sites, unexpressed hybrids and unresolved orientation
    - **implementation status:** research_script_only
    - **confirmed repository callables:** 

    - **invocation note:** Normalized capability contract; the confirmed callable list identifies existing related primitives only, not interchangeable signatures.
- **availability:** 
  - **repository catalog defined:** 
    - public.uniprot.record, material.annotations and sequence.align/sites can provide source features and selected residue correspondences; no specific SignalP/TMHMM/DeepTMHMM/FlaFind callable confirmed.
  - **research operations performed:** 
    - spatial/archaeal_processing/investigation.json: exact selected leader-length panel and six-pilin-minus-2-residue rule audits from published records. No full FlaFind rerun or de-novo topology prediction.
  - **capability specifications not confirmed as repository callables:** 
    - Topology, export-signal prediction and genome-scale pilin discovery require a supplied implementation; existing annotations are source assertions.
  - **author experiments are source evidence only:** 
    - Spheroplasts, membrane vesicles, reporter fusions, protease/alkylation access, localization, processing and filament assays are author experiments.
  - **binding limit:** A repository catalog definition is confirmed source-code identity, not proof of caller enablement, service availability, installed dependencies or execution in this research. Research scripts are retained operations, not registered runtime tools.
- **limits:** 
  - Processing-band shift need not identify the exact cleavage site or restore downstream assembly.
  - Predicted orientation and reagent accessibility are different observations; vesicle orientation/leakage and burial controls matter.
  - An unexpressed hybrid cannot establish an assembly-specific defect; heterologous membrane preparation/temperature limits transfer.
- **observed uses:** 
  - 
    - **case group:** archaeal_pibd_flak_recognition_access
    - **use:** Actual leader-length rule audit showed LP5 positive/LP6 negative for FlaK, defeating a length-only explanation; PibD results had different preparation/temperature.
    - **execution scope:** Selected nine-member panel, not classifier validation; length 11 not tested.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** archaeal_hvo_pilin_processing_assembly
    - **use:** Processing-positive PilA1 hybrid lacked pili/adhesion while an unexpressed PilA3 hybrid could not isolate assembly failure.
    - **execution scope:** Author experiments; six-pilin rule audit adds no native cleavage-site or filament-composition measurement.
    - **use status:** research_read_only_operation_performed
  - 
    - **case group:** spatial_dsbd_topology_revision
    - **use:** Orientation-controlled cysteine accessibility revised an opposite-face static model while leaving the complete transport cycle unresolved.
    - **execution scope:** Published alkylation/vesicle experiments; no new topology prediction.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** spatial_murj_lipidII_access
    - **use:** Membrane disruption restored substrate cleavage after MurJ inhibition whereas outer-membrane removal did not, making access controls decisive.
    - **execution scope:** Author experiments; no purified transport repetition.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** spatial_amic_amia_export_septal_access
    - **use:** Functional export/targeting fusions separated Tat-dependent processing from AmiC septal concentration and induced rescue.
    - **execution scope:** No direct binding target or mandatory targeting claim.
    - **use status:** published_author_result_inspected_no_fresh_operation
  - 
    - **case group:** spatial_trxa_relocation_role
    - **use:** Exported thioredoxin function required genotype correction and DsbB-dependent reoxidation rather than localization alone.
    - **execution scope:** Author pulse-chase and redox assays; high-expression interpretation remains proposed.
    - **use status:** published_author_result_inspected_no_fresh_operation

Source observations: E-T13-01, E-T13-02, E-T13-03, E-T13-04, E-T13-05, E-T13-06 in [OPTION_SOURCES.md](OPTION_SOURCES.md).
