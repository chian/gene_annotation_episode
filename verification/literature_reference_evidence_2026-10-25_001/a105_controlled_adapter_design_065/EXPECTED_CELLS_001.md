# Constructed expected controlled-response cells065

Actual frozen006 calculations; all inputs below are proposed parsed fixtures, not captured v2 source-reader outputs. No primary source or model execution.

|case|d1|d0|e|conditional e bounds|V|
|---|---:|---:|---:|---|---:|
|all_text_distinct|0.01|0.004|0.006|[None,None]|1.7e-06|
|mixed_graph_text|0.00995|0.004|0.00595|[0.00585,0.00605]|1.7e-06|
|shared_graph_control|0.01|0.00305|0.00695|[0.00685,0.00705]|1.36e-06|
|one_control_unavailable|None|0.004|None|[None,None]|None|
|reported_point_graph_alias_after_proposed_reconciliation|0.00995|0.003|0.00695|[0.00685,0.00705]|1.36e-06|
|full_source_covariance_invalid|0.00995|0.004|0.00595|[0.00585,0.00605]|None|
|unreconciled_mixed_alias_DIAGNOSTIC_ONLY|0.01|0.003|None|[None,None]|None|

Rates are umol/min/mg; V is (umol/min/mg)^2. Graph bounds are conditional digitization domains, not sampling CIs. S/B stay unavailable.

Full source N=6 projects actual indices [3,1,4,1]; one shared owner cancels. Expected graph-arm reported SD0.6 nmol/min/mg converts to0.0006 umol/min/mg, n3 technical measurements. This spread is not the joint source C.

The unreconciled mixed-alias row diagnoses frozen006 behavior; it is not the proposed final scientific result. The reconciled row shows an explicitly proposed canonical reported point after checking the graph domain. No new reader/reconciler or covariance parser was executed.
