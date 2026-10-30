# Selected fluorescence preparation handoff

P589 implementation, 2026-10-28. The original user-entered goal is unchanged.
No GOAL.md was read or created. Both fixed fluorescence inventory rows and the
historical tool-grader instructions were read. This implements contract013 P,
proposal573 sections2–5/7 and corrections012/014–017; it does not claim either
operation's producer/episode integration is complete.

Implemented ports are validate_preparation_request, validate_resolved_preparation,
validate_prepared_event_data, validate_preparation_outcome,
assemble_prepared_parse, prepare_fcs_scaling, prepare_spill_compensation, and
read_fcs_spill_matrix. New numerical payload digests use the existing common
core canonical/digest. Assembly checks the independently retained numerical
canonical bytes plus LF, then adds actual Source and preparation identities.
The producer still authenticates actual recipe/support custody and topology.

Request validation uses016 per-kind DomainIdentity projections. Execution uses
an authenticated full parent parse. Every represented event is kept with its
primary original identity; output positions are contiguous and correspond to
the immediate parent. All raw input records remain unchanged. Untouched values
and their states are copied. Changed finite components become derived only in
the explicit prepared child domain. Unavailable/missing/invalid/singular values
are neither zero nor fallback raw values.

Actual FlowIO1.4.0 FlowData.as_array(preprocess=True) supplies metadata scaling.
Actual FlowUtils1.2.2 get_spill and compensate supply matrix parsing/solving.
No custom transform, inverse, pseudoinverse, clipping, gate inference, statistics,
resource substitution, installation or execution loop was added. Backend imports
are lazy. Numerical exception classes are retained under015 diagnostics.

The added strict decoder port reuses the existing FlowIO constructor, source
identity check, dataset traversal, bounds and datatype checks. A narrow TEXT
observer records ordered native tokens; the original FlowIO method supplies
actual decoder metadata. Duplicate relevant keys and altered value tokens are
rejected. The old encoded reader does not opt into that observer. A native
constructor error preserves already exposed selected matrix tokens.

Strict scaling rejects undocumented fallback metadata. Absent optional gain
and timestep remain undeclared. Time unit validation follows017: actual linear
Time plus applied timestep allows selected seconds or null; no timestep preserves
the old unit; nonlinear Time values remain possible with null unit. Scaling
preserves inherited compensation/transformation records, whereas new compensation
requires known uncompensated and untransformed input in the selected basis.
Successful scaling resolutions validate lexical/effective metadata relationships.

The sheet/calculator are unchanged: fluorescence_event_population_sheet_v1,
calculate_fluorescence_sheet, and project_fluorescence_result. Tests exercise
raw A>=105 selecting1 and compensated A>=105 selecting0 for measured rows
[110,60] and [20,100] with S=[[1,0.1],[0.2,1]], recovering approximately
[100,50] and [0,100]. Gain2 maps100 to50; Time timestep0.1 maps10 to1;
integer PnE=(2,1), PnR=100 maps50 to10. Saved-only calculation uses the same
retained sheet with native preparation imports disabled.

Source reads included the complete current FCS reader, event readers, all
relevant common contract/builder functions, actual retained FlowIO constructor,
metadata extraction, TEXT parser, as_array, writer and relevant tests; the complete
tagged FlowUtils compensation module was examined. The Time unit source is
[ISAC FCS3.1 normative reference, printed p27](https://flowcytometry.smhs.gwu.edu/sites/g/files/zaskib311/files/2021-11/Data%20File%20Standard%20for%20Flow%20Cytometry%281%29.pdf).
The existing R _context consumer was checked and its owner was notified of017's
prospective Time-unit exception; this lane did not edit that owner’s files.

Root reported check043 used actual installed FlowIO1.4.0, FlowUtils1.2.2 and
NumPy2.5.4:197 tests passed; no frozen P/R test failed. One root-owned authentic
FACS test failed because its staged dependency tree omitted pytz.exceptions.
That failure is preserved and is not this lane's native preparation evidence.
The current source includes subsequent exact metadata/token/type/unit/lineage
fixes and tests; those deltas need root's next bounded run. MANIFEST_001.json
records current hashes, selectors, support and dependency requirements. No host
application imports, tests, native computations or installations were performed.

Remaining verification is explicit: current-hash bounded tests, producer and
worker dependency custody, prepared batch admission, full requested episode
returns, and configured resource deployment are root-owned. Synthetic writer
fixtures establish native-format numerical behavior, not molecular observations.
No tool inventory completion status, historical receipt, scoring implementation,
message, prompt, runtime controller or lifecycle file was changed here.
