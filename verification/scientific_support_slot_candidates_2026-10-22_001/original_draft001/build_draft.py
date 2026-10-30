"""Construct review artifacts only. No library freeze, Store, Workflow or runtime.

All output is contained by this new /tmp directory. No network is used.
"""
from pathlib import Path
import csv
import hashlib
import json
import sys

ROOT = Path('/home/chia/repos/gene_annotation_episode')
OUT = Path('/tmp/scientific-support-slot-draft-20261022-001')
CROSS_PATH = 'docs/SCIENTIFIC_SUPPORT_CASE_CROSSWALK_2026-10-21_002.json'
SOURCE_FIELDS = 'case_group case_id source_url source_locator observation limit'.split()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def pointer(value, path):
    for segment in path.split('/')[1:]:
        segment = segment.replace('~1', '/').replace('~0', '~')
        value = value[int(segment)] if isinstance(value, list) else value[segment]
    return value

cross = json.loads((ROOT / CROSS_PATH).read_text())
by_group = {r['case_group']: (i, r) for i, r in enumerate(cross['case_rows'])}
# Inherited metadata and source-provenance safeguards are part of every body.
ROUTES = ('At construction and in decision context, resolve these observation kinds through '
    'annotation_support_routes for the actual caller-bound annotation policy; an entry does not '
    'supply universal component labels, select a projector, mask another kind, change a weight, '
    'or create a target finding. An unavailable route declaration remains unavailable.')
SOURCES = ('Retain actual source_ref, source_subject_refs, condition_refs and assumption_refs. '
    'The published examples below are instruction provenance about their named subjects; they '
    'are not observations of ybhP/b0790 and were not repeated to prepare this draft.')
CREDIT = ('Use actual retained assessments in a compatible annotation account. Selecting this '
    'entry earns nothing. The current caller-owned applicability × relation × extent arithmetic, '
    'same-component maximum, coherent-account integration and derived discrimination remain '
    'unchanged for this review basis. A finding qualification is not an automatic numeric discount; '
    'no independence, confidence or new score dimension is implied.')
REL = ['strengthens', 'weakens', 'mixed', 'does_not_discriminate']
NON_DIRECT = ['transfer', 'contextual', 'scope_limited', 'incomparable']
NONDIRECT_EXTENT = ('For another source subject use non-direct applicability. inferred_extent '
    'requires an explicit target_footprint bounded by the actual assigned original-input scope; '
    'missing target_footprint supplies no invented extent. context_allocation requires explicit '
    'context_account_scope and nonempty context_scope on both assessment and compatible account; '
    'it cannot carry target_footprint, creates no molecular measurement and is not a sequence map. '
    'Source residue numbers never become target coordinates.')
OBSERVED_EXTENT = ('observed_extent applies only to actual measured input/source geometry, clipped '
    'to original material; target_footprint can restrict that measurement. direct applies only '
    'when actual source subjects and the target proposition/conditions match. ' + NONDIRECT_EXTENT)

def operand(id, kinds, predicates, qualifications, instruction, *,
            applicability=NON_DIRECT, extent=['inferred_extent', 'context_allocation']):
    return dict(operand_id=id, observation_kinds=kinds,
        hypothesis_predicates=predicates, assessment_relations=REL,
        applicabilities=applicability, extent_bases=extent,
        finding_qualifications=qualifications,
        instruction=instruction + ' ' + (OBSERVED_EXTENT if 'observed_extent' in extent else NONDIRECT_EXTENT))

ALL_APPLICABILITY = ['direct', *NON_DIRECT]
ALL_EXTENT = ['observed_extent', 'inferred_extent', 'context_allocation']
entries = []

def entry(id, candidate_index, description, proposition, operands, qualifications, boundary):
    candidate = cross['candidate_support_entries'][candidate_index]
    entries.append(dict(entry_version='scientific_support_entry_v1', id=id,
        slot='annotation_distinction', name=candidate['name'], description=description,
        support=dict(proposition=proposition, operands=operands,
            qualifications=[*qualifications, SOURCES, ROUTES, CREDIT], boundary=boundary), evidence=[]))

entry('A101', 0,
 'Support a bounded target property through actual sequence correspondence to a separately characterized homolog; preserve family ancestry when exact activity fails to transfer.',
 'A named, source-characterized property of an identified comparator is relevant to a bounded target hypothesis through demonstrated sequence/domain/site correspondence, with the transferred property and its limits explicitly stated.',
 [operand('sequence_correspondence', ['alignment', 'profile_match', 'comparison'],
    ['functional_family', 'catalyzes', 'binds', 'transports', 'participates_in', 'requires', 'uses', 'produces'],
    ['different_source_subject', 'alternatives_not_discriminated', 'conditions_limit_transfer', 'prediction_not_measurement'],
    'Keep query/comparator identities, molecule and domain boundaries, aligned intervals, coverage and relevant site evidence. State which comparator property each target hypothesis seeks to transfer, and identify the separate characterizing observation in existing hypothesis/assumption/dependency references. A coherent family correspondence can strengthen functional_family while does_not_discriminate withholds exact catalyzes/binds/transports support. Discordant tested specificity can weaken the proposed transfer without erasing ancestry. Similarity scores and coverage are not calibrated reliability.'),
  operand('characterized_comparator_property', ['assay_report', 'biochemical_assay', 'genetic_phenotype', 'growth_assay'],
    ['functional_family', 'catalyzes', 'binds', 'transports', 'participates_in', 'requires', 'uses', 'produces', 'growth_capability'],
    ['different_source_subject', 'conditions_limit_transfer', 'measurement_does_not_establish_claim', 'confounding_unresolved'],
    'Record the comparator characterization as a separate source-bound assay or phenotype with its actual preparation/organism, inputs, output identity, controls and conditions. Do not relabel that assay as an alignment or a direct target measurement. Failed complementation or expression is not a purified-enzyme null; side activity or heterologous rescue does not establish native responsibility.')],
 ['HemK chemistry does not specify RF versus L3 substrate; TriA/AtzA near identity does not transfer the tested specificity. HisN complementation comparisons are selected examples, not a benchmark; host/expression effects remain possible. YadB recognition architecture and the matched Q34 test limit GluRS transfer.'],
 'This route does not choose a sequence threshold, certify orthology, join characterization to correspondence automatically, or establish exact activity from identity. The current record vocabulary has no dedicated typed characterized-property/correspondence join; the episode must state that relationship through the existing records. Entry suitability and scientifically adequate transfer criteria remain review questions.')

