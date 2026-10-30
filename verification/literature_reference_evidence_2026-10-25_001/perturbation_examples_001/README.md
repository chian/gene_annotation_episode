# Controlled source-perturbation examples

Both examples ran the ordinary Workflow and LiteratureEpisodes. Decisions and
controllers were scripted fixtures; there was no configured-model inference.
Each used an isolated six-base target fixture, one selected
`literature.perturbation.populate` action, one typed child return and a parent
bookkeeping action. Each has exactly three completed runtime observations,
one population operation, one parent receipt and zero scientific credit from
source bookkeeping. Original target-case and live-run stores were not opened.

| Requested cell | Synthetic matched restoration | Retained primary Cas2 |
| --- | --- | --- |
| symmetric_effect | 0.6666666666666666 | unknown: ratio scale not validated |
| restoration_fraction_raw | 0.875 | unknown: ratio scale not validated |
| reference_restoration_index | 0.4725, proposed conditional source index | unknown: ratio scale not validated |
| reference_index_lower | unknown: joint uncertainty unreported | unknown: joint uncertainty unreported |

Synthetic operands W=100,K=20,R=90,A_reference=100,A_restored=90,B_pert=8,
B_rest=7 are fixture data. Their source-only arithmetic is not a Cas2 result,
annotation probability, target transfer or complete A106 score. Its data origin
remains synthetic even where the numerical transformation's origin is derived
or proposed. Joint uncertainty, necessity counterevidence, broader comparability
and cross-experiment aggregation remain unfinished.

The primary example uses unchanged retained Cas2 XML and the exact original-byte
selectors already established in the parent review. Its selected interpretation
is cas-free reconstitution with qualitative-only measurements. It retains the
recipient/partner and endpoint/normalization witnesses, with no numerical data
source and no invented endpoint or exposure unit. This harness reuses that prior
source interpretation; it does not independently review the paper or perform
model-backed scientific interpretation.

Each case's RECEIPT.json contains the full saved extraction and numerical sheet,
the actual admitted four-cell parent subset, direct-source byte hashes and
observed counts. EXAMPLES_RECEIPT.json records the original invocation.

A separate process ran the runner with `--reopen`. It disabled the input reader,
calculator and physical-measurement identity generator. Only the saved sheet and
request artifacts could be read; original XML and retained measurement bytes
were forbidden. With SQL query-only enabled, it replayed the selected operation,
checked the original frozen child form against the selected saved cells and
the parent's admitted subset, and verified that three observations remained
three. REOPEN_RECEIPT.json records both results. This proves closed controlled
reconstruction, not live host-restart recovery or actual-model execution.

Commands, from the repository root:

```
.venv/bin/python verification/literature_reference_evidence_2026-10-25_001/run_perturbation_examples.py --directory verification/literature_reference_evidence_2026-10-25_001/perturbation_examples_001
.venv/bin/python verification/literature_reference_evidence_2026-10-25_001/run_perturbation_examples.py --directory verification/literature_reference_evidence_2026-10-25_001/perturbation_examples_001 --reopen
```

The original command creates a new directory and refuses to overwrite an
existing example. The second command reuses these closed records.
