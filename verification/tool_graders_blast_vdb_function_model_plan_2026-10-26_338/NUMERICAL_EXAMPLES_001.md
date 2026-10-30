# Checkable numerical examples and proposed tests

2026-10-26. Plan-only companions to PROPOSED_CONTRACT_001.md. **All data below are supplied/synthetic calculation examples, not native database runs, measurements acquired by this task, or evidence that production integration passes.** No test or reproduction was run. Exact fractions are arithmetic oracles; decimals are explanatory. `A` and `B` mean literal Functions `{namespace:"fixture_function",value:"A"}` and `{namespace:"fixture_function",value:"B"}`. All original HSP/member/source references must remain in a future complete fixture, even when a table abbreviates their names.

## 1. blastn_vdb whole-member assignments, duplicates and census

Use a bound nucleotide query and three uniquely identified reported-origin members from the same explicitly selected snapshot/filter population. Full member sequences are supplied, source-linked and checked. `a1` and `a2` contain exactly the same full nt sequence; `b1` differs. Each A member has an explicit whole-sequence A scope declaration; b1 has B. A feature or title alone is not that declaration. Each listed HSP is wholly within its member and its reference traceback agrees with the actual source sequence. The supplied bit scores are fixture values, not values recalculated from these descriptions.

| Original member / HSP | Full target identity | Assigned function | Native score (bits) | Calculation use |
|---|---|---|---:|---|
| a1 / h0 | seq-a | A | 22 | Winning A observation |
| a1 / h1 | seq-a | A | 18 | Retained additional original HSP; no summed mass |
| a2 / h0 | seq-a | A | 21 | Proven duplicate target; retained original association |
| b1 / h0 | seq-b | B | 20 | Winning B observation |

Baseline target units=2, source entities=3, eligible HSPs=4, groups=2. Sample facts/dependence edges do not alter this baseline. T=1 bit, priors=null means pi_A=pi_B=1/2. Each group has one function, hence Z=1. B_F=22. M_A=1; M_B=2^(-2)=1/4. Prior-weighted masses are 1/2 and 1/8; their denominator is 5/8. **P_A=4/5; P_B=1/5.** No result is called calibrated annotation probability.

Independently supply a complete census enumeration of six member instances. a1/a2 share one target; three other distinct full targets are assigned A, and one distinct target is assigned B. Thus there are five unique full targets: N=5, N_A=4, N_B=1. Exact source dataset, selected_input, snapshot, sra_mode, include_filtered_reads, annotation snapshot and each observed entity/assignment mapping match. Census fractions are 4/5 and 1/5. With the same target partition, R_A=(1/2)*1/4=1/8; R_B=(1/2)*(1/4)/1=1/8. Their sum is 1/4. **C_A=C_B=1/2.** Six member instances must not replace N=5 or N_A=4; the three reported hit members must not replace a census.

Change only saved model T from1 to2 bits. M_A=1, M_B=1/2; P=(2/3,1/3). R=(1/8,1/4); **C=(1/3,2/3)**. The exact original HSP scores, sheet bytes, source identity and original native receipt stay unchanged. Only the new model/calculation generation and its numerical results differ.

Additional priors test: selected raw weights A=1,B=0 normalize to1,0. M_B remains1/4. P_B and C_B are model-selected0; no native negative-function assertion is inferred. Both raw weights0 is a structural model rejection.

## 2. Feature containment and unrelated annotation in blastn_vdb

The contig carries explicit feature F at nt interval[10,20) with function A. Supply its complete nt sequence and exact member join. h_good has all non-gap reference columns in[12,18), six paired nt and score18. h_broad has columns in[0,30), including F, and score60. h_unrelated lies in[30,40), where an unrelated feature G has function B.

- h_good supplies A's full native18-bit score. F coverage remains6/10 separately.
- h_broad supplies no feature-function score for F. The source overlap count10 and native60 bits survive; do **not** create a20-bit score by multiplying60 by10/30.
- h_unrelated can supply B only if G itself is supplied, explicitly assigned, fully identity-qualified and the entire HSP is attributable to G. It cannot supply A because another feature on the same contig has A.
- If the only retained annotation is F and only h_unrelated exists, there is no A contribution. Whole-member A is also unavailable without an explicit whole-member scope declaration.
- A column opposite a query gap but outside F still makes h_broad unqualified for F; testing paired-column containment alone is insufficient.

