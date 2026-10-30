# Actual one-gene homology probe

This was an empirical inspection of one tool job and its scientific usefulness.
It was not a model-driven episodic run or completion of the annotation goal.

## Measured execution

The only query was the 253-aa product of the fixed ybhP gene. Native phmmer 3.4
searched 575,748 reviewed reference proteins (209,017,843 residues). The query,
database and executable hashes, exact command, resource policy, native exit
metadata and output hashes are in jobs/homology_001/job.json.

| Phase | Protected-service wall time | What was observed |
| --- | ---: | --- |
| Reference acquisition | 580.92 s | Incoming I/O and changing process memory; no stdout payload during the 571 samples. The helper saved the completed FASTA at the end. |
| One-query homology search | 1.54 s | Two samples, both with zero stdout bytes. Complete matches, alignments and pipeline counters were available after return. Native phmmer separately reported 1.41 s internally. |

The outer probe recorded 581.03 s and 2.02 s, respectively. These include its
sampling/detection delay and are not substituted for native execution time.
Sampling is evidence of what this probe saw, not proof that every intermediate
change was captured. I/O counters do not establish percentage searched, nor does
CPU activity establish scientific progress. Both protected services verified
20 GiB memory, zero swap and no work timeout. Monitored scratch ended around
275 MiB. Sampled RSS is not an exact peak-memory measurement.

No resource failure occurred. All native matches and weak/noisy output remain
in the retained files; no extra match cutoff or scientific approval was applied.
The reusable reference database stays on disk. Reusing it removes the measured
download cost; another execution must not pretend that acquisition is still
required or repeat it merely to make monitoring take longer.

## What the results actually change

There are 17 reported reference records but only 11 distinct reference sequences.
Four records are exactly the query protein, including its own source entry;
all four have uncharacterized product labels. They do not supply four independent
functional discoveries or resolve the function by being excellent matches.

The best remaining sequence match is a bovine protein labeled RNA 2',3'-cyclic
phosphatase ANGEL2, with sequence E-value 0.16, followed by weak matches to other
unknown proteins and several named proteins. This supplies a possible lead to
investigate, not a defensible enzyme assignment to YbhP. Domain conditional
E-values must not be substituted for full-search independent E-values. An
unfavorable or ambiguous comparison is still a recorded result; it does not
reject the job or erase other work.

The immediate interpretation is that this search has not resolved a specific
molecular function. Further reasoning must decide what evidence could discriminate
the alternatives. The overlapping clsB neighborhood and source localization
study are possible context, with the limitations described in CASE.md. They do
not automatically convert this sequence comparison into a lipid-function claim.

## Consequences for the design discussion

* The search itself is a short ordinary job. Its measured behavior gives no
  reason to force extended monitoring or a fixed number of monitoring children.
* A monitor may learn execution facts without learning a gene function. Those
  are different contributions and need distinct local credit meanings.
* No intermediate hit-based scientific score can be claimed from this observed
  run. The native counters appeared at completion, and a larger hit count alone
  would not establish better annotation.
* Scientific improvement must record what the comparison changes about the
  evidence-supported interpretation, including specificity and limitations. It
  cannot be projected from elapsed time, bytes, native scores, copied labels or
  the number of returned references alone.
* One calibration supplies measured durations under one configuration. It does
  not establish a calibrated completion-time or future-information forecast.

No numerical credit formula, time exchange rate, continuation cost or new stopping
rule has been adopted. The generic weighted scores in the unfinished minimap2
example are not used here. A suitable longer job, if this investigation needs
one, must be chosen for its scientific purpose rather than to force an episode
demonstration. The required end-to-end episode and timer evidence is still missing.

The reproducible inspection script is inspect_probe.py. Its inspection.json keeps
all reported measurements and alignment coordinates, including the native program
flags as source information with no control effect. observations.jsonl is durable
raw timing history; the inspection streams it rather than retaining the archive
in active memory.

The two completed protected-service timings now populate the separately owned
shared run-statistics history. `run-expectations.json` records immutable snapshot
bindings. Acquisition and search remain distinct classes. No poll sample became
a completed-action observation, scientific credit or another timing trial.
See `../../docs/RUN_EXPECTATIONS.md` for the restricted interface and evidence
limits. Integration with actual child yield estimation remains unfinished.

## Configured-model sensitivity investigation, 2026-10-21 UTC

The later `runs/investigation_005` is an actual configured-model episode run,
distinct from the empirical probe above. The parent selected maximum sensitivity
for the same fixed gene and retained corpus. The native job is
`homology_job_e31b101ee959a2b555e58b7d`, in that run's `native-jobs` directory:

```text
phmmer --cpu 1 --max --tblout hits.tbl --domtblout domains.tbl query.faa references.faa
```

The installed primary manual defines `--max` as disabling acceleration filters
and running full Forward/Backward analysis on each reference. The actual output
comparison establishes what changed in this case:

| Observation | Default probe | Maximum-sensitivity job |
| --- | ---: | ---: |
| Query amino-acid length | 253 | 253 |
| Reference proteins | 575,748 | 575,748 |
| Reported hit-table rows | 17 | 37 |
| Service duration | 1.54 s, protected-service wall measure | 318.802496923 s, systemd-service wall measure |

The two duration measures have different provenance; the shared estimator does
not pool them or interpret these two observations as a calibrated speed ratio.
Both query sequences have SHA-256
`f0cdd3744b5bc986fd574175ecb7155c0ed57c7749098f20300735a3c849560a`.
Their FASTA byte hashes differ because the headers differ. The corpus bytes are
identical, SHA-256
`0e39da39014607bd1687caef1f495721bd4a405c4b83dceb134cd62f0c26332b`.
The unchanged executable hash is recorded in both native job metadata records.

Read each non-comment row of the two native `hits.tbl` files, index by column 1,
and compare columns 5–7 (full-sequence E-value, bit score, bias): all 17 old hits
remain with identical printed values. Twenty additional hits appear. The new
zebrafish ANGEL2 Q5RGT6 hit has full-sequence E-value 0.014 and bit score 20.2;
the other 19 additional hits have full-sequence E-values 2.3–9.6. Additional
reported hits do not by themselves establish better biological conclusions.

For Q5RGT6, `domains.tbl` distinguishes conditional domain E-value 1.9e-6 from
independent domain E-value 0.03 and full-sequence E-value 0.014. The printed
domain alignment spans query residues 30–178 and reference residues 233–386;
the parsed alignment records retain gaps and actual covered intervals. These
different values are not interchangeable evidence of function.

| Native artifact | SHA-256 |
| --- | --- |
| Default `hits.tbl` | `8e8623935fcddbde20e239e1e75a9c40ce4240db04fda0763cedbf0ab7426ef7` |
| Maximum-sensitivity `hits.tbl` | `0d22396658c740f2baea94d8fb902da4697851a67eae44dcfd4500df759bd958` |
| Maximum-sensitivity `domains.tbl` | `ac2d6550afa2390e1af54f77938a9b6f93bcc64d1a4cdefd1171c96dfd383d5d` |

The parent chose launch, monitor and results-acquisition children dynamically.
Their respective own-action counts were 46, 55 and 8 before numerical yielding;
these were not limits. Parent decisions 4, 6 and 7 each received one observation,
with scientific progress zero. The launch child returned a usable handoff while
the native job continued; the monitor observed completion before it yielded.
Thus this occurrence does not demonstrate a monitoring child closing during
ongoing execution. No timer was selected through parent action 18.

Selected monitoring gained one information unit for initial running-state
knowledge and one for completed-state/output/duration knowledge. Unchanged
samples gained zero. The single physical attempt supplied one global duration
statistic in its maximum-sensitivity class. The parent's original empty forecast
remains unchanged; its subsequent decision context received the new estimate.
Results acquisition retained all 85 native rows (37 references and 48 comparison
observations) and returned the parent's requested form. Acquisition credit 85
remained operational, separate from scientific investigation progress. All three
closed child archives and process-retirement receipts were independently checked.

Parent actions 12–16 then acquired UniProt Q5RGT6, read its source annotation and
committed a qualified transfer assessment. Its cited function annotation names
ECO:0000250 and human Q5VTE6 as the evidence source; it does not measure YbhP.
Assessment `assessment_5caafc056d08db6b6e90b5bf` is scope-limited and mixed,
retaining the partial native comparison as a condition. This earned one
provisional investigation unit without recording a confirmed YbhP function.
Scientific interpretation has begun; scientific completion, timed recommissioning
and ongoing-job monitoring closure remain unestablished at this inspection.

Parent action 101 subsequently committed an actual primary-paper qualification
after reading PMC9525292. Its extracted assay observations name DmANGEL and
MmANGEL2 as their subjects, retain positive cyclic-phosphate and negative
3′-phosphate results, and cite the exact source passage. Assessment
`assessment_c5394bd69401b56e5711feb7` links that source proposition to the YbhP
activity question as `different_source_subject`, `incomparable` and
`does_not_discriminate`. The partial zebrafish native alignment remains a
separate condition. The original source artifact hash and selected UTF-8 byte interval
were checked; neither the bacterial expression host nor the zebrafish match was
relabelled as an assayed YbhP protein.

This qualified finding raises the parent's provisional investigation progress
from 8 to 9. Action 102 incorporates it into annotation
`annotation_cc0d369f743b4eee8820c91c`, keeping that specific activity unresolved
and leaving progress at 9. Saved next-decision context 103 receives nine retained
findings and annotation-support score 0 separately. The exact finding is an
own-action receipt from index 101. This demonstrates useful investigation
progress without a stronger annotation-support claim; it is not a claim of
scientific completion or a newly demonstrated timing behavior.

This section is an audit of durable public actions, sources and native output.
It creates no episode findings, credit or controller observations and does not
change the live run's code, prompts or bindings.