entry('A102', 1,
 'Constrain transferred function with relevant local structural correspondence while preserving model origin, ligand identity, access geometry and measured comparator chemistry.',
 'Relevant local machinery, pocket, access route or architecture of the target corresponds to that of an identified, separately characterized structural comparator; the supported property is bounded by observed correspondence and structural origin.',
 [operand('structural_correspondence', ['structure_match', 'comparison'],
    ['functional_family', 'catalyzes', 'binds', 'uses', 'requires', 'partner_dependence', 'participates_in'],
    ['prediction_not_measurement', 'different_source_subject', 'alternatives_not_discriminated', 'assumption_not_established'],
    'Retain exact structure/chain/construct identifiers, deposited versus predicted origin, residue/ligand identity, numbering correspondence, local geometry and conditions. Treat a fold, a modeled loop and a measured contact as their actual distinct propositions. Conserved catalytic architecture can strengthen broad chemistry; pocket/access changes can weaken a specific transfer. Lack of a search hit is limited by the actual search and does_not_discriminate unexamined structures.'),
  operand('structural_comparator_characterization', ['assay_report', 'biochemical_assay'],
    ['catalyzes', 'binds', 'uses', 'produces', 'requires', 'partner_dependence'],
    ['different_source_subject', 'conditions_limit_transfer', 'measurement_does_not_establish_claim', 'confounding_unresolved'],
    'Keep the comparator assay separate from structural correspondence and identify which measured property is relevant. TM0936 substrate negatives and positives constrain chemistry; retained ATP in MJ0577 establishes binding separately from hydrolysis, whose extract dependence leaves the enabling factor unresolved. A modeled contact explanation is not another assay.')],
 ['TM0936 local amidohydrolase similarity did not transfer cytosine specificity. Bc1793 loop explanations remain modeled and censored efficiencies remain bounds. Static geometry does not establish contact energy, catalytic necessity or physiological substrate.'],
 'This route supplies no calibrated model-to-function rule, no structural search or new coordinate calculation, and no claim that a matching fold entails a reaction. Structural support and chemical/resource accounting still share their current policy routes when the actual caller maps them together. Adequate local correspondence criteria remain unresolved.')

entry('A103', 2,
 'Support process association from recurrent locus, operon or fusion organization with exact genome identity, arrangement and exceptions.',
 'Actual, specifically organized recurrence of the target homolog/domain with a separately characterized process supports bounded functional association, rather than an exact reaction or substrate assignment.',
 [operand('observed_gene_organization', ['context', 'context_measurement', 'comparison'],
    ['participates_in', 'functional_family', 'partner_dependence'],
    ['different_source_subject', 'conditions_limit_transfer', 'alternatives_not_discriminated', 'confounding_unresolved'],
    'Preserve genome accession/release and strain, feature identity, order/orientation, overlap or intergenic interval, fusion boundaries and the exact examined inventory. Separate source feature labels from an assessed organization observation. Preserve broken/nonuniversal linkage and paralog/assembly ambiguity. Assess strengthens only for the bounded process association; does_not_discriminate exact catalyzes or substrate claims from proximity alone.'),
  operand('associated_process_characterization', ['assay_report', 'biochemical_assay', 'genetic_phenotype'],
    ['participates_in', 'functional_family', 'catalyzes', 'requires', 'partner_dependence'],
    ['different_source_subject', 'conditions_limit_transfer', 'measurement_does_not_establish_claim'],
    'Identify the independent source fact that characterizes the neighboring/fused process and preserve what it actually measured. HemK-prfA overlap nominates an RF relationship; methylation assays establish substrate/site. YjeF fusion supports coupling while epimerase chemistry and ADP dependence require separate assays. Use exact experimental strain rather than borrowing a comparison-table strain.')],
 ['HemK-prfA organization recurs but is nonuniversal. OarX ATCC 13032 table context and ATCC 14067 experimental work remain distinct; blank FmnO cells are unknown assignments. A fused architecture is not proof of a particular partner reaction or donor.'],
 'A proximity/fusion observation is not a direct assay, proof of operon transcription, universal linkage or independent replication across closely related genomes. No fixed neighborhood radius or required recurrence count is adopted. The episode retains actual observation meaning when kind dispatch differs under the caller policy.')