These are separate feature and whole-sequence views. No sum of the two distributions is defined.

## 3. tblastn_vdb coding features, opposite strands and multiple frames

Query protein is `PMAKPP` (six aa); an HSP can align positions1..3 in zero-based query coordinates without implying full query coverage. Use code1 and explicit codon_start1. Original source coordinates and native frame remain retained.

| Member and exact feature | Full source nt | Source segment / strand | Oriented complete feature | Translation | Qualified native score |
|---|---|---|---|---|---:|
| forward/F | CCCATGGCTAAACCCCCC | [3,12), +1 | ATGGCTAAA | MAK | 30 |
| reverse/Fcopy | TTTAGCCATAAA | [0,9), -1 | ATGGCTAAA | MAK | 29 |
| reverse/G | CAGACCCATCCC | [0,9), -1 | ATGGGTCTG | MGL | 28 |

F and Fcopy are explicitly assigned A, G is explicitly assigned B. Their original oriented codon coordinates are respectively `[3,4,5],[6,7,8],[9,10,11]`; `[8,7,6],[5,4,3],[2,1,0]`; and `[8,7,6],[5,4,3],[2,1,0]`. Native translated reference symbols must equal MAK, MAK and MGL respectively; query mismatches against MGL remain ordinary measured mismatches. Every HSP's own native frame and source endpoints must generate those same triplets.

F and Fcopy have identical complete oriented nt, code, codon_start and translation identity. They are **one translated-feature target unit** despite opposite original strands and different parent contigs. Keep all three feature source entities, both A coordinate maps and their original HSPs. G is a different target. With T=2, B_F=30, M_A=1,M_B=1/2; uniform priors give **P=(2/3,1/3)**. Treating source strand as target identity would incorrectly produce A mass1+2^(-1/2) and raise its weight; that behavior is specifically forbidden.

Add another valid F HSP with score27: A stays30. Add an HSP reported in an incompatible frame with score40: retain40 as native data, but it does not lend a score to F. Add a broad correct-frame HSP over the entire forward18-nt member with score50: it overlaps F but is not contained, so it also cannot replace F's30. A separate correctly located feature in another frame can have its own feature target only when its own supplied coding map and full HSP correspondence qualify; sharing a contig does not make it A.

For the nucleotide feature model, the comparison identity is the oriented full feature nt with coding=null; no translation or amino-acid interpretation is made. For translated features the coding tuple is additionally required. Whole-member identity is the exact full stored nt sequence with coding=null, without reverse-complement canonicalization. A whole-member tblastn assignment still needs its explicit complete member-wide CDS witness for HSP attribution. For member `ATGGCTAAA`, a separate explicit whole-member A assignment plus exact CDS[0,9), strand+1, code1, codon_start1, translationMAK qualifies the MAK HSP; the same member/function without that witness produces coding_witness_missing. A feature A annotation alone does not create that whole-member declaration.

## 4. What the optional source cap loses

Three **different proven full targets**, all at20 bits: gene x has A in originating sampleS1; gene y has B inS1; gene z has A inS2. These sample links are exact source facts. They do not demonstrate duplicate genes. There are no duplicate targets; three target units and three original entity/HSP contributions remain inspectable in either result.

| Calculation | x:A mass | y:B mass | z:A mass | M_A | M_B | P_A | P_B |
|---|---:|---:|---:|---:|---:|---:|---:|
| target_duplicates_only | 1 | 1 | 1 | 2 | 1 | 2/3 | 1/3 |
| known_source_blocks (S1 cap; S2 cap) | 1/2 | 1/2 | 1 | 3/2 | 1/2 | 3/4 | 1/4 |

The second model caps distinct S1 genes' combined mass at1, losing1/2 of x's A mass and1/2 of y's B mass. It preserves z's full mass. This is the selected statistical assumption; it is not an established independence correction. Distinct features sharing a complete parent contig, and supplied same-library/study/dependent relations, have the same cap interpretation when that model is selected. All exact sample memberships, dependence links, source evidence and target identities remain in the saved components even when the baseline does not use the cap.

