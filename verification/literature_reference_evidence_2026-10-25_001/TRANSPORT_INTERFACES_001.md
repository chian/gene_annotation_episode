# A105 transport — paired components and disjoint coding workloads

Current adopted GOAL_VERBATIM.txt and latest scope direction govern. Parent
independently reviewed BtsT original Results, Methods and Figures3–5 and reread
the complete required authority set, current696-line A105 sheet and applicable
native/rate/assay contracts. Current scope excludes target correspondence and
combined annotation credit. Source review/reset provenance is recorded separately.

## Numerical meaning, printed before coding

The BtsT whole-cell apparent Km is16.5±6.4uM. Its relative printed spread is
6.4/16.5=.3878787878787879; ± is unspecified, not borrowed caption SEM. On an
explicitly hypothetical SAME applicable Michaelis-Menten curve, substrate
test10uM/reference40uM gives saturations10/26.5 and40/56.5, hence response
h=.5330188679245283. This is a measured-response model correction, not a
reliability weight. It may divide an appropriate source effect and enter its
joint uncertainty once; no extra multiplier is applied afterward.

Actual paper whole-cell10uM and proteoliposome40uM have different systems and
cannot use this h. Their keys differ, so response cells are unavailable while
native numerical inputs survive. Accumulated label and initial rate remain
separate endpoints. A105 molecular activity and A106 deletion-background
complementation remain separate scientific uses; no matched WT arm is invented.

Investigation question: establish the actual molecule/construct, preparation,
compartment, analyte, endpoint and fitted curve; identify whether test/reference
substrates belong to that same curve. Find the point/spread and its actual
uncertainty meaning, calibration and shared measurements. Unknown relationships
remain unknown. Model interpretation selects meanings/operands; calculators
perform arithmetic. Complete sheets/formulas stay outside episode TASK.

## Fresh reader worker ownership

ONLY new gene_annotation_episode/literature_html_quantity_reader.py and
tests/test_literature_html_quantity_reader.py. No source papers/packets opened;
synthetic fixtures only. Root runs primary-source example.

Export read_html_quantity(source,*,section_id,paragraph_id,expected_subject,
quantity,analyte=None), source exact keys source_ref,artifact_ref,html,
representation(primary_html|synthetic_fixture). This finite original HTML
reader supports quantity=apparent_km only; other roles explicit unavailable.
Return the SAME exact numerical/extraction keys as read_jats_quantity with
version=a105_html_quantity_v1 and source representation/locators original.
No number is accepted as an argument. Require globally unique selected section
and paragraph IDs, actual containment in selected section, no nested section,
figure/table/caption/scripts/styles/hidden text, no caption-derived uncertainty.
Expected subject and analyte are literal token-presence checks, not molecular
attribution. Preserve inline sub/sup/text without concatenating adjacent numbers.
Finite native syntax includes `The Km of the transporter BtsT for pyruvate
measured in intact cells was 16.5 ± 6.4 μM.` plus a finite `Km = ... for analyte`
form if straightforward. Avoid scanning whole article for a convenient value.
Reject multiple expressions, wrong analyte/subject, limits/ranges, malformed
HTML/duplicate IDs, nonfinite/underflow, negative spread or nonpositive Km.
Preserve exact paragraph text/expression offsets, source IDs, canonical uM
conversion, origin, normalization none, unspecified/unreported uncertainty,
null count, unspecified sampling basis. No SD/SEM/n inferred from nearby text.
No JATS conversion, network, acquisition, state, prompt, repository or other edits.

## Fresh calculator worker ownership

ONLY new gene_annotation_episode/literature_transport_calculations.py and
tests/test_literature_transport_calculations.py. No source papers/packets opened;
synthetic fixtures only. Export populate_transport_response(inputs).

Exact inputs:
{values:{substrate_test,substrate_reference,km},
 curve_keys:{substrate_test,substrate_reference,km},
 measurement_keys:{substrate_test,substrate_reference,km},
 covariance,variance_status,observation_model,origin}

values finite number|null in uM; bool forbidden. curve_keys andmeasurement_keys
each nonempty string|null. All three same nonnull curve keys needed for h.
measurement keys retain physical ownership, and repeated same key requires
equal native values and identical covariance rows/columns; equal values alone
do not collapse. covariance full3x3|null in uM² ordered test,reference,km,
finite symmetric PSD (no jitter/default independence); variance_status
known|estimated|unknown. observation_model=michaelis_menten|unknown;
origin=reported|derived|graph_derived|synthetic.

Output version=a105_transport_response_v1, primitive_order, inputs, cells.
Cells: substrate_test,substrate_reference,apparent_km(uM),
test_saturation,reference_saturation,condition_response,
log_condition_response(dimensionless),
condition_response_variance(dimensionless_squared),
condition_response_standard_uncertainty(dimensionless).
Each exact value,unit,status,formula,origin,unavailable_reason,conditional_on.
Missing inputs preserve unaffected native cells. Positive concentrations/Km
needed by this first log-response route; invalid/nonpositive values yield
explicit unavailable calculation cells, not fabricated zero or pseudocount.
No curve/model claim, no inferred independence, no sampling error from ±.

h=St*(Km+Sr)/(Sr*(Km+St)). Use numerically stable arithmetic, not avoidable
intermediate overflow. logh derivatives in test,reference,Km order are
[Km/(St*(Km+St)), -Km/(Sr*(Km+Sr)),
 1/(Km+Sr)-1/(Km+St)]. Jh=h*Jlogh; Vh=Jh*C*JhT.
Use full covariance/shared Km once. Supplied known/estimated C can give a
first-order propagated variance, explicitly conditional; unknown status cannot
yield a sampling uncertainty. A computable h has conditional_on
[same_kinetic_curve,michaelis_menten_response]; uncertainty additionally
first_order_covariance_propagation. No statistical likelihood/index or final
credit is generated: this is a comparability operand for downstream effect
correction, not a source validity score. Handle numerical range explicitly.
Use ExperimentalContractError(code,field) for malformed inputs.

## Root ownership

Native quantity repository dispatch, original HTML custody, existing typed
returns/descriptor pins/prompt presentation, assembled verification and primary
example; all affected consumers read before edits. Later selected response
storage and typed transport return remain explicit unfinished integration until
actually implemented. No existing method_loop, credit, controller, tool-grader,
case Store, live pin, permanent research record or historical source edits.