entry('A104', 3,
 'Support bounded process association from identified homolog co-distribution or replacement across an explicit organism inventory, retaining detection and missingness limits.',
 'Presence, supported absence or replacement of properly identified homologs covaries with a separately established pathway/product requirement in an explicit examined organism set, supporting bounded association.',
 [operand('homolog_distribution_comparison', ['context', 'context_measurement', 'comparison'],
    ['participates_in', 'functional_family', 'requires', 'partner_dependence'],
    ['different_source_subject', 'conditions_limit_transfer', 'alternatives_not_discriminated', 'assumption_not_established', 'confounding_unresolved'],
    'Retain organism/strain inventory, actual homolog-detection method and thresholds, sequence/database scope, paralogs, gene-model uncertainty and unexamined cells. Distinguish examined non-detection from supported absence. Keep product/pathway presence as a separately supported fact. A bounded covariance can strengthen association; a product retained without the usual gene can weaken a universal requirement and motivate a replacement, while blank cells remain unknown.'),
  operand('pathway_presence_or_requirement', ['assay_report', 'biochemical_assay', 'genetic_phenotype', 'growth_assay', 'context_measurement'],
    ['participates_in', 'produces', 'requires', 'growth_capability'],
    ['different_source_subject', 'conditions_limit_transfer', 'measurement_does_not_establish_claim', 'confounding_unresolved'],
    'Retain actual product identity, organism, assay/physiological context and pathway boundary that make the distribution relevant. QueF absence from archaea was interpreted against the shared preQ0 boundary, not as no archaeal modification pathway. HisZ occurrence and HisG length are associated architectures; subunit biochemistry remains separate. IspD homolog occurrence was assessed in the examined genomes, not every organism.')],
 ['Repeated related genomes do not establish independent observations. OarX/FmnO blank assignments do not demonstrate absence; organism inclusion and homolog detection bias can produce association. None of these retained cases defines a universal association significance threshold.'],
 'This route does not supply phylogenetic correction, a pan-genome completeness audit, a closed detection-scope record or a calibrated association test. Correlation does_not_discriminate exact reaction, substrate, donor or causal direction without further evidence. Entry suitability and adequate distribution criteria remain review questions.')

