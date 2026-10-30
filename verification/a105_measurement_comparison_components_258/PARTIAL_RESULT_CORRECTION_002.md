# Additive correction002: singular common estimates and descriptive difference uncertainty

This corrects PLAN001's paragraph that withheld the combined estimate along with nonunique weights, and its grouping of difference_variance/standard_uncertainty with common-mean prerequisites. PLAN001 and all original001 artifacts remain byte-for-byte unchanged. This is a proposal, not a production or test change. No interface is released for coding.

## Singular covariance: preserve the identifiable quantities

Write the converted covariance as C=[[a,b],[b,c]], D=L-R and V_D=a+c-2b. Under PSD, V_D=0 implies a=b=c=v>=0: substituting b=(a+c)/2 into det(C)>=0 gives -(a-c)^2/4>=0. Thus the zero-discrepancy-variance case has precisely the stated shared covariance form.

With the declared supported common unbiased-quantity model and L=R=x, every unbiased allocation w_L+w_R=1 gives

- combined estimate w_L*x+w_R*x=x;
- combined variance v*(w_L+w_R)^2=v;
- combined standard uncertainty sqrt(v).

These results are unique despite nonunique weights. The reader/calculator must not choose w_L=w_R=1/2 or any other allocation. weight_left and weight_right remain null with nonunique_gls_weights. z and z² remain unavailable because 0/sqrt(0) and 0/0 are undefined. The source-protocol difference, its variance and standard uncertainty remain 0. The combined value, variance and standard uncertainty are populated, with their existing dependency/contribution identities, rather than inheriting the weight-cell failure.

For v=0, the declared known model gives combined variance0 and standard uncertainty0 exactly. This adds no infinite-precision score, confidence interval, general accuracy claim, or information about an unknown fixed bias. With estimated covariance the analogous displayed variance is a plugin quantity, not proof that actual uncertainty is exactly zero.

With known actual covariance V_D=0 and L!=R under the common unbiased model, retain D and its descriptive variance0 while marking standardized/common-estimate inference inconsistent_deterministic_constraint. Since E[D]=0 and Var(D)=0 in that model, the observed nonzero difference contradicts its deterministic constraint. No pooled mean or variance is inferred from an inconsistent model. A descriptive protocol comparison with distinct expected means can have Var(D)=0 and D!=0 without that common-model contradiction.

An estimated covariance matrix is not automatically the true covariance. Its zero estimated difference variance alone cannot prove a deterministic contradiction in the actual data-generating model. The proposed existing estimated/plugin interpretation remains explicit; any implementation must not promote this case to the known-covariance contradiction without the declared model supporting it.

## Difference variance does not require a common mean

The difference_variance and difference_standard_uncertainty cells describe the selected protocol difference D=L-R. They require supported endpoint scaling/compatible denominators and the authenticated joint covariance of those actual selected estimators, with its proper unit, ownership, status and approximation qualifications. They do not require equal protocol conditions, E[L]=E[R], or common_model selection.

Their formulas remain:

V_D=c_left^2*Cll+c_right^2*Crr-2*c_left*c_right*Clr;

u_D=sqrt(V_D).

This is exactly the variance of a fixed linear contrast, including when the two expectations differ. Random estimator covariance does not automatically account for a systematic protocol difference or unresolved fixed bias. If the joint covariance is estimated, these are explicitly plugin variance/uncertainty quantities. Source SD/SEM and unrelated marginal uncertainty still do not supply missing joint covariance.

The proposed standardized_difference and squared_standardized_difference retain their narrower common-estimand/model meanings. A protocol difference variance being available does not enable those common-condition agreement cells or a common pooled mean. No new generic standardized protocol score is introduced. For Nfn, the original covariance remains absent and estimate-scale limitations remain unchanged; this correction supplies no new scientific number.

## Exact formula/meaning/domain/schema proposal

The new complete replacement resources are *_SCHEMA_002.json. Each remains standalone with local #/$defs references and a new plan002 root resource identity. Selection shape and function signatures are unchanged; the root $id distinguishes this draft without claiming a deployed format migration.

The exact complete component map is COMPONENT_FORMULAS_AND_MEANINGS_002.json. Its changed entries are:

