# A101 native-score contract 010

Goal: provide a concrete numerical input and combination contract for BLAST protein local-alignment scores and HMMER/Pfam protein/profile scores, as one bounded contribution toward the A101 sheet. Completion of this research task requires the operands, scopes, equations, missing-value behavior, overlap/dependence rules, source trace, and checked synthetic examples to be reviewable. It does not complete the A101 sheet or any of the ten axes.

The complete deliverable consists of:

1. [NATIVE_SCORE_CONTRACT.md](NATIVE_SCORE_CONTRACT.md): source-traced fields, exact native meanings/calculations, coverage and site denominators, uncertainty/missing behavior, and valid versus unsupported arithmetic.
2. [COMPILATION_PROPOSAL.md](COMPILATION_PROPOSAL.md): the additive expanded combination route, every synthetic coefficient and operand, explicit alternative-function contrasts, a complete bounded contribution, missing-input bounds, and the remaining policy/calibration boundary. This is the proposed worked compilation to review; it extends the earlier contract's Section 7 without altering it.
3. [SYNTHETIC_EXAMPLES.md](SYNTHETIC_EXAMPLES.md): filled program-family rows and worked calculations. All numbers are explicitly synthetic.
4. [SOURCE_AND_AUTHORITY_AUDIT.md](SOURCE_AND_AUTHORITY_AUDIT.md): full authority-read record, exact inspected source sections, source reconciliation, check scope and limits.
5. [synthetic_arithmetic_results.json](synthetic_arithmetic_results.json) and [synthetic_joint_alternative_results.json](synthetic_joint_alternative_results.json): checked outputs from the two standard-library arithmetic scripts.
6. `source_documents/`, `source_manifest.json` and `authority_read_manifest.json`: retained official-source bytes and custody/read metadata.

| Bounded completion criterion | Status |
| --- | --- |
| Native raw, bit, E, identity and coverage meanings with actual operands | Delivered |
| HSP, domain and full-sequence scopes and search-space dependence | Delivered |
| Raw/bit/E relationships limited to their actual defined regimes | Delivered |
| Different coverage denominators and grounded site correspondence | Delivered |
| Duplicate, overlapping, repeated-domain and shared-family handling | Delivered |
| Valid sums/differences/products and raw pair/self substitution boundary | Delivered |
| Finite, explicitly unadopted bounded combination route | Delivered, as a group contribution and synthetic convention; real policy/calibration absent |
| Complete synthetic calculation including function alternatives | Delivered; arithmetic checks passed |
| Official source trace and complete initial authority review | Delivered; no paper-specific read or post-paper reset claimed |
| New files confined to owned research directory | Verified from performed write paths; production changes not made by this task |

Unfinished beyond this bounded research deliverable: accepted component/combination policy, actual function-grounded published cases, suitable fitted calibration if a probability interpretation is wanted, meaningful real-input readers, multi-group aggregation, user feedback, and full A101/W04/W05 verification. Current whole-goal accounting remains 0/10. No runtime gate, required tool sequence, universal evidence threshold, production code change, or scientific execution was introduced.

Reproduction is pure arithmetic:

```text
python3 research/experimental_scoring_review_2026-10-23/a101_native_score_contract_010/synthetic_arithmetic_check.py
python3 research/experimental_scoring_review_2026-10-23/a101_native_score_contract_010/synthetic_joint_alternative_check.py
```

The second script reads the retained first result file. It does not rerun or import any scientific tool. The additive source/authority audit documents the initial invocation failure caused by the absent `python` command implicitly through the actual successful `python3` commands; no successful check is attributed to that failed invocation.