Same group, unequal own-function scores: if a selected block has A at20 and B at18, T=1, z=(1,1/4), Z=5/4, its A/B masses are4/5 and1/5 at B_F=20. B must not borrow A's20-bit score and receive1/2. Two equal-score labels on the same target instead split1/2 each. Repeating either metadata row or adding a lower-scoring HSP does not add mass.

Unknown sample relation: the baseline above still uses the proven target identities and gives2/3,1/3. Source-block `withhold_weights` returns null statistical weights with dependency_unknown; `qualify_separate` adds no guessed edge, retains the unknown relation and marks the conditional result partial. Neither option changes a stored sample membership fact.

## 5. Full census partition versus returned-only blocks

Returned target a(A,20 bits) belongs toS1; returned target b(B,20 bits) belongs toS2. Under the selected source-cap model the returned partition has two blocks and M_A=M_B=1. A complete census additionally contains an unreported occurrence of a's exact target inS2. Its full-target duplicate relation connectsS1 andS2 in the census graph. No query HSP exists for that unreported occurrence.

The observed HSPs map into one census block containingA,B. Census-partition masses become M_A^c=M_B^c=1/2. Add one other census block containingA and no observed HSP. Then N=2 blocks, N_A=2,N_B=1; with uniform priors R_A=1/8,R_B=1/4 and C=(1/3,2/3). The unreported block receives no query mass. Preserve returned-only masses1,1, census-partition masses1/2,1/2, the connecting source identities and all census counts. Although this two-function example happens to have the same normalized C if the wrong masses are divided, those intermediate numerical fields expose the mismatch. A third observed function in an unaffected block must expose a changed normalized answer.

Concrete third-function extension: add returned c(C,20 bits) inS3 and its separate census block; now N=3,N_A=2,N_B=1,N_C=1. Uniform priors are1/3. Correct masses=(1/2,1/2,1), rates=(1/12,1/6,1/3), sum7/12, and **C=(1/7,2/7,4/7)**. Incorrect returned-only masses=(1,1,1) would yield **(1/5,2/5,2/5)**. Baseline target-duplicate grouping does not acquire sample edges and does not use this source-cap partition.

## 6. Unknown, partial, zero and contradictory facts

| Supplied situation | Required observable outcome |
|---|---|
| Known member/sequence, eligible HSP20, no function in the scored namespace; plus distinct A20 and B20 targets | Unknown bucket mass1; assigned global mass2; unknown fraction1/3. Conditional represented-function weights remain1/2,1/2. |
| Unannotated duplicate of the known A target | Missing annotation coverage retained; no extra unknown target or mass. |
| Native hit20 with catalogue membership only, or two conflicting reported-origin members | Native geometry/20bits remain. No origin-conditioned function observation or unknown-annotation mass is invented; unknown/ambiguous origin subject count increments. |
| Exact same digest/length claimed but source full symbols conflict | Target identity conflict; no independent fallback group. Retain original proofs/assignments and disable dependent contribution. |
| Feature on another contig or metadata ordinal/function mismatch | Structured assignment_entity_conflict or assignment_function_conflict; no label borrowing. |
| Census absent | P from section1 remains4/5,1/5; all corrected weights null with census_missing. |
| Census enumeration partial, pagination incomplete, or reported_total mismatches rows | Descriptive retained enumeration counts survive. Correction unavailable/contradictory with census_partial or census_count_conflict; no completed denominator from returned hits. |
| Complete census wrong snapshot, selected_input, filter, scope, unit, or annotation snapshot | Entire corrected distribution unavailable with the specific mismatch. Changing source field labels is not repair. |
| Census has no B entry, or positive B hit but N_B=0 | Whole corrected distribution null; preserve A's count but do not normalize only A. B0 is census_zero_conflict, not division by epsilon. |
| Function membership not source-linked to the selected complete enumeration | census_membership_unverified even if a supplied total is numerically plausible. |
| Partial native report retains only A's valid22-bit row | P_A=1 conditional on that retained assigned set; status=partial and report_complete=false. It is not certainty about the query or a bound on the eventual weight. Qualified census facts may still exist; C remains partial. |
| Partial report contains valid A row and malformed B row | Preserve B's original malformed slot and failure. Do not compact its original ordinal or use its unqualified score. A remains a valid partial contribution. |
| Successful source-qualified explicit zero hits | no_reported_hits; observed hit/HSP/target counts0, groups/functions empty, normalized weights null. Census facts and source metadata may remain nonzero. |
| Empty table6, missing report, failed/truncated capture without explicit successful zero-hit evidence | unavailable/partial as actual retained facts permit; never successful zero hits. |

