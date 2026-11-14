# BV-BRC Similar Genome Finder operations

Use the caller-configured BV-BRC Minhash API resource through launch/API execution.
`api.bvbrc.minhash.genome` accepts the assigned native genome ID;
`api.bvbrc.minhash.fasta` accepts the assigned Workspace FASTA file path. FASTA
mode does not upload a local file or accept inline sequence. The assignment
supplies mode, query, max_pvalue, max_distance, max_hits, include_reference,
include_representative, bacterial and viral. Preserve all supplied values;
there are no inserted search defaults. The selected operation's arguments are
empty because the original assignment already fixes the request.

Both operations make one direct RPC and retain its entire response. A valid
response supplies a completed-request handoff, not an AppService job. A missing
response leaves the issued call's outcome unknown. No automatic resubmission,
polling, different endpoint or resource substitution occurs. The caller supplies
the actual endpoint and any authorization configuration; an available operation
description does not establish authentication or deployment.

`api.bvbrc.minhash.result` is available to the results episode using that original
handoff and selector `{}`. It reuses the retained response, without repeating the
search. Each native row is `[genome_id, distance, pvalue, shared/union]`. Native
row order, duplicate genome rows, original strings/numbers and malformed fields
remain in the stored output. The tool sheet keeps parsed quantities beside those
native values. The deterministic calculator computes shared_hashes divided by
compared_union_hashes when the denominator is positive. That fraction describes
the sampled hash union, not bases or the fraction of genomes in a database.

Native distance and p-value are preserved. This production return path has no
actual k-mer length, sequence lengths or alphabet metadata, so recalculated
distance and p-value remain unavailable. An empty returned array does not prove
a complete negative search. Search population size, truncation and reference
release remain unknown when the native response does not report them. None of
these quantities is a calibrated probability of gene function.

Parents can request `bvbrc_minhash_matches` for native distances, p-values, hash
counts and shared fractions associated with original row indices and genome
identifiers, or `bvbrc_minhash_counts` for the actual number of returned rows.
Only requested typed fields are returned. The complete sheet and response stay
in retained artifacts. Partial rows preserve usable measurements with explicit
qualification; failed parsing does not convert missing values to zero.
