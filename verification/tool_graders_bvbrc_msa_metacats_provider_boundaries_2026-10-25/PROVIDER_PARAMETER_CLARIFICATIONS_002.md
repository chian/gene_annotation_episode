# Additive commissioning clarification to the unaccepted provider parameter section

2026-10-25. The accepted math subset of CALCULATIONS_001.md is unchanged. This additive provider-only proposal replaces its final PValuePlan native-observation selection, so commissioning does not require unknown future artifact-derived observation IDs. Root's accepted math provenance, native count-v2 decision and MATH_CLARIFICATIONS_007 remain in force.

```text
PValuePlan =
 {kind:'statistical_results',statistics_request_ids:[id],field:'mathematical_p'} |
 {kind:'native_tables',table_ids:[id],eligibility_statistics_request_ids:[id]}
```

At commissioning each table_ids entry is a declared SlotRef; the pure provider receives resolved actual table IDs. Native table plans select only unadjusted p observations with validated native test associations. `eligibility_statistics_request_ids` names explicit complete native-reproduction statistics results proving the variable positive-df population when native pair rows do not report df. It can be empty when independent actual native/family evidence establishes eligibility. These results identify the tested population; they do not substitute recalculated p values for missing native p values. Filtered exports do not establish completeness. The selected FamilyPlan still determines all_eligible versus an explicit exact test subset.

The native p=1 produced by a pair underflow rule retains its source identity, never becoming a mathematical p value. A calculation-derived test ID and a native-observation-derived test ID remain distinct; actual category/position/group associations relate them without overwriting either identity. Cross-analysis selectors use exact table SlotRefs and explicit per-analysis eligibility request references as defined in BUNDLE_AND_RETURN_001.md.

The provider-request tagged unions after the frozen math sections were not part of root's accepted math workload. This proposal changes no existing pure signature or result, no previously saved record, and no arithmetic. The original pinned CALCULATIONS_001.md content is retained for its accepted hash; the clarified commissioning rule is recorded here additively.