| Component | Exact proposed formula | Exact scope/meaning |
|---|---|---|
| difference_variance | c_left^2*Cll+c_right^2*Crr-2*c_left*c_right*Clr | Variance of the linked reported-protocol difference under the actual joint selected-estimator covariance; no common-condition or common-mean equivalence is required. |
| difference_standard_uncertainty | sqrt(V_D) | Square root of that reported-protocol difference variance; no common-mean model or sampling distribution is inferred. |
| combined_estimate | if(V_D>0,w_L*L+w_R*R,if(V_D==0&&D==0,L,unavailable)) | Common unbiased quantity estimate under the declared covariance model; for V_D=0 and L=R the shared value is unique even when the unbiased weight allocation is nonunique. |
| combined_variance | if(V_D>0,(V_L*V_R-C_LR^2)/V_D,if(V_D==0&&D==0,V_L,unavailable)) | Variance of the common estimate under the declared covariance model; for V_D=0 and L=R, PSD implies V_L=V_R=C_LR=v and every unbiased weight allocation has variance v. |
| combined_standard_uncertainty | sqrt(V_combined) | Square root of that common-estimate variance, including zero under a declared known zero-variance model; nonunique weights do not erase this quantity. |

The piecewise strings are formula identifiers/descriptions, not a new expression evaluator. The calculator applies closed explicit branches after existing model/units/covariance validation. The singular branch is eligible only with the needed common-model applicability and exact converted-covariance relationships; missing prerequisites cannot enter it.

SHEET_SCHEMA002 updates the formula enum and the component-specific formula const for combined_estimate and combined_variance. Existing cell numerical-state constraints are unchanged: combined cells are populated with their real numeric results, while individual weight and standardized cells can independently remain unavailable.

PLAN_DOMAINS002 replaces the prospective degeneracy reason degenerate_equal_estimate_covariance with the more precise nonunique_gls_weights, used only for unavailable weight allocation in the equal-estimate singular case. This is not an implemented-format migration;001 retains its original enum. Shared reason definitions in EXTRACTION002/CALCULATION_INPUTS002 are updated consistently. No nonunique-weight reason is attached to the valid combined estimate or its variance.

Two interpretation values are added for difference_variance and difference_standard_uncertainty: protocol_difference_uncertainty_known_covariance and protocol_difference_uncertainty_estimated_covariance. This makes their scope independent of common_mean while preserving the variance status. Their model_keys must omit the common-unbiased-quantity model; they retain fixed endpoint-conversion and covariance dependencies. combined_estimate/variance retain known_covariance_common_estimate or estimated_covariance_plugin_common_estimate, including the singular-equal branch. No category-to-number mapping or new score is introduced.

## Exact mathematical illustrations

SINGULAR_AND_PROTOCOL_PARTIAL_EXAMPLES_002.json contains labelled synthetic mathematical input summaries and cell-schema-valid expected rows. These are not authenticated source fixtures, full extraction samples, or execution of the proposed reader/calculator.

| Case | D | V_D; u_D | z; z² | w_L; w_R | combined value; variance; u |
|---|---:|---:|---|---|---|
| L=R=20, C=[[4,4],[4,4]], supported common model | 0 | 0; 0 | unavailable | unavailable, nonunique_gls_weights | 20; 4; 2 |
| L=R=20, C=[[0,0],[0,0]], supported known common model | 0 | 0; 0 | unavailable | unavailable, nonunique_gls_weights | 20; 0; 0 |
| L=20,R=22, C=[[4,4],[4,4]], known supported common model | -2 | 0; 0 | unavailable, inconsistent_deterministic_constraint | unavailable, model inconsistent | unavailable, model inconsistent |
| L=20,R=22, C=[[4,1],[1,9]], different source protocols, common_model absent | -2 | 11; sqrt(11)≈3.3166247903554 | common-model cells unavailable | unavailable | common-model cells unavailable |

The final row illustrates the corrected partial result directly: a meaningful descriptive difference variance survives lack of common-condition equivalence. It does not demonstrate new primary-source coverage. Ratio, difference, covariance-derived uncertainty and combined representations still reuse one contribution; singular recovery does not manufacture independent evidence.

ADDITIVE_CORRECTION_CHECKS_002.json records standalone metaschema checks and validation of these hand-constructed expected cells, plus unchanged hashes for all previously existing001 files. No production/test file was created or edited, and no production component was executed.
