# Selected-request fulfillment and pure fact validation

Root confirmed: Status.state describes fulfillment of the selected request;
native_state and output_complete separately retain actual native execution facts.
An original failed command can completely fulfill a selected request for retained
diagnostic/output artifacts. That does not label native execution successful or
claim scientific completion. Missing requested records/artifacts/saved data,
unavailable requested numerical inputs or unavailable requested native statistics
fields yield partial/failed/unavailable. Native failures and validation checks
remain returned facts and are not independent completion gates.

Known qualified nulls hard_mask_ambiguous and not_applicable can fulfill the
corresponding nullable quantity. A missing/broken mask denominator cannot. An
explicitly absent requested unit code is reported in missing_unit_codes; it is
an observed absence from the retained statistics, never a measured zero or
fabricated count. An empty input population cannot satisfy requested mask
quantities by silently returning an empty list.

Examples: failed command + requested retained stderr only can return
state=complete/native_state=failed/output_complete=false. The same attempt with
requested missing masked_positions returns partial or failed. DUST hard output
with pre-existing N returns the known null mask plus exact 64 symbol changes,
and can have state=complete without changing those numerical meanings.

Host completion validates the original selected request, exact typed return and
actual selected action through its existing practical endpoint. There is no mask
threshold, all-checks-pass gate or additional observation/zero turn.

Expose validate_masking_fact_values(source, values) -> independent validated
copy for root's communication boundary. It accepts only the exact seven sources,
their array schemas, core Count/Fraction/Occurrence/Check/Failure relationships,
statistics lexeme/association fields and saved-data identity/schema relationships.
It performs no Store IO, custody authentication, numerical calculation or arbitrary
selection. Those remain publication/host responsibilities. Fact descriptors use
the existing {type,meaning,report_schema} shape.
