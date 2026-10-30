# Preserve declared native-report links on missing association support

Additive correction to proposal001 discovered during the final reread of
execution contracts008–011. Proposal001 remains immutable. This changes only
the proposed failure handling and its exact common-core consumer; it changes
no user goal, production code, historical observation, or settled contract.

Proposal001 section5 says an unavailable association clears a report's
component_request. That is withdrawn. The original declared comparison link
must remain inspectable in the saved sheet, as original control definitions
remain under011. A null comparison result must describe unavailable support,
not erase the selected relationship.

The corrected exact behavior is:

1. R preserves every ReportField.component_request in its resulting NativeReport,
   including when the declared association artifact is missing, mismatched, or
   uninterpretable. A caller that originally selected no link still has null.
   Invalid caller shapes remain contract errors. The numerical token must still
   come from the actual report bytes; association metadata never supplies it.
2. Each ReportInput already has exactly one association_file and a distinct
   source_key. R appends the existing core Issue with code
   `native_population_unknown`, stage `input`, that report source_key, and all
   other locators null when that association cannot support the declared links.
   B performs the same translation if the association capture fails after
   parsing; deduplicate the Issue. Preserve the exact missing/mismatched support
   file, role and reason in the existing Job, ReportBatch and Failure records.
   This source-scoped Issue affects only reports from that ReportInput; separate
   report inputs and independent event measurements remain usable.
3. S makes one additional narrow change to the existing
   `_Calculation.native_comparison` in fluorescence_event_calculations.py. For
   a linked report, an input `native_population_unknown` Issue with the matching
   report source_key prevents `native_minus_calculated`: value=null,
   state=unavailable, with the Issue and its sheet pointer as operands. Preserve
   the reported native_value when its bytes yielded a valid number, and preserve
   the referenced common calculated cell unchanged. This is the existing shared
   comparison calculator, not a worker/return postprocessor or another sheet.
4. The source-unit token and original known unit declarations remain recorded.
   No absent unit is invented. No field is changed to pretend a previously
   declared association was never requested. Saved recalculation retains the
   issue and never reacquires or silently rehabilitates the missing support.
5. Practical completion still distinguishes native producer delivery from a
   successful saved calculation as010 requires; unavailable comparison cells
   are not a scientific acceptance gate. Capture failure is an operational
   failure; extracted native values and independent scientific cells survive.

The function signatures and closed handoff shapes in INTERFACES_001.json do
not change. Its S calculator row's phrase “accepts derived event state” is not
an exhaustive implementation scope: include the dependency check above. P/R/A/B/C
ownership remains exactly as proposed. Add verification for missing versus
mismatched association bytes; unchanged declared component_request and native
value; unavailable delta with exact saved Issue; unaffected independent report;
saved-only recalculation; requested return equality; and old reportless sheet
replay. No tests or application imports were run for this correction.