Taxonomy changes, independently supplied target taxon changes, or measured assembly completeness/contamination changes alter their separate v1 components and qualifications. With the same qualified HSP/function/census inputs they do not change these kernel weights. Test that explicitly; do not add categorical confidence weights.

## 7. Numerical boundary cases

- A0 bits and B-2 bits at T=1 are valid finite native values and give the same4/5,1/5 weights as section1. Bit-score0 is not missing.
- Finite assigned score difference2000 at T=1 produces a finite log2 mass-2000 and positive mathematical mass whose linear binary64 output underflows. Retain log2=-2000, linear value=null, linear_status=underflow, issue linear_underflow. The dominated final weight is also retained in log form, not called observed0.
- Scores1 and0 with T=1e-320 are finite inputs but the log2 difference quotient cannot be represented finitely in binary64. Return kernel_arithmetic_out_of_range for the affected stratum's statistical fields, with native1/0 scores, candidate/group counts and qualified census facts preserved. No infinity, NaN, zero substitute, temperature cap or scientific retry is generated.
- Native scores near opposite binary64 extremes can overflow a naive subtraction even before division. Check the mathematical derived result safely; if the declared output log2 is not representable, return the same closed arithmetic failure. A difference that can be represented after safe evaluation must not fail merely because a naive intermediate overflowed.
- Nonfinite source score, T<=0 or nonfinite T fails the closed structural validation. A different valid stratum is not erased by another stratum's arithmetic failure.

## 8. Saved calculation and actual typed returns

The future test must execute the real result-owner/worker/publication/admission path on retained **supplied synthetic artifacts**, not only call the pure calculator or inspect an artifact JSON. No native BLAST operation is needed or permitted by this plan.

For section1 save FunctionSheet v2 under an authenticated retained original attempt, with T=1 generationG1 and an admitted immediate-child result receipt. The original parent's form requests the exact registered execution_blast_database_vdb_function_saved_inputs descriptor source as well as its numerical rows. A newly selected results calculation receives that admitted G1 descriptor (sealed manifest/sheets/collection references, original receipt address/hash and generation identities), selects saved_function_sheet and T=2, and emits generationG2. Assert identical input_interpretation_id and exact saved sheet bytes; differing model/calculation_id; G1's original values and receipt unchanged. Assert zero calls to native execution, observation/polling, transfer/capture, scientific API, native parsers, metadata population, base VDB calculator and FunctionSheet populator in this saved mode. Only the pure new calculator, row projection and normal publication/admission run. New metadata cannot be slipped into saved mode.

The selector is closed, version=native_blast_database_result_selector_vdb_function_v1, with required acquisition, metadata_inputs, retained_sources, projections, vdb_function_model and calculation_input. Its projection can request these actual metrics in familyvdb_function: prior, conditional_function_weight, representation_adjusted_function_weight. The requested form uses the **exact registered** `execution_blast_database_vdb_function_rows` schema plus the registered failures schema as top-level x-source fields; it is not a free-form summary or a handwritten relaxed approximation.

Example delivered G1 A row, in structural notation below. D is G1's actual64-hex calculation_id; R is its actual canonical row identity; S is the publication source reference admitted from the original immediate child. These symbols are explanatory metavariables, not literal valid record references. All keys are required; no hidden fields are omitted. Let P=`/vdb_function/0/components/strata/0/functions/0` and Q=`/vdb_function/0/components/strata/0`.

