# Source corrections to the experimental scoring research

Keep the original lane reports as historical research records. The corrections
below supersede the specified interpretations and must be applied when deriving
the scoring sheet or worked examples.

## SC01 — YeaG recovery-growth variants versus long-term survival

Affected record: perturbation_and_attribution/case_reviews.jsonl, case_group
`yeag`, experiment packet `E2`. Its assay family is "survival rescue and
abundance-controlled variants" and its endpoint combines "CFU loss over
sustained starvation; wild-type and mutant complementation" with the Fig.3C
abundance measurements K116A64%, R232A48%, K426A100%, Y382Stop96%.

That packet combined distinct endpoints. Primary Fig.3 evaluates recovery-growth
complementation and the relevant variant abundances. The Fig.6B long-term
survival comparison specifically includes K426A and Y382Stop, not K116A.

Use these separate interpretations:

- **Recovery-growth phenotype:** the matched K116A/K426A failed-complementation
  comparison belongs to Fig.3. K116A is reported at64% WT abundance and K426A
  at100%. These can illustrate the differing abundance confound for this endpoint.
- **Prolonged-starvation survival:** Fig.6 supplies the CFU/time outcome and its
  actual listed complementation comparisons. Do not infer a K116A survival
  experiment from Fig.3 or borrow the recovery-growth mutant panel as if every
  variant had been tested in Fig.6.

Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC4664914/ — Fig.3 and Fig.6B,
corresponding Results and Methods. The numerical-rubric reviewer independently
checked this distinction against the retained primary text. Root checked that
the original E2 packet indeed mixed these fields.

The native percentages themselves are not changed. The corrected endpoint
boundary governs their use. No production annotation, scoring function or saved
run used this research proposal.