entry('A105', 4,
 'Support a defined molecular effect through identified inputs and measured outputs of the actual protein/preparation, with assay competence, controls and conditions.',
 'The actual source protein or preparation performs a specified conversion, transport, binding or physical effect on identified inputs under explicit conditions, with output identity and assay limitations retained.',
 [operand('identified_molecular_effect', ['assay_report', 'biochemical_assay'],
    ['catalyzes', 'transports', 'binds', 'uses', 'produces', 'requires', 'partner_dependence'],
    ['none', 'conditions_limit_transfer', 'measurement_does_not_establish_claim', 'alternatives_not_discriminated', 'confounding_unresolved'],
    'Preserve actual subject/preparation, substrate/recipient/product identities, measured units, concentration, temperature, pH, readout, positive/negative controls and tested panel. A product-identifying positive can strengthen only the tested proposition. A competent negative can weaken that proposition under those conditions; insolubility, missing substrate/partners, assay failure or contamination uncertainty leaves intrinsic capacity unresolved. Separate binding, proxy signal, net conversion and spontaneous downstream decomposition.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT),
  operand('molecular_effect_comparator', ['comparison', 'assay_report', 'biochemical_assay'],
    ['catalyzes', 'transports', 'binds', 'uses', 'produces'],
    ['conditions_limit_transfer', 'alternatives_not_discriminated', 'measurement_does_not_establish_claim', 'different_source_subject'],
    'Keep tested alternative substrates/preparations and derived ratios linked to the observations from which they came. QueF authentic preQ1 product is separate from controlled cyclohydrolase negatives. M3K phosphorylation is separate from spontaneous alkene formation. YadB binding to both Q-containing and Q-lacking tRNA does_not_discriminate glutamylation, whose matched test differs. YjeH export evidence retains dipeptide-loading and overexpression conditions; neither fold nor tolerance alone supplies flux direction.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT)],
 ['Side activity does not establish ordinary native responsibility, and a tested panel does not establish universal exclusivity. A source-reported bound remains a bound, not zero or an exact numeric threshold measurement; use the existing typed bound field when recording a genuine source bound. No assay magnitude is converted into score confidence.'],
 'A reporter, affinity value, survival rescue or preparation contaminant does not automatically establish purified conversion. No assay-completeness or product-authentication threshold, assay-to-reliability function, or new experiment is adopted. Published preparations remain their source subjects when compared with the fixed target.')

entry('A106', 5,
 'Support the component-specific contribution to a measured system output with selective perturbation, restoration and the actual construct, abundance, localization and bypass controls.',
 'A specified molecular/cellular output changes with a defined component or interaction, and the available perturbation/restoration controls support that component-specific contribution within the tested system.',
 [operand('perturbation_and_restoration_output', ['assay_report', 'biochemical_assay', 'genetic_phenotype'],
    ['participates_in', 'requires', 'partner_dependence', 'regulates', 'catalyzes'],
    ['conditions_limit_transfer', 'measurement_does_not_establish_claim', 'confounding_unresolved', 'alternatives_not_discriminated'],
    'Record actual genotype/construct and host, expression/preparation, partners, readout, condition and restoration/bypass comparison. Preserve independently measured abundance/stability/localization when present; an unmeasured control remains unknown. Use separate hypotheses for participation, activation, assembly and direct catalysis. Rescue can strengthen the restored relationship while does_not_discriminate the normal route; overexpression or nutrient bypass can be an alternative mechanism.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT),
  operand('selectivity_or_interface_constraint', ['comparison', 'structure_match', 'assay_report', 'biochemical_assay'],
    ['participates_in', 'requires', 'partner_dependence', 'regulates', 'binds', 'catalyzes'],
    ['prediction_not_measurement', 'assumption_not_established', 'confounding_unresolved', 'measurement_does_not_establish_claim', 'conditions_limit_transfer'],
    'Keep interface/contact evidence distinct from its functional test. Stable septal EnvC variants with lost AmiB activation can support activation rather than copied peptidase chemistry, while failed direct complex detection leaves the proposed helix contact unresolved. TsaE single-product versus repeated-turnover and retained ATPase versus failed t6A synthesis separate coupling from hydrolysis. Cas2 acquisition/assembly and the source-species nuclease expectation are separate; E. coli E9 variants were not directly demonstrated nuclease-null. YabA complementary-defect repair is bounded by actual same-defect controls.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT)],
 ['A deletion or active-site change is not automatically an interaction-only or catalysis-only perturbation. TsaE organisms/assay endpoints differ and remain unreconciled. Contact geometry is neither energetic necessity nor an independent functional assay. A silent single deletion retains overlap and condition-demand alternatives.'],
 'Existing references retain constructs and controls but do not prove causal entailment. This entry adopts no required control checklist, causal threshold or scientific acceptance gate. System attribution and isolated chemistry can remain merged numerically under the actual caller policy; that unresolved combination is not repaired by renaming the route.')

entry('A107', 6,
 'Assess bounded native deployment from measured availability or coordinated response in the same actual condition/state, preserving reporter, abundance and response limits.',
 'Measured availability or coordinated molecular response of the target and proposed process in the same native condition, cell state or phase supports their compatibility for participation at that condition.',
 [operand('native_availability_or_response', ['context_measurement', 'context'],
    ['participates_in', 'regulates', 'requires'],
    ['conditions_limit_transfer', 'measurement_does_not_establish_claim', 'alternatives_not_discriminated', 'confounding_unresolved'],
    'Retain measured entity, organism/strain, native versus induced construct, actual condition/phase/time, direct readout versus reporter, sampling/replicate context and matched process partners. State the bounded availability/co-response proposition. A coordinated measured change can strengthen compatibility for participation; decoupling or unaffected targets narrows that proposition. Induction alone does_not_discriminate catalytic action, flux, direct substrate or causal order.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT),
  operand('response_perturbation_or_contrast', ['assay_report', 'genetic_phenotype', 'comparison'],
    ['participates_in', 'regulates', 'requires', 'produces'],
    ['conditions_limit_transfer', 'measurement_does_not_establish_claim', 'confounding_unresolved', 'alternatives_not_discriminated'],
    'Preserve a perturbed response and its actual restoration/control as a separate fact from expression. Cdv cell-cycle induction and spatial dynamics differ from dominant-negative division effects. YeaG induction precedes delayed survival; GFP distributions are proxies rather than direct kinase action or uniform cell histories. Preserve Y-complex selective RNA-processing results and the separate strain/phosphorelay disagreement rather than treating every transcript as equivalent.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT)],
 ['A pooled abundance, expression reporter or phosphosite change is not a direct catalytic substrate or flux measurement. Sampling times, population composition and direct versus proxy readouts remain explicit. Selective responses constrain broad regulatory claims and do not automatically establish an entire process.'],
 'This is a concrete review candidate, with support thresholds and entry suitability still unresolved. No coexpression significance, phosphorylation-target rule, transcriptomics pipeline or universal minimum effect is adopted. The episode must distinguish compatibility for deployment from demonstrated native contribution; the current policy supplies no separate expression/deployment reliability operand.')

entry('A108', 7,
 'Support physiological prerequisites through measured access, localization or orientation of the actual protein/material/partners, with barrier, fractionation and functional-fusion limits.',
 'Measured access of protein, substrate and required partners to the relevant compartment/orientation under explicit conditions supports a prerequisite for the proposed physiological function.',
 [operand('measured_access_and_location', ['assay_report', 'biochemical_assay', 'context_measurement', 'context'],
    ['located_in', 'transports', 'participates_in', 'requires', 'partner_dependence'],
    ['conditions_limit_transfer', 'measurement_does_not_establish_claim', 'confounding_unresolved', 'alternatives_not_discriminated'],
    'Retain actual protein/construct and preparation, membrane/compartment/orientation, reporter competence, functional-fusion/fractionation/sided-access controls and native versus engineered location. MurJ barrier removal distinguishes outer access from inner translocation; DsbD cysteine accessibility retains orientation and mature-protein numbering. AmiC export, septal concentration and induced rescue are different propositions. A degraded or inaccessible reporter does_not_discriminate native protein location.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT),
  operand('predicted_or_transferred_access', ['comparison', 'structure_match'],
    ['located_in', 'transports', 'participates_in', 'requires'],
    ['prediction_not_measurement', 'different_source_subject', 'conditions_limit_transfer', 'alternatives_not_discriminated'],
    'Record actual prediction/model or homolog comparison with its origin and scope, separate from measured access. A prediction can motivate a location hypothesis without being relabeled a native assay. Conflicting measured sided-access results can weaken that prediction while preserving intrinsic chemical capacity. Heterologous membranes or partial blocking limit native orientation claims; do not grant a predictor that is absent from the selected real callable set.')],
 ['Measured location/access supports a prerequisite, not automatically productive conversion, assembly, native targeting necessity or an entire transport cycle. Functional induced rescue does not establish native targeting dispensability. Residual FtsW, degraded fusions, leakage/burial and reporter access retain their measured or unresolved limits.'],
 'No localization/topology prediction, localization assay or new transport experiment is performed by this entry. Kind dispatch can place distinct measurements in different current components; preserve the underlying support meaning instead of choosing kinds to gain volume. Scientifically adequate access controls and the suitability of this first-slot candidate remain review questions.')

entry('A109', 8,
 'Support a conditioned native contribution through allele-linked physiological performance with exact strain, resources, environment, time window, population and restoration controls.',
 'A defined physiological outcome depends on the gene/activity in a specified strain under explicit resource, environmental, time-window and population conditions, with the actual perturbation and restoration comparisons retained.',
 [operand('condition_matched_organism_performance', ['growth_assay', 'genetic_phenotype', 'assay_report'],
    ['growth_capability', 'participates_in', 'regulates', 'requires'],
    ['conditions_limit_transfer', 'measurement_does_not_establish_claim', 'confounding_unresolved', 'alternatives_not_discriminated'],
    'Keep actual allele/strain and organism, resource/medium, atmosphere/host/environment, competition or monoculture, sampling time, population and readout. Distinguish growth, survival/CFU, colonization, recovery and immediate lag. Preserve allele restoration, competitor/host controls and alternative-route genotypes. A matched effect strengthens the conditioned contribution; a matched nonphenotype weakens universal necessity without erasing biochemical capability.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT),
  operand('physiological_condition_or_window_contrast', ['comparison', 'growth_assay', 'genetic_phenotype'],
    ['growth_capability', 'participates_in', 'requires', 'regulates'],
    ['conditions_limit_transfer', 'alternatives_not_discriminated', 'confounding_unresolved', 'measurement_does_not_establish_claim'],
    'Represent opposing conditions/time windows as separate hypotheses and actual observations, keeping a derived comparison dependent on its source data. Ttr systemic nonphenotype differs from inflammation-dependent intestinal benefit. YeaG shortened recovery lag differs from worse prolonged-starvation survival; no averaging creates universal benefit. XoxF metal rescue needs identity/activity and alternate-oxidation controls. LysU historical heat rescue and later tested nonphenotype retain strain/media/temperature and inspection limits.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT)],
 ['A survival phenotype does not identify a molecular substrate, and nutrient/metal rescue can reflect regulation or bypass. Individual-cell trajectories, pooled reporters and CFU are distinct; no unmeasured lineage relationship is asserted. No tested nonphenotype establishes universal dispensability.'],
 'This route creates no new time/population axis and adopts no physiological effect-size, fitness threshold or acceptance rule. Whether native corroboration should receive a separate numeric dimension remains unresolved; the unchanged actual policy applies. Retain conflicting observations and specific unestablished mechanisms.')

entry('A110', 9,
 'Constrain a proposed reaction or coupled system with explicit material, electron, cofactor and regeneration obligations while keeping feasibility distinct from observed occurrence.',
 'Within a declared reaction/system boundary and stated assumptions, identified substrates, products, cofactors, electron sources/sinks and regeneration obligations form a consistent chemical/resource account for the proposed function.',
 [operand('reaction_or_resource_account', ['reaction_context', 'mechanism'],
    ['catalyzes', 'uses', 'produces', 'requires', 'partner_dependence'],
    ['assumption_not_established', 'measurement_does_not_establish_claim', 'conditions_limit_transfer', 'alternatives_not_discriminated'],
    'Retain named species, stoichiometric/chemical relationships, carrier states, electron source/sink, boundary, regeneration obligations and each actual measurement versus assumption. An incompatible account can weaken the specified route; a feasible account removes that objection and does_not_discriminate actual occurrence or native flux. Bcd/Etf measured H2-linked ratios differ from fully coupled extrapolation. BioZ local carbon/reduction events are not whole-pathway named-cofactor or energy use. ThyX and ThyA share dTMP but differ in folate-return obligations.'),
  operand('measured_chemical_constraint', ['assay_report', 'biochemical_assay', 'comparison'],
    ['uses', 'produces', 'catalyzes', 'requires', 'partner_dependence'],
    ['none', 'conditions_limit_transfer', 'measurement_does_not_establish_claim', 'assumption_not_established', 'confounding_unresolved'],
    'Preserve identified product/isotope position/turnover and omission/partner controls with their actual source subjects and conditions; derived balances/comparisons remain dependent on these measurements. F420 apparent precursor preference depends on the actual downstream partner and regeneration system. UbiUV isotope/route controls support a pathway oxygen source while purified hydroxylation and electron acceptor remain unestablished. A common final product does not establish equal routes, donor demand, stoichiometry or regeneration.',
    applicability=ALL_APPLICABILITY, extent=ALL_EXTENT)],
 ['Illustrative standard potentials, hypothetical event counts or source-derived ledgers are not intracellular free energy, measured pools, measured flux or independent experiments. Unknown donors, missing enzymes and boundary-excluded costs stay unknown. Source product identification cannot by itself validate a microscopic mechanism.'],
 'This entry performs no balance, arithmetic, thermodynamic analysis or experiment and adopts no completeness threshold or confidence weight. The current caller may route both accounting and structural evidence to one maximum; whether to separate them and how to reward dependent derived comparisons remain explicit unresolved numerical choices.')

# Each tuple is a deliberate selection of actual retained record values. For source
# records with several publications the row remains a case-level source mapping;
# source-specific IDs are checked where the original supplies them.
# (candidate index, case group, case ID, original observation pointer, source URL)
selection = [
(0,'hemk_prmc','seq_hemk_prmc_ecoli','/actual_observations/1','https://pmc.ncbi.nlm.nih.gov/articles/PMC125846/'),
(0,'seq_triA_atzA_near_identity','seq_triA_atzA_near_identity','/actual_observations/1','https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/'),
(0,'seq_triA_atzA_near_identity','seq_triA_atzA_near_identity','/actual_observations/2','https://pmc.ncbi.nlm.nih.gov/articles/PMC95154/'),
(0,'seq_hisn_impase_discrimination','seq_hisn_impase_discrimination','/actual_observations/3','https://link.springer.com/article/10.1186/s12866-017-1069-4'),
(0,'seq_yadB_gluQRS_ecoli','seq_yadB_gluQRS_ecoli','/actual_observations/0','https://pubmed.ncbi.nlm.nih.gov/15096594/'),
(1,'TM0936_Hermann_2007','TM0936_Hermann_2007','/actual_observations/paper_reported/0','https://doi.org/10.1038/nature05981'),
(1,'TM0936_Hermann_2007','TM0936_Hermann_2007','/actual_observations/paper_reported/1','https://doi.org/10.1038/nature05981'),
(1,'BC1793_Hitchcock_2013','BC1793_Hitchcock_2013','/actual_observations/paper_reported/0','https://doi.org/10.1021/ja4066078'),
(1,'BC1793_Hitchcock_2013','BC1793_Hitchcock_2013','/actual_observations/paper_reported/1','https://doi.org/10.1021/ja4066078'),
(1,'MJ0577_Zarembinski_1998','MJ0577_Zarembinski_1998','/actual_observations/paper_reported/1','https://pmc.ncbi.nlm.nih.gov/articles/PMC28018/'),
(1,'MJ0577_Zarembinski_1998','MJ0577_Zarembinski_1998','/actual_observations/paper_reported/2','https://pmc.ncbi.nlm.nih.gov/articles/PMC28018/'),
(2,'hemk_prmc','context_hemk_prmc_2002','/actual_observations','https://pmc.ncbi.nlm.nih.gov/articles/PMC125846/'),
(2,'yjef_nnr','context_yjef_nnr_fusion_2011','/actual_observations','https://pmc.ncbi.nlm.nih.gov/articles/PMC3308837/'),
(2,'context_oarx_thiamin_2024','context_oarx_thiamin_2024','/actual_observations/paper_reported','https://pmc.ncbi.nlm.nih.gov/articles/PMC11223231/'),
(3,'quef','context_quef_nitrile_reductase_2005','/actual_observations','https://pmc.ncbi.nlm.nih.gov/articles/PMC555470/'),
(3,'seq_hisZ_lactococcus','seq_hisZ_lactococcus','/actual_observations/0','https://pmc.ncbi.nlm.nih.gov/articles/PMC17719/'),
(3,'seq_ygbP_ispD_ecoli','seq_ygbP_ispD_ecoli','/actual_observations/2','https://pmc.ncbi.nlm.nih.gov/articles/PMC18359/'),
(3,'context_oarx_thiamin_2024','context_oarx_thiamin_2024','/actual_observations/paper_reported','https://pmc.ncbi.nlm.nih.gov/articles/PMC11223231/'),
(4,'quef','seq_queF_not_folE','/actual_observations/0','https://pmc.ncbi.nlm.nih.gov/articles/PMC555470/'),
(4,'quef','seq_queF_not_folE','/actual_observations/2','https://pmc.ncbi.nlm.nih.gov/articles/PMC555470/'),
(4,'seq_ptmvd_m3k_picrophilus','seq_ptmvd_m3k_picrophilus','/actual_observations/3','https://journals.asm.org/doi/full/10.1128/aem.04033-14'),
(4,'seq_yadB_gluQRS_ecoli','seq_yadB_gluQRS_ecoli','/actual_observations/2','https://pmc.ncbi.nlm.nih.gov/articles/PMC419609/'),
(4,'seq_yjeH_exporter_ecoli','seq_yjeH_exporter_ecoli','/actual_observations/1','https://pmc.ncbi.nlm.nih.gov/articles/PMC4616930/'),
(5,'causal_envC_activation','causal_envC_activation','/actual_observations/1','https://pmc.ncbi.nlm.nih.gov/articles/PMC3923381/'),
(5,'causal_envC_activation','causal_envC_activation','/actual_observations/2','https://pmc.ncbi.nlm.nih.gov/articles/PMC3923381/'),
(5,'causal_tsaE_turnover','causal_tsaE_turnover','/actual_observations/0','https://pmc.ncbi.nlm.nih.gov/articles/PMC5814804/'),
(5,'causal_tsaE_turnover','causal_tsaE_turnover','/actual_observations/1','https://pmc.ncbi.nlm.nih.gov/articles/PMC6614819/'),
(5,'causal_cas2_spacer_acquisition','causal_cas2_spacer_acquisition','/key_observations/1/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC4075942/'),
(5,'causal_cas2_spacer_acquisition','causal_cas2_spacer_acquisition','/key_observations/2/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC4359072/'),
(5,'cellular_yabA','cellular_yabA','/actual_observations/0/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC1413692/'),
(6,'cellular_cdv','cellular_cdv','/actual_observations/0/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC2596248/'),
(6,'yeag','cellular_yeaG','/actual_observations/0/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC4664914/'),
(6,'cellular_y_complex','cellular_y_complex','/actual_observations/0/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC4989519/'),
(6,'cellular_y_complex','cellular_y_complex','/actual_observations/1/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC4978174/'),
(7,'spatial_murj_lipidII_access','spatial_murj_lipidII_access','/actual_observations/1/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC4163187/'),
(7,'spatial_dsbd_topology_revision','spatial_dsbd_topology_revision','/actual_observations/1/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC193585/'),
(7,'spatial_amic_amia_export_septal_access','spatial_amic_amia_export_septal_access','/actual_observations/1/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC4428285/'),
(7,'spatial_amic_amia_export_septal_access','spatial_amic_amia_export_septal_access','/actual_observations/2/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC4428285/'),
(8,'organism_01_ttr','organism_01_ttr','/actual_observations/0','https://pmc.ncbi.nlm.nih.gov/articles/PMC2946174/'),
(8,'yeag','organism_06_yeag','/actual_observations/0','https://pmc.ncbi.nlm.nih.gov/articles/PMC4664914/'),
(8,'organism_02_xoxf','organism_02_xoxf','/actual_observations/0','https://pmc.ncbi.nlm.nih.gov/articles/PMC5075040/'),
(8,'replacement_lysU','replacement_lysU','/actual_observations/0/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC209130/'),
(8,'replacement_lysU','replacement_lysU','/actual_observations/1/observation','https://febs.onlinelibrary.wiley.com/doi/10.1111/febs.14113'),
(9,'chem_bcd_etf','chem_bcd_etf','/actual_observations/2/result','https://pmc.ncbi.nlm.nih.gov/articles/PMC2223550/'),
(9,'chem_f420_precursor_partner','chem_f420_precursor_partner','/actual_observations/2/result','https://pmc.ncbi.nlm.nih.gov/articles/PMC8764529/'),
(9,'chem_ubiuv_oxygen_donor','chem_ubiuv_oxygen_donor','/actual_observations/1/result','https://pmc.ncbi.nlm.nih.gov/articles/PMC10990095/'),
(9,'chem_ubiuv_oxygen_donor','chem_ubiuv_oxygen_donor','/actual_observations/2/result','https://pmc.ncbi.nlm.nih.gov/articles/PMC10990095/'),
(9,'replacement_bioZ','replacement_bioZ','/actual_observations/0/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC7645780/'),
(9,'replacement_thyX','replacement_thyX','/actual_observations/0/observation','https://pmc.ncbi.nlm.nih.gov/articles/PMC2168944/'),
]

source_mappings = []
for ei, group, case_id, observation_pointer, url in selection:
    ci, cr = by_group[group]
    si, source = next((j,s) for j,s in enumerate(cr['record_sources']) if s['case_id']==case_id)
    path = ROOT / source['corpus_path']
    locator = source['line_or_selector']
    if type(locator) is int:
        record = json.loads(path.read_text().splitlines()[locator-1])
        base_pointer = ''
        location = source['corpus_path'] + ':' + str(locator)
    else:
        document = json.loads(path.read_text())
        record = pointer(document, locator) if locator else document
        base_pointer = locator
        location = source['corpus_path'] + '#' + base_pointer
    assert digest(record)==source['original_record_sha256'], (case_id,'digest mismatch')
    observation = pointer(record, observation_pointer)
    assert isinstance(observation,str) and observation.strip()
    # Most retained original records supply one aggregate inspection scope; Cas2
    # observations additionally supply precise per-observation source ID and limit.
    scope = source['inspected_scope']
    specific = None
    if case_id=='causal_cas2_spacer_acquisition':
        obs_object = pointer(record, observation_pointer.rsplit('/',1)[0])
        primary = next(s for s in record['primary_sources'] if s['source_id']==obs_object['source_id'])
        assert primary['url']==url
        scope += ' | Specific observation limit: ' + obs_object['limit']
        specific = dict(source_id=obs_object['source_id'],
            source_id_pointer=observation_pointer.rsplit('/',1)[0]+'/source_id',
            limit_pointer=observation_pointer.rsplit('/',1)[0]+'/limit',
            publication_locator=obs_object['source_locator'])
    # A URL is permitted only if actually preserved by the original source row.
    def strings(v):
        if isinstance(v,str): yield v
        elif isinstance(v,list):
            for item in v: yield from strings(item)
        elif isinstance(v,dict):
            for item in v.values(): yield from strings(item)
    assert url in set(strings(source['primary_urls']))
    original_url_fields = {k:v for k,v in record.items() if k in
        ['primary_source_urls','primary_source_urls/DOIs','primary_sources']}
    assert url in set(strings(original_url_fields))
    # Published statements can be aggregates across linked papers in a single
    # retained case record; this map claims case-record membership, not a new
    # passage-level verification of each clause against one selected URL.
    source_locator = location + ('#' if type(locator) is int else '') + observation_pointer
    evidence = dict(case_group=group,case_id=case_id,source_url=url,
        source_locator=source_locator,observation=observation,limit=scope)
    evidence_index = len(entries[ei]['evidence'])
    entries[ei]['evidence'].append(evidence)
    source_mappings.append(dict(entry_id=entries[ei]['id'], evidence_index=evidence_index,
        evidence_id=f"E-{entries[ei]['id']}-{evidence_index+1:02d}",
        evidence_sha256=digest(evidence), crosswalk_case_pointer=f'/case_rows/{ci}',
        crosswalk_record_pointer=f'/case_rows/{ci}/record_sources/{si}',
        original_path=source['corpus_path'], original_file_sha256=file_digest(path),
        original_record_selector=locator, original_record_sha256=digest(record),
        original_observation_pointer=observation_pointer,
        crosswalk_observation_sha256=digest(source['preserved_observations']),
        source_relation='exact retained observation value and case-source URL membership; not new primary passage verification',
        original_inspection_scope=source['inspected_scope'], source_specific=specific))

# Prevent the instruction declarations from presenting the invalid cross-product
# direct+inferred_extent as an available pairing. These are alternatives, not a
# requirement to collect both. No new record schema or validator is introduced.
for e in entries:
    split=[]
    for op in e['support']['operands']:
        if op['applicabilities']==ALL_APPLICABILITY and op['extent_bases']==ALL_EXTENT:
            measured=dict(op,operand_id=op['operand_id']+'_measured',
                applicabilities=['direct','scope_limited'],extent_bases=['observed_extent'])
            measured['instruction'] += (' This measured-extent operand is for actual matching '
                'scoped source material only; direct never pairs with inferred_extent. '
                'Source facts from another protein/organism instead use the attributed operand.')
            attributed=dict(op,operand_id=op['operand_id']+'_attributed',
                applicabilities=NON_DIRECT,extent_bases=['inferred_extent','context_allocation'])
            attributed['instruction'] += (' This attributed operand is always non-direct. '
                'Choose inferred_extent with bounded target_footprint or context_allocation '
                'with explicit material allocation and no target_footprint, according to the actual fact.')
            split.extend([measured,attributed])
        else: split.append(op)
    e['support']['operands']=split
    write_json(f"entries/{e['id']}.json",e)

write_json('source_mapping.json',dict(status='review_draft_only_not_adopted',
    meaning='Exact source relationships for the selected illustrative evidence rows. Full 142-group review coverage is separate and does not imply that every group directly supports every draft body.',
    crosswalk_path=CROSS_PATH,crosswalk_file_sha256=file_digest(ROOT/CROSS_PATH), rows=source_mappings))
write_json('instruction_sources.json',dict(meaning='Library instruction provenance only; neither target findings nor newly executed published experiments.',
    rows=[dict(evidence_id=m['evidence_id'],option_id=m['entry_id'],
        **entries[int(m['entry_id'][1:])-101]['evidence'][m['evidence_index']]) for m in source_mappings]))
write_json('review_policy_reference.json',dict(status='unchanged_review_basis_not_runtime_binding_or_approval',
    source_path=CROSS_PATH,source_pointer='/arithmetic_review/policy',
    policy=cross['arithmetic_review']['policy'],
    applicability='This reference describes the review arithmetic only. At real construction, annotation_support_routes must declare the actual caller-bound matching policy; these bodies contain no hardcoded axis names. No score is calculated or policy selected here.',
    unresolved_choices=['current component merging versus explicitly specified separate contributions',
        'derived discrimination in the product versus nonnumerical interpretation metadata',
        'same-component maximum versus an explicitly specified provenance-aware accumulation',
        'reward for derived comparative interpretation versus additional independent evidence']))

# Keep the complete retained review partition and all149 record identities visible,
# without inventing a new scientific assignment of each group to one of10 routes.
coverage=[]
for ci, row in enumerate(cross['case_rows']):
    candidate_mentions = sorted({tag for contrast in row['support_contrasts']
        for tag in contrast['candidate_support_entries']})
    coverage.append(dict(case_group=row['case_group'],crosswalk_case_pointer=f'/case_rows/{ci}',
        best_coverage=row['best_coverage'], retained_candidate_mentions=candidate_mentions,
        records=[dict(case_id=s['case_id'],corpus_path=s['corpus_path'],
            line_or_selector=s['line_or_selector'],original_record_sha256=s['original_record_sha256'])
            for s in row['record_sources']],
        selected_draft_entries=sorted({m['entry_id'] for m in source_mappings
            if entries[int(m['entry_id'][1:])-101]['evidence'][m['evidence_index']]['case_group']==row['case_group']})))
write_json('review_coverage.json',dict(meaning='Unmodified membership and original record identities from the retained142-group review. Candidate mentions remain original review proposals; selected_draft_entries identifies only exact examples used by this draft. Empty selection means unused by the concrete bodies, not irrelevant to scientific support.',
    source_path=CROSS_PATH, partitions=cross['partitions'],
    counts=dict(groups=len(coverage),records=sum(len(r['records']) for r in coverage),
        support_contrasts=sum(len(r['support_contrasts']) for r in cross['case_rows']),
        selected_groups=sum(bool(r['selected_draft_entries']) for r in coverage),
        unused_groups=sum(not r['selected_draft_entries'] for r in coverage),
        relevant_primary_section_groups=sum(r['best_coverage']=='relevant_primary_sections' for r in coverage),
        abstract_or_summary_groups=sum(r['best_coverage']=='abstract_or_summary' for r in coverage)),
    abstract_or_summary_group_ids=[r['case_group'] for r in coverage if r['best_coverage']=='abstract_or_summary'],
    unused_group_ids=[r['case_group'] for r in coverage if not r['selected_draft_entries']],
    entry_case_index={e['id']:sorted({s['case_group'] for s in e['evidence']}) for e in entries},
    retained_exact_tag_index={e['id']:sorted(r['case_group'] for r in coverage
        if cross['candidate_support_entries'][i]['id'] in r['retained_candidate_mentions'])
        for i,e in enumerate(entries)},
    groups=coverage))

with (OUT/'source_mapping.tsv').open('w',newline='') as stream:
    writer=csv.writer(stream,delimiter='\t');writer.writerow(['entry_id','evidence_id',*SOURCE_FIELDS,'original_record_sha256'])
    for m in source_mappings:
        evidence=entries[int(m['entry_id'][1:])-101]['evidence'][m['evidence_index']]
        writer.writerow([m['entry_id'],m['evidence_id'],*(evidence[k] for k in SOURCE_FIELDS),m['original_record_sha256']])

write_json('candidate_catalog.json',dict(status='review_draft_only_not_a_loadable_source_index',
    entries=[dict(id=e['id'],name=e['name'],path=f"entries/{e['id']}.json",
        candidate_source_pointer=f'/candidate_support_entries/{i}',
        canonical_sha256=digest(e),file_sha256=file_digest(OUT/f"entries/{e['id']}.json"),
        evidence_rows=len(e['evidence'])) for i,e in enumerate(entries)]))

inspected = [
 '/home/chia/.codex/attachments/6c61440f-d223-4bea-91e3-6e4f7b2c5013/pasted-text-1.txt',
 'AGENTS.md','GOAL.md','docs/EPISODE_STRUCTURE.md','docs/TIME_AWARE_ESTIMATION.md',
 'docs/SCIENTIFIC_SUPPORT_SLOT_REVIEW_2026-10-21_002.md', CROSS_PATH,
 'gene_annotation_episode/scientific_support_metadata.py',
 'gene_annotation_episode/scientific_process_library.py',
 'gene_annotation_episode/scientific_process_episodes.py',
 'gene_annotation_episode/scientific_process_records.py',
 'gene_annotation_episode/scientific_process_setup.py',
 'gene_annotation_episode/scientific_tool_library.py',
 'gene_annotation_episode/domain.py', 'gene_annotation_episode/credit.py',
 'gene_annotation_episode/scientific_credit.py',
 'research/slotted_process_library/index.json',
 'research/slotted_process_library/option_sources.json',
 'research/slotted_process_library/entries/P19.json',
 'research/slotted_process_library/background/biological_claim_distinctions/option_sources.json',
 'research/slotted_process_library/case_records.json']
for m in source_mappings:
    if m['original_path'] not in inspected:inspected.append(m['original_path'])
write_json('input_manifest.json',dict(meaning='Read-only input hashes for this draft; no input is adopted or modified.',
    files=[dict(path=p,file_sha256=file_digest(Path(p) if Path(p).is_absolute() else ROOT/p)) for p in inspected]))
print(json.dumps(dict(entries=len(entries),evidence_rows=len(source_mappings),
    directly_illustrative_groups=len({e['case_group'] for x in entries for e in x['evidence']}),
    retained_review_groups=len(coverage),retained_review_records=sum(len(x['records']) for x in coverage))))