```text
{
 schema:"native_blast_vdb_function_numeric_row_v1", family:"vdb_function",
 record_key:R,calculation_id:D,
 identity:{search_key:{artifact_key:"report",member_ordinal:null,
   report_index:0,search_pointer:"/BlastOutput2/0/report/results/search"},
   assignment_scope:"whole_sequence",namespace:"fixture_function",
   grouping_model:"target_duplicates_only",
   function:{namespace:"fixture_function",value:"A"},census_key:"census-1"},
 program:"blastn_vdb",
 context:{query_axis_kind:"sequence",reference_axis_kind:"vdb_member",
   stage:null,native_iteration:null,biological_round:null},
 component_refs:[{artifact_role:"calculations",pointer:"/vdb_function/0/components"}],
 native_status:"complete",
 measurements:[
  {name:"prior",value:0.5,numerator:null,denominator:null,unit:"fraction",
   status:"available",reason:null,origin:"derived",complete:true,
   component_pointer:P+"/prior/value"},
  {name:"conditional_function_weight",value:0.8,numerator:0.5,denominator:0.625,
   unit:"fraction",status:"available",reason:null,origin:"derived",complete:true,
   component_pointer:P+"/conditional_function_weight/value"},
  {name:"representation_adjusted_function_weight",value:0.5,
   numerator:0.125,denominator:0.25,unit:"fraction",status:"available",
   reason:null,origin:"derived",complete:true,
   component_pointer:P+"/representation_adjusted_function_weight/value"}
 ],
 booleans:[{name:"calibrated_annotation_probability",value:false,
   status:"available",reason:null,origin:"derived",
   component_pointer:"/vdb_function/0/components/calibrated_annotation_probability"}],
 source_ref:S,observation_ref:null,subject_ref:null,reference_refs:[],
 publication_status:"source_only"
}
```

Include the boolean in the actual selector if this exact row is requested. The full saved row has all declared family metrics; this example is the permitted frozen metric subset. Its component_refs ancestor covers both function cells and the top-level calibration flag. The projection preserves those authentic refs as actually constructed. The real test resolves pointers to the exact frozen saved components and original source/receipt, then validates the actual parent's form, records admission and resolves the admitted row in the receiver. A source_only row has no fabricated annotation observation.

Reject a forged source_ref, altered numeric value, wrong calculation_id, sibling/unreceived saved descriptor or receipt, changed receipt hash, cyclic saved-receipt chain, source-only first-match receipt selection, changed saved artifact bytes, mismatched original target, wrong model version, original v1 sheet presented as FunctionSheet v2, or unsupported version without fallback acquisition. Same record_key from G1/G2 remains two distinct calculation generations. Repeated identical admission is idempotent and manufactures no scientific/monitoring observation. A parent-requested empty row array accompanied by a specific structured failure is allowed; an unavailable value is not replaced with0 to satisfy a form.

Legacy v1 regression must compare exact saved components, numeric rows and receipts under the legacy selected path, including the original function_weight_model unavailable/vdb_function_weight_model_not_defined marker. No retrospective new formula or prior change is inserted into that history.

## 9. Proposed test ownership and acceptance evidence

| Owner/file | Required independent assertions |
|---|---|
| F-input / tests/test_blast_vdb_function_inputs.py | Exact closed shapes; actual ordinal/source/member links; blastn reference-symbol check; feature whole-HSP containment; per-HSP translated geometry/code/phase; reverse-strand target identity; explicit whole scope; sample assignment exclusion; source conflict and missingness retention. |
| F-calc / tests/test_blast_vdb_function_calculators.py | Exact fractions in1,3,4,5; duplicate and multiple-HSP invariance; own-score split; sample-cap opt-in; unknown/prior0/underflow/extreme arithmetic; all census mismatch cases; independent valid strata; deterministic order invariance; parameter-only recalculation. |
| F-wire / tests/test_native_blast_vdb_function_metadata.py | Registered new schema; exact retained byte custody and wire lowering; nonunique premerge/final key conflicts; no new native parser/acquisition; rejected source rows retained; census/assignment snapshot binding. |
| F-integration / tests/test_native_blast_vdb_function_integration.py | Original selected tool/mode and child-owned result binding; complete immutable sheet/components/rows; partial and zero native outputs; actual published source-only rows; old selected v1 unchanged. |
| F-integration / tests/test_native_blast_vdb_function_recalculation.py | Saved authenticated artifacts and received original receipt; G1/G2 identities and unchanged history; no observe/capture/parser/populator/acquisition; closed failures for changed/inaccessible inputs. |
| F-integration / tests/test_native_blast_vdb_function_returns.py | Exact registered form construction, frozen projection, immediate-child receipt admission, receiver resolution, cross-generation separation, tamper/scope denial and idempotent forwarding. |

Existing tests are preserved, including old assertions that the v1 function model is unavailable. These proposed assertions have not been executed. Root must review the contract before fresh implementation workloads are assigned.
