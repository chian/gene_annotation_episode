from pathlib import Path
import json, hashlib
ROOT=Path('/home/chia/repos/gene_annotation_episode')
OUT=Path('/tmp/scientific-support-slot-draft-20261022-001')
x=json.loads((ROOT/'docs/SCIENTIFIC_SUPPORT_CASE_CROSSWALK_2026-10-21_002.json').read_text())
rows={r['case_group']:r for r in x['case_rows']}
def ptr(x,p):
 for k in p.split('/')[1:]:x=x[int(k)] if isinstance(x,list) else x[k]
 return x
def can(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(x):return hashlib.sha256(can(x).encode()).hexdigest()
curated={}
def source(g,case=None):return next(s for s in rows[g]['record_sources'] if case is None or s['case_id']==case)
def evidence(g,p,ui=0,case=None,doc=False):
 s=source(g,case); path=ROOT/s['corpus_path'];sel=s['line_or_selector']
 d=json.loads(path.read_text().splitlines()[sel-1]) if type(sel)is int else json.loads(path.read_text())
 r=d if type(sel)is int or not sel else ptr(d,sel)
 assert sha(r)==s['original_record_sha256']
 value=ptr(d if doc else r,p);assert isinstance(value,str)
 urls=s['primary_urls'];url=urls[ui];url=url['url'] if isinstance(url,dict) else url
 return dict(case_id=s['case_id'],**({'document_observation_pointer':p} if doc else {'observation_pointer':p}),source_url=url)
def add(g,entry,p,reason,ui=0,case=None,doc=False,role='support_and_boundary'):
 c=curated.setdefault(g,dict(case_group=g,mappings=[],unassigned_reason=None,gaps=[]))
 c['mappings'].append(dict(entry_id=entry,rationale=reason,role=role,evidence=[evidence(g,p,ui,case,doc)]))
def skip(g,reason):curated[g]=dict(case_group=g,mappings=[],unassigned_reason=reason,gaps=[])
# Explicit per-case review judgements; the rationale is a proposed library-source
# use, never a target assessment, positive score or independent evidence claim.
for g in x['partitions']['transfer']['case_groups']:
 if rows[g]['best_coverage']=='abstract_or_summary':
  skip(g,'Retained group is abstract/summary only: '+rows[g]['record_sources'][0]['inspected_scope']+' No methods/results upgrade was performed; retained as an inspected, unassigned source rather than ready curated instruction support.')
T=[
('Arad3529_Fan_2013','A102','/actual_observations/paper_reported/0','Conserved catalytic residues and remodeled substrate loops bound structural transfer.'),
('Arad3529_Fan_2013','A105','/actual_observations/paper_reported/1','Screening and product mass support tested pterin deamination, with unreproduced full substrate profile retained.'),
('BC1793_Hitchcock_2013','A101','/actual_observations/paper_reported/0','Aligned arginine is a counterexample to sequence-site sufficiency for SAH activity.'),
('BC1793_Hitchcock_2013','A102','/actual_observations/paper_reported/1','Inserted-loop contact account is modeled, constraining a structural transfer without claiming new measurement.'),
('BC1793_Hitchcock_2013','A105','/actual_observations/paper_reported/0','Assayed SAH nonactivity is bounded by the reported panel and censored efficiencies.'),
('Cc0300_Xiang_2009','A102','/actual_observations/paper_reported/1','Comparator ligand pocket localizes a structural specificity contrast without transferring the whole panel.'),
('Cc0300_Xiang_2009','A105','/actual_observations/paper_reported/0','Measured peptide panel separates terminal preference from longer/acylated capacity.'),
('Cc2672_Cc3125_Xiang_2009','A102','/actual_observations/paper_reported/1','Arginine-bound comparator and modeled contacts constrain inherited prolidase transfer.'),
('Cc2672_Cc3125_Xiang_2009','A105','/actual_observations/paper_reported/0','Xaa-Pro negatives and Arg/Lys positives retain distinct length/derivative tolerance.'),
('DUF1537_Zhang_2016','A102','/actual_observations/paper_reported/0','Uninformative domain search is a boundary example for structural transfer, not positive functional correspondence.'),
('DUF1537_Zhang_2016','A105','/actual_observations/paper_reported/2','Retained biochemical kinase assignment is source-reported; structural sites alone are not chemistry.'),
('EF1143_Vorontsov_2011_2014','A105','/actual_observations/paper_reported/0','dGTP and metal-conditioned hydrolysis are measured requirements, not a universal physiological role.'),
('EUBREC0560_PG1327_Fleischman_2014','A102','/actual_observations/paper_reported/0','Structural-neighborhood interpretation is bounded by distinct screened and kinetic specificities.'),
('EUBREC0560_PG1327_Fleischman_2014','A105','/actual_observations/paper_reported/0','Half-reaction screening and kinetics support the tested different aminotransferases.'),
('EUBREC2651_Fleischman_2014','A105','/actual_observations/paper_reported/0','PLP half reaction and failed expected glutamate separate proxy chemistry from complete conversion.'),
('EUBREC2651_Fleischman_2014','A110','/actual_observations/paper_reported/0','Observed carrier conversion, phosphate elimination and missing expected product constrain a complete reaction account; physiological-direction substrate remains unavailable.'),
('HpbD_Zhao_2013','A102','/actual_observations/paper_reported/0','Neighbor binding-protein model refined a local structural substrate hypothesis; model is not activity.'),
('HpbD_Zhao_2013','A105','/actual_observations/paper_reported/1','Epimerization and ligand structure support bounded hydroxyproline-betaine chemistry.'),
('HpbD_Zhao_2013','A109','/actual_observations/paper_reported/2','Native genetics/metabolomics distinguish salt-dependent retention from catabolism in the tested organism.'),
('Lmo2620_Bh0225_Xiang_2012','A102','/actual_observations/paper_reported/1','Family/pocket correspondence suggests missing-library substrates and bounds docking negatives.'),
('Lmo2620_Bh0225_Xiang_2012','A105','/actual_observations/paper_reported/2','Synthesized pentose substrates were positive while unavailable hexonic substrates stay untested.'),
('MJ0577_Zarembinski_1998','A102','/actual_observations/paper_reported/0','Uninformative fold matches bound structural function transfer; bound ATP alone does not solve switch function.'),
('MJ0577_Zarembinski_1998','A105','/actual_observations/paper_reported/1','Retained binding versus absent purified-alone hydrolysis are different measured propositions.'),
('MS53_0025_MAG6390_Korczynska_2014','A105','/actual_observations/paper_reported/1','Screened phosphorylated-lactone hydrolysis is retained with incomplete-results inspection limit.'),
('TM0936_Hermann_2007','A102','/actual_observations/paper_reported/0','Shared core accompanies negative cytosine derivatives, bounding exact structural transfer.'),
('TM0936_Hermann_2007','A105','/actual_observations/paper_reported/1','Actual positive and negative substrate tests distinguish product chemistry from docking priorities.'),
('TT1927b_Handa_2005','A101','/actual_observations/paper_reported/1','Close-homolog contact conservation differs from remote-family variation and limits ligand transfer.'),
('hemk_prmc','A101','/actual_observations/1','YfcB homolog identity preserves related chemistry while its RF negative blocks exact substrate transfer.'),
('hemk_prmc','A103','/actual_observations','Recurrent but nonuniversal overlapping prfA-hemK organization supports bounded RF association.',0,'context_hemk_prmc_2002'),
('hemk_prmc','A105','/experiment_dependence','Published RF methylation and GGQ controls are the activity/site evidence distinct from neighborhood.',0,'context_hemk_prmc_2002'),
('pa0142','A101','/actual_observations/0','Changed recognition-pair subcluster motivates bounded transfer and screening.',0,'seq_pa0142_8oxoguanine'),
('pa0142','A102','/actual_observations/paper_reported/2','Failed target crystallization leaves a homolog structure/model, not a target structure.',0,'Pa0142_Hall_2010'),
('pa0142','A105','/actual_observations/1','Purified product-identified 8-oxoguanine conversion remains distinct from native disposal.',0,'seq_pa0142_8oxoguanine'),
('quef','A101','/actual_observations/3','Alignment separates QueF motif and lost FolE sites without establishing chemistry.',0,'seq_queF_not_folE'),
('quef','A104','/actual_observations','Archaeal absence is interpreted against the shared intermediate and organism pathway boundary.',0,'context_quef_nitrile_reductase_2005'),
('quef','A105','/actual_observations/2','Authentic preQ1 product identifies measured nitrile reduction.',0,'seq_queF_not_folE'),
('rida','A102','/actual_observations/1','Ligand-bound TdcF is a comparator for positioning, not a universal catalytic mechanism.',0,'seq_yjgF_ridA_salmonella'),
('rida','A105','/actual_observations/0','IlvA-generated intermediate conversion is measured molecular output.',0,'seq_yjgF_ridA_salmonella'),
('rida','A106','/actual_observations/2','Arg105 versus other variants and complementation distinguish residue contribution, with mechanism limits.',0,'seq_yjgF_ridA_salmonella'),
('seq_codA_isoguanine_failed_candidate','A105','/actual_observations/3','Recombinant CodA product identity supports capacity; insoluble archaeal candidate is not enzyme-null.'),
('seq_codA_isoguanine_failed_candidate','A106','/actual_observations/2','Candidate negatives and peptide-guided attribution distinguish extract source from an expressed insoluble candidate.'),
('seq_hisZ_lactococcus','A104','/actual_observations/0','HisZ occurrence tracks explicit HisG-length architecture in the examined comparison.'),
('seq_hisZ_lactococcus','A106','/actual_observations/1','Subunit omission/complementation distinguishes joint system capacity from either subunit alone.'),
('seq_hisn_impase_discrimination','A101','/actual_observations/3','More-similar motif-deficient failure bounds overall-similarity specificity transfer.'),
('seq_hisn_impase_discrimination','A106','/actual_observations/0','Overexpression rescue and native-loss residual distinguish capacity from native backup responsibility.'),
('seq_hutW_vibrio','A101','/actual_observations/0','HutW-ChuW correspondence motivates transfer but does not transfer detailed redox products.'),
('seq_hutW_vibrio','A103','/actual_observations/0','Related heme-utilization operon organization supports bounded process association.'),
('seq_hutW_vibrio','A105','/actual_observations/1','Reconstituted heme degradation, iron release and SAM-turnover products are actual measured outputs.'),
('seq_hutW_vibrio','A110','/actual_observations/2','Changed product reduction state and NADPH support constrain donor/product obligations.'),
('seq_ptmvd_m3k_picrophilus','A101','/actual_observations/1','Conserved versus divergent recognition regions bound MVD transfer.'),
('seq_ptmvd_m3k_picrophilus','A105','/actual_observations/2','Measured mevalonate-3-phosphate identifies phosphorylation rather than inherited decarboxylation.'),
('seq_ptmvd_m3k_picrophilus','A110','/actual_observations/3','Separate spontaneous decomposition prevents assigning all final-product chemistry to enzyme action.'),
('seq_pucM_transthyretin_like','A101','/actual_observations/2','Human transthyretin fails the source effect, bounding family-name function transfer.'),
('seq_pucM_transthyretin_like','A105','/actual_observations/0','Measured uricase-product hydrolysis supplies actual molecular support.'),
('seq_queFL_archaeosine','A101','/actual_observations/0','Related-family comparison and differing engineered tRNA product bound QueF function transfer.'),
('seq_queFL_archaeosine','A105','/actual_observations/1','Adduct formation on both substrates differs from productive tRNA-bound synthesis.',1),
('seq_queFL_archaeosine','A110','/actual_observations/2','Ammonium versus glutamine directly constrains the tested nitrogen-input account.',1),
('seq_triA_atzA_near_identity','A101','/actual_observations/1','Nine substitutions plus divergent reactions defeat near-identity specificity sufficiency.'),
('seq_triA_atzA_near_identity','A105','/actual_observations/2','Bounded opposite substrate panels supply actual molecular specificity evidence.'),
('seq_yadB_gluQRS_ecoli','A101','/actual_observations/0','Lost anticodon architecture constrains GluRS-like target/property transfer.'),
('seq_yadB_gluQRS_ecoli','A105','/actual_observations/2','Matched Q34 substrates distinguish binding from productive modification.',1),
('seq_ygbP_ispD_ecoli','A101','/actual_observations/1','Characterized Acs1-related domain supplies a bounded correspondence hypothesis.'),
('seq_ygbP_ispD_ecoli','A104','/actual_observations/2','Homolog occurrence tracks the nonmevalonate pathway in examined genomes.'),
('seq_ygbP_ispD_ecoli','A105','/actual_observations/3','Recombinant product formation supplies exact activity independently of the discovery query.'),
('seq_yggH_trmB_ecoli','A101','/actual_observations/0','Cofactor-binding similarity motivates characterization while lacking exact catalytic signatures.'),
('seq_yggH_trmB_ecoli','A105','/actual_observations/1','Radiolabel/TLC assigns tested tRNA m7G production.'),
('seq_yggH_trmB_ecoli','A106','/actual_observations/2','Substrate G46A and gene-disruption effects constrain site and component contribution.'),
('seq_yjeH_exporter_ecoli','A101','/actual_observations/0','Actual APC comparison is bounded by branch assignment rather than flux inference.'),
('seq_yjeH_exporter_ecoli','A105','/actual_observations/1','Loaded-cell export and intracellular pools retain engineered expression and substrate conditions.'),
('seq_yrdC_tsaC_ecoli','A101','/actual_observations/0','Family/HypF chemistry is a candidate hypothesis rather than a complete t6A mechanism.'),
('seq_yrdC_tsaC_ecoli','A106','/actual_observations/1','Loss and complementation identify a bounded contribution to measured t6A.'),
]
for t in T:add(*t)
# Discriminating follow-up cases: curated against the actual support relation,
# not the presence of a protein/reaction/phenotype word in the case title.
F=[
('archaeal_hvo_pilin_processing_assembly','A106','/source_observations/4/published_wetlab','Processing-competent expressed hybrid loses assembly/adhesion; unexpressed hybrid is not an assembly-negative.',1,None,True),
('archaeal_hvo_pilin_processing_assembly','A109','/source_observations/3/published_wetlab','Native matched deletions and restoration separate motility and condition-dependent adhesion.',0,None,True),
('archaeal_pibd_flak_recognition_access','A105','/source_observations/2/published_wetlab','Matched leader cleavage panel and separately bounded rescue distinguish specificity from assembly.',2,None,True),
('archaeal_pibd_flak_recognition_access','A108','/source_observations/1/published_wetlab','Functional sided-access reporters retain heterologous membrane/burial/leakage limitations.',1,None,True),
('causal_actS_stress_activation','A106','/actual_observations/0','Isolated-negative versus paired-positive cleavage supports activation rather than copied hydrolysis.'),
('causal_actS_stress_activation','A109','/actual_observations/2','Deletion suppresses lysis only in the tested envelope-stress background; direct LdtF regulation remains unknown.'),
('causal_cas2_spacer_acquisition','A106','/key_observations/2/observation','Defined integration and interface/catalytic contrasts separate component contribution from nuclease assumptions.',1),
('causal_cas2_spacer_acquisition','A105','/key_observations/3/observation','Radiolabel/disintegration/3-prime-OH controls authenticate covalent integration rather than migration.',1),
('causal_envC_activation','A106','/actual_observations/1','Stable localized variants with lost paired amidase activation constrain component action.'),
('causal_envC_activation','A102','/actual_observations/0','Lost LytM metal machinery bounds fold-to-peptidase transfer.'),
('causal_nlpI_scaffolding','A105','/actual_observations/0','Purified binding is measured, while pairwise binding alone cannot establish simultaneous assembly.'),
('causal_nlpI_scaffolding','A106','/actual_observations/1','Preformed partner complexes and controls support ternary scaffolding and selective output effects.'),
('causal_tsaE_turnover','A106','/actual_observations/1','Retained ATPase with lost repeated t6A synthesis separates hydrolysis from productive coupling.',1),
('chem_bcd_etf','A105','/actual_observations/1/result','Omission and donor controls identify actual coupled reduction conditions.'),
('chem_bcd_etf','A110','/actual_observations/2/result','Measured donor/acceptor stoichiometry constrains ideal coupled account; extrapolation is explicit.'),
('chem_bioc','A105','/actual_observations/1/result','Carrier/substrate panel and methyl-ester product identity constrain physiological carrier inference.'),
('chem_dsr_terminal','A105','/actual_observations/1/result','Reduced protein and sulfide products authenticate terminal reaction with incomplete recovery.'),
('chem_dsr_terminal','A110','/actual_observations/0/result','Donor/substrate omission account constrains coupled electron input while native quinol/potential remain unknown.'),
('chem_f420_precursor_partner','A105','/actual_observations/2/result','Measured coupled output depends on actual cognate downstream partner.',2),
('chem_f420_precursor_partner','A106','/actual_observations/2/result','Changing downstream partner selectively changes apparent upstream preference.',2),
('chem_f420_precursor_partner','A110','/actual_observations/0/result','Dehydro versus mature F420 and regeneration obligations constrain broad precursor transfer.'),
('chem_hemq','A105','/actual_observations/1/result','Time-resolved identified conversion and product destruction resolve a misleading endpoint negative.',1),
('chem_hemq','A110','/actual_observations/0/result','Metal-substrate and oxidant alternatives constrain reaction inputs without identifying universal native supply.'),
('chem_hydabc','A105','/actual_observations/0/result','Actual combined donors and FMN support tested H2 output.'),
('chem_hydabc','A110','/actual_observations/1/result','Limited-donor stoichiometry and carryover caveats constrain electron accounting, not microscopic bifurcation.'),
('chem_mvh_hdr','A105','/actual_observations/0/result','Defined H2 plus heterodisulfide dependence is a measured molecular relationship.'),
('chem_mvh_hdr','A110','/actual_observations/1/result','Limited-substrate carrier ratio constrains coupled electron output with disclosed uncertainty.'),
('chem_nfnab','A105','/actual_observations/0/result','Bidirectional donor/acceptor dependence supplies actual molecular support.'),
('chem_nfnab','A106','/actual_observations/2/result','Separated/reconstituted subunits constrain coupled component contribution.'),
('chem_nfnab','A110','/actual_observations/1/result','Measured paired-carrier stoichiometry constrains reversible net chemistry, not native flux.'),
('chem_queg','A105','/actual_observations/1/result','Identified oQ-to-Q conversion is distinct from incomplete-preparation inactivity.'),
('chem_queg','A106','/actual_observations/0/result','Sequential cofactor restoration identifies competence requirements without native donor assignment.'),
('chem_ubiuv_oxygen_donor','A110','/actual_observations/1/result','Isotope placement constrains pathway atom source while purified hydroxylation/electron acceptor remain unknown.'),
('chem_ubiuv_oxygen_donor','A106','/actual_observations/0/result','Genetic precursor loss and supplementation support pathway dependence rather than isolated catalysis.'),
('chem_ubix','A105','/actual_observations/0/result','Identified modified flavin establishes actual UbiX synthesis rather than decarboxylase attribution.'),
('chem_ubix','A106','/actual_observations/1/result','Protein-free filtrate and oxidation-state contrast attribute activation to a transferable product.'),
('csiD_glutarate_hydroxylase','A105','/actual_observations/0','Identified stereochemical product separates activity from mere adjacency/induction.'),
('csiD_glutarate_hydroxylase','A106','/actual_observations/1','Deletion-conditioned metabolite accumulation supports a contribution distinct from tube capacity.'),
('fluc_fluoride_channel','A105','/actual_observations/0','Reconstituted ion flux and channel currents distinguish channels from tolerance alone.'),
('lhgO_electron_acceptor_correction','A105','/actual_observations/0','Competent oxygen-negative followed by quinone-positive revises acceptor assignment.'),
('lhgO_electron_acceptor_correction','A106','/actual_observations/1','Deletion/restoration attributes membrane activity to the component without proving integral topology.'),
('pxpABC_oxoproline_disposal','A103','/actual_observations/1','Actual neighboring organization is one bounded input to the three-component hypothesis.'),
('pxpABC_oxoproline_disposal','A106','/actual_observations/2','Complete three-protein reconstitution supports collective capacity without assigning all chemistry to each component.'),
('pxpABC_oxoproline_disposal','A110','/actual_observations/2','ATP-dependent versus ATP-independent direction concern constrains physiological disposal feasibility.'),
('pxpT_pxpR_access_and_sensing','A105','/actual_observations/2','Purified ligand binding and four comparators support bounded recognition.'),
('pxpT_pxpR_access_and_sensing','A106','/actual_observations/1','Signed promoter/motif and expression perturbations support repression beyond induction alone.'),
('pxpT_pxpR_access_and_sensing','A109','/actual_observations/0','Allele-linked 5-OP growth and restoration support conditioned uptake involvement rather than direct transport.'),
('reg_iscR_state_target_specificity','A105','/actual_observations/5/observation','Measured retained-reference affinity plus expanded target set distinguishes specificity from one affinity.',3),
('reg_iscR_state_target_specificity','A106','/actual_observations/3/observation','Matched binding-site and cluster/abundance perturbations separate occupancy from productive signed control.',2),
('reg_iscR_state_target_specificity','A107','/actual_observations/10/observation','Controlled-expression reporters retain state/atmosphere-dependent molecular response without equating total abundance with activity.',4),
('replacement_bioG','A105','/actual_observations/0/observation','Defined acyl-ACP cleavage plus soluble inactive control supports bounded molecular conversion.'),
('replacement_bioJ','A105','/actual_observations/0/observation','Product mass and extract DTB distinguish exact conversion from rescue alone.'),
('replacement_bioJ','A109','/actual_observations/0/observation','Native growth/host defects and biotin relief constrain condition-dependent contribution.'),
('replacement_bioK','A106','/actual_observations/0/observation','Controlled heterologous restoration supports replacement capacity; insolubility leaves isolated chemistry unresolved.'),
('replacement_bioV','A105','/actual_observations/0/observation','Cognate-ACP conversion with mass/DTB supports chemistry; no transformants does not establish essentiality.'),
('replacement_bioV','A106','/actual_observations/0/observation','Subcloning separates gene attribution within the rescuing library fragment.'),
('replacement_bioZ','A105','/actual_observations/0/observation','Identified alternate input condensation prevents misassigning demethylase from rescue.'),
('replacement_bioZ','A106','/actual_observations/0/observation','Native loss/C115S and precursor-supply perturbations support defined pathway contribution.'),
('replacement_bioZ','A110','/actual_observations/0/observation','Identified distinct entry reactants constrain the local chemical account without cellular energy/flux inference.'),
('replacement_cobY','A105','/actual_observations/0/observation','GMP-transfer positive and kinase-negative separate partial activity replacement.'),
('replacement_cobY','A109','/actual_observations/0/observation','De-novo versus aerobic salvage rescue bounds the conditioned organism contribution.'),
('replacement_folA_bypass','A106','/actual_observations/1/observation','Active re-expression and nutrient contrasts separate restored enzyme from bypass allocation.'),
('replacement_folA_bypass','A109','/actual_observations/0/observation','Lineage-specific supplement dependence prevents universal recovered-DHFR attribution.'),
('replacement_folE2','A105','/actual_observations/0/observation','Measured metal-supported activity does not measure native occupancy.'),
('replacement_folE2','A106','/actual_observations/0/observation','Combined deletions distinguish overlapping capacity and route-specific growth rescue.'),
('replacement_folM','A105','/actual_observations/4/observation','Matched substrate and donor panel distinguish favored capacity from side folate activity.',1),
('replacement_folM','A106','/actual_observations/3/observation','Deletion/restoration of engineered cofactor-dependent rescue identifies contribution without native exported-product use.',1),
('replacement_hemJ','A106','/actual_observations/0/observation','Loss, validated replacement and combined fractions support cellular pathway contribution rather than isolated enzyme proof.'),
('replacement_hemJ','A109','/actual_observations/1/observation','Trophic-state-specific replacement and negative isolated assay remain separate conditioned propositions.',1),
('replacement_lysU','A109','/actual_observations/1/observation','Complete later tested nonphenotype limits historical universal heat requirement.',1),
('replacement_queH','A103','/actual_observations/0/observation','Q-pathway neighborhoods and QueA fusions support bounded process organization.'),
('replacement_queH','A104','/actual_observations/0/observation','Inverse QueG/DUF208 distribution supplies bounded replacement association.'),
('replacement_queH','A106','/actual_observations/2/observation','Combined versus single deletions distinguish overlapping native Q contribution.'),
('replacement_queH','A105','/actual_observations/5/observation','Substrate loss without Q is a molecular-output boundary rather than proven productive catalysis.',1),
('replacement_thyX','A106','/actual_observations/0/observation','ThyA versus ThyA+FolA restoration distinguishes replacement and regeneration dependence.'),
('replacement_thyX','A110','/actual_observations/0/observation','Regeneration rescue constrains pathway-equivalence account without identifying sole native reductase.'),
('spatial_amic_amia_export_septal_access','A108','/actual_observations/0/observation','Functional fusion and Tat/export measurements support actual compartment access.'),
('spatial_amic_amia_export_septal_access','A106','/actual_observations/1/observation','Induced rescue despite lost concentration separates export/targeting/catalytic contribution.'),
('spatial_ccda_dsbd_acceptor_range','A101','/actual_observations/1/observation','Failed alternate acceptors limit homolog-family transfer of the complete repertoire.'),
('spatial_ccda_dsbd_acceptor_range','A106','/actual_observations/0/observation','Reciprocal rescue and partner requirements support the defined component relationship rather than each direct transfer pair.'),
('spatial_dsbd_topology_revision','A108','/actual_observations/2/observation','Orientation-controlled access supports sidedness while dynamic encounter remains unresolved.'),
('spatial_ftsw_bpbp_job','A108','/actual_observations/0/observation','Reconstituted sided access with leakage controls is bounded access evidence.'),
('spatial_ftsw_bpbp_job','A105','/actual_observations/1/observation','Product-authenticated polymerization depends on cognate partner, separate from earlier access readout.',1),
('spatial_ftsw_bpbp_job','A106','/actual_observations/2/observation','Helix/interface and catalytic contrasts identify productive partner contribution.',1),
('spatial_murj_lipidII_access','A108','/actual_observations/1/observation','Sequential barrier controls locate substrate access prerequisite.'),
('spatial_murj_lipidII_access','A106','/actual_observations/0/observation','Selective functional allele inhibition with product/access change supports component contribution.'),
('spatial_trxa_relocation_role','A108','/actual_observations/0/observation','Engineered export measurements do not establish native TrxA localization.'),
('spatial_trxa_relocation_role','A106','/actual_observations/1/observation','Corrected genotype and trapped partner plus oxidation output repair the DsbB-dependence interpretation.',1),
('spec_aquifex_hfp_coupling_contamination','A105','/actual_observations/0/result','Staged versus one-pot output distinguishes partial conversion from pathway-compatible activity.'),
('spec_aquifex_hfp_coupling_contamination','A106','/actual_observations/2/result','Unrelated-preparation controls and contaminant MS defeat enzyme attribution despite purification persistence.'),
('spec_cysq_pap_not_imp','A105','/actual_observations/1/result','Sensitive substrate panel and preference bound side-activity/native-substrate inference.'),
('spec_cysq_pap_not_imp','A109','/actual_observations/3/result','Recovered native deletion nonphenotype retains suppressor/condition alternatives.',1),
('spec_frsa_disputed_pdc_native_unknown','A105','/actual_observations/0/result','Orthogonal competent negatives revise claimed PDC; artificial positives do not solve native function.'),
('spec_frsa_disputed_pdc_native_unknown','A111','/actual_observations/1/result','Unknown density despite ligand model bounds structural functional inference.'),
('spec_suhb_catalysis_vs_rrna','A106','/actual_observations/2/result','Endogenous recruitment and reporter contrast bound component contribution rather than inherited IMPase growth explanation.',1),
('spec_suhb_catalysis_vs_rrna','A105','/actual_observations/3/result','Purified NusA/RNA binding and complex assembly remain molecular measurements with mechanism limits.',2),
('spec_yigl_conditional_b6','A105','/actual_observations/1/result','Purified PNP hydrolysis differs from noncatalytic suppressors and native responsibility.'),
('spec_yigl_conditional_b6','A106','/actual_observations/2/result','Matched deletion/extract/metabolite effects constrain responsibility under normal versus forced load.'),
('spec_yigl_conditional_b6','A109','/actual_observations/4/result','Stress/media-specific competition prevents replacing one conditioned role with another.',1),
('spec_yihu_native_sulfonate','A105','/actual_observations/3/result','Favored SLA kinetics and GAP negative constrain substrate assignment; old SSA capacity remains real.',3),
('spec_yihu_native_sulfonate','A107','/actual_observations/2/result','SQ induction plus native active-protein identity supports deployment in the matched pathway condition.',1),
('spec_yjjg_conditional_salvage_cleanup','A106','/actual_observations/0/result','Deletion/restoration and residual extract activity distinguish contribution from exclusive capacity.'),
('spec_yjjg_conditional_salvage_cleanup','A109','/actual_observations/2/result','Casamino-acid enrichment and alternate route bound the salvage growth contribution.',2),
('sulfoglycolysis_selectivity','A105','/actual_observations/2/result','NMR/exchange/synthetic reference authenticate additional product independently of the protein label.',1,'spec_yihs_sulfosugar_selectivity'),
]
for t in F:add(*t)
skip('replacement_purT','Primary abstract only: scanned main Results and underlying data were not inspected. Keep the formate/double-mutant contrast in retained review coverage, but do not promote it to fully curated instruction support.')
# Record a scope gap explicitly, without inventing another entry or forcing a
# direct structure/contact measurement into comparator function transfer.
for g in ['DUF1537_Zhang_2016','TT1927b_Handa_2005','chem_f420_precursor_partner','replacement_queH','causal_cas2_spacer_acquisition']:
 if g in curated:curated[g]['gaps'].append('Direct structural ligand/contact/identity constraints are not equivalent to function transfer from a characterized structural comparator. These10 draft bodies do not fully define that separate reusable support relation; mapped structural cases here are explicitly limiting examples or use another justified route. No additional entry is adopted.')
expected=set(x['partitions']['transfer']['case_groups']+x['partitions']['discriminating_followups']['case_groups'])
assert set(curated)==expected,(set(curated)^expected)
(OUT/'curation_transfer_followups.json').write_text(json.dumps(dict(status='new_review_draft_mapping_judgments_not_adopted',groups=[curated[g] for g in sorted(curated)]),ensure_ascii=False,indent=2)+'\n')
print('curated',len(curated),'groups',sum(len(g['mappings']) for g in curated.values()),'route links')
