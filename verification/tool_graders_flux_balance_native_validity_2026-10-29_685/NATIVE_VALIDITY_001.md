# Pinned GLPK option ranges and original-point validity, 685/001

This is source evidence for the two G6 questions in681. It changes no production
code, analytical schema, scientific calculation, selected execution, or goal.
The authoritative user attachment remains unchanged. Contracts679/001–007 and
the677 stack remain the implementation inputs. No optimization was run here.

## Source custody and verification limits

The selected stack is Cobra0.32.1, optlang1.9.1, swiglpk5.0.13, bundled GLPK5.0.
The Cobra/optlang sources and original native observation are reused from677.
The installed `swiglpk/glpk.i`, `swiglpk.py` and `__init__.py` are retained here
as source text copied from677's frozen `check134c_probe677/dependencies`.

The official [GNU GLPK5.0 source distribution](https://ftp.gnu.org/gnu/glpk/glpk-5.0.tar.gz)
was acquired once in bounded529/check148_validity685. Its exact size is
4,132,649 bytes and SHA256 is
`4a1013eebb50f728fc601bdd833b0b2870333c3b3e5a816eeba921d95bec6f15`.
`sources/ACQUISITION.json` retains the HTTPS response, archive pin and every
extracted source/document pin. `sources/glpk-5.0/src/glpk.h:33` declares5.0;
the full versioned manual sources are under `sources/glpk-5.0/doc/`.
The archive was not compiled and no native binary was replaced. This is a
versioned source trace, not a reproducible-build attestation for the wheel.

The source-acquisition test passed (1 test,2.53s). The enclosing runner audit
**failed with returncode4**, because DNS loaded the undeclared library
`/usr/lib/x86_64-linux-gnu/libnss_mdns4_minimal.so.2`. Preserve that failure;
do not call this a clean runner pass. `outside_modules=[]`, native and frozen
source/dependency/stdlib/binary pins were unchanged, and writer closure was
terminal/quiescent. The original receipt verifies20GiB RAM,4GiB monitored
scratch,zero swap,no wall cap; observed scratch was615,997,440 bytes.
The downloaded source and original failure receipts were preserved without
repeating the download or retroactively adding that library to its closure.

The acquisition test used only stdlib acquisition/archive operations. The reused
bounded runner also performed its existing baseline NumPy/Biopython import
probe, pytest import and library-resolution audit. No Cobra/optlang/swiglpk
import, solver call, installation, build or new native helper was executed by685.
The test file subsequently gained an explicit attempt/test-selection guard to
prevent implicit future downloads; that guard was not rerun and is not part of
the original frozen test receipt.

## 1. Exact public tolerance admission

All optional request fields use null to mean **not requested**. For a supplied
value, first apply the shared finite-JSON-number rule (excluding bool), convert
to the double value that will actually reach the native field, and require that
this converted value is finite and strictly between0 and1. Reject conversion
overflow, nonfinite values and values that become0 or1 after conversion. Do not
clamp, replace with a default, impose an additional preferred lower bound, or
translate one option into another. This is native input validity, not a
scientific acceptance criterion or diagnostic tolerance.

| Selected request field | Exact optlang path | Native range and meaning | Producer action |
|---|---|---|---|
| `feasibility_tolerance` | `model.solver.configuration.tolerances.feasibility` → `Configuration._set_feasibility` → `_smcp.tol_bnd` | `0 < double_value < 1`; primal basic-solution feasibility control | Validate before mutation/solve, set this property only, retain requested value and actual before/after value. |
| `integrality_tolerance` | `model.solver.configuration.tolerances.integrality` → `Configuration._set_integrality` → `_iocp.tol_int` | `0 < double_value < 1`; absolute integer-feasibility tolerance for MIP LP-relaxation values | Same validation/readback. It does not affect this continuous LP's `glp_simplex` computation; retain it as actual configuration, not continuous-FBA evidence. |
| `optimality_tolerance` | No public setter in this pinned GLPK interface | No accepted public value | Any non-null request is `solver_option_unsupported` before solve. Captured public value is missing/`unsupported_api`. Do not silently redirect it to `tol_dj`, `tol_obj`, `mip_gap`, or `model.tolerance`. |

The selected API exposes precisely `feasibility` and `integrality` through
`Configuration._tolerance_functions`. Both setters directly assign their
native fields; they do not check a range. `SolverTolerances.__setattr__` rejects
any unavailable public tolerance name with `AttributeError`. In contrast,
`Configuration.__init__(tolerances=...)` catches that error and ignores it, and
Cobra `Model.tolerance` catches unsupported optimality assignment, logs and
continues. Neither swallowing path is appropriate for an explicitly requested
unsupported option. Use the named direct properties after deterministic
validation. The closed selected-job option shape does not expose arbitrary
native control names or additional public properties.

Exact source locations in677:

* `sources/optlang/glpk_interface.py:371`–483: complete Configuration class;
  setters and supported-name map at440–455.
* `sources/optlang/util.py:307`–326: complete SolverTolerances implementation.
* `sources/optlang/interface.py:985`–1048: Configuration construction/clone and
  tolerance-dispatch hooks.
* `sources/cobra/core/model.py:177`–222: complete model-tolerance property/setter.

Native source locations in this packet:

* `src/draft/glpapi06.c:364`–480, complete `glp_simplex`: checks `tol_bnd`,
  `tol_dj`, and `tol_piv` using strict `(0,1)` predicates at401–409.
* `src/draft/glpapi09.c:443`–638, complete `glp_intopt`: checks `tol_int` and
  `tol_obj` using strict `(0,1)` predicates at476–481.
* `src/env/error.c:39`–65: invalid controls enter the native fatal-error path,
  whose ordinary implementation calls `abort`; they are not normal solver
  return codes. The retained swiglpk interface defines no alternative control
  validation or exception wrapper around these functions.

`0`, `-0.0`, `1`, negative numbers, values above1, NaN/±infinity and bool are
therefore invalid requested feasibility/integrality tolerances. Finite
binary64 values such as `1e-7`, `1e-9` and `0.25` satisfy the native parameter
range; range acceptance alone asserts no numerical quality. Even a positive
representable subnormal satisfies the native range check; there is no
source-supported arbitrary minimum such as `1e-12` to add here. Integer JSON
values0 and1 both fail; accepting JSON numbers does not make bool an integer.

### Separate native controls and their meanings

`tol_bnd` checks primal feasibility; `tol_dj` checks dual feasibility/reduced-cost
signs. `tol_dj` is an independent native control, not an exposed public
`optimality_tolerance` or a bound on objective error. `tol_piv` selects eligible
pivots. `tol_int` concerns integer feasibility; integer `tol_obj` concerns
relative objective comparison with the incumbent integer solution. None is
automatically the shared FBA calculator's explicit comparison tolerance.

The manual describes these at `doc/glpk02.tex:1802`–1823 and3070–3084.
For the exact numerical context, primal and dual simplex set secondary
tolerances to0.001 times `tol_bnd`/`tol_dj`
(`src/simplex/spxprim.c:1740`–1744; `spydual.c:1965`–1971).
`spxprim.c:284`–342 and `spydual.c:581`–625 use bound-dependent
`eps = tol + tol1 * abs(bound)` in the **working** LP.
`spxchuzc.c:53`–110 and `spydual.c:364`–425 use
`eps = tol + tol1 * abs(objective_coefficient)` for reduced-cost tests with
the corresponding active-bound/sign conditions. Initial phase selection and
other phases use additional specified factors, so neither scalar is a universal
unscaled absolute error guarantee. `glpios03.c:153`–225 contains the complete
integer-feasibility check: it skips continuous/nonbasic columns and uses
absolute comparisons to integral bounds/nearest integers for basic integer
columns, retaining the existing bound-roundoff handling.

GLPK's initialization sets `tol_bnd=tol_dj=1e-7`, `tol_piv=1e-9`
(`glpapi06.c:499`–530) and `tol_int=1e-5`, `tol_obj=1e-7`
(`glpapi09.c:640`–696). Cobra's model-tolerance setter can subsequently change
feasibility and integrality;677 observed both at1e-7. Native defaults and that
actual observation have different provenance. Capture actual controls instead
of assigning either set of values as new defaults.

## 2. Native evidence that establishes an original continuous point

The following is a source-derived predicate for this selected stack and
continuous LP route. It is not native execution testing of every branch.
It applies separately to each observed pass and, with the final-state conditions
below, to final `SolutionPayload.point_state`.

Inputs are:

* evidence that exactly the original public `model.optimize()` invocation was
  entered, with its actual call count and selected effective-problem identity;
* the actual same live original `glp_prob *P`, known to contain continuous
  variables only (no MIP solution substituted or integer relaxation);
* the observer's actual `glp_simplex(P, parameters)` return event, return code,
  parameter snapshot and post-return original-P primal status;
* independently recorded generic/dual status when available, raw native values
  addressed by original variable/row identity, and any capture exceptions;
* chronology proving which pass produced a value, and whether any later native
  invocation or problem/solution mutation could have changed that state.

The return/status portion of the predicate is exactly:

```text
established_return =
  (return_code == 0 and primal_status in {GLP_FEAS, GLP_INFEAS, GLP_NOFEAS})
  or
  (return_code in {GLP_EOBJLL, GLP_EOBJUL, GLP_EITLIM, GLP_ETMLIM}
   and primal_status in {GLP_FEAS, GLP_INFEAS})
```

Combined with the actual-return, original-P, continuous-model, identity and
chronology evidence above, this permits retaining an original basic point.
It does not require optimality, a feasible candidate, a positive value,
one or more iterations, a Cobra Solution object, or all values being finite.
An unknown return/status/custody relationship does not establish a point.
If other available native statuses contradict the source's relationships,
preserve the contradictory evidence and mark the admission unestablished;
do not choose a convenient field. Failure to capture a *dual* status does not
by itself negate independently established primal evidence.

The native codes are from `src/glpk.h:75`–80 and248–258:

| Native return | Value | Original-point consequence in this source |
|---|---:|---|
| Successful search | 0 | Original point is stored when primal status is FEAS2, INFEAS3 or NOFEAS4. This return alone does not assert optimality. |
| `GLP_EOBJLL`, `GLP_EOBJUL` | 6,7 | Direct dual-simplex exit stores a point with primal FEAS/INFEAS and dual FEAS. With nontrivial presolving, an unrecovered original remains UNDEF and fails admission. |
| `GLP_EITLIM`, `GLP_ETMLIM` | 8,9 | Direct simplex exit stores a point with primal FEAS/INFEAS. With nontrivial presolving, an unrecovered original remains UNDEF and fails admission. |
| `GLP_EBADB`, `GLP_ESING`, `GLP_ECOND` | 1,2,3 | Initial-basis failures; original primal is UNDEF. No new original point. |
| `GLP_EBOUND` | 4 | Invalid double bounds; original status was reset to UNDEF before returning. No new original point. |
| `GLP_EFAIL` | 5 | Failure branches leave primal UNDEF; do not trust residual getter values as a point. |
| `GLP_ENOPFS`, `GLP_ENODFS` | 10,11 | Presolver infeasibility or inability to recover a transformed nonoptimal solution; original point remains UNDEF. |
| Exception, no return, unknown code | unavailable/other | This evidence does not establish an original point. Earlier independently captured pass evidence remains separate. |

Generic statuses are not return codes: OPT5, UNBND6, NOFEAS4, etc. Never confuse
generic-status6 with return-code6. `glp_get_status` derives generic status from
primal/dual statuses: FEAS/FEAS → OPT; FEAS/NOFEAS → UNBND; FEAS with dual
UNDEF/INFEAS → FEAS; primal UNDEF/INFEAS/NOFEAS passes through unchanged.
This full function is `src/draft/glpapi06.c:551`–582. The complete raw-status
getters and scalar getters follow at601–800. The numeric getters do not
independently validate status or replace an unavailable point with null.

### Why NOFEAS must remain usable when a point was stored

1. `glp_simplex` validates controls, then resets original primal/dual status to
   UNDEF and objective to0 (`glpapi06.c:440`–443). It then dispatches to the
   empty-matrix path, direct solver, or presolver (`:470`–479).
2. `trivial_lp` (`:109`–219, complete function) writes all original row/column
   values and objective. An inconsistent zero row sets primal NOFEAS, yet the
   original basic vector was explicitly written and return code is0. Zeros
   here can therefore be legitimate observed values, including an all-zero
   infeasible point. This dispatch happens before checking the presolve flag.
3. The complete primal search (`src/simplex/spxprim.c:1124`–1600) sets primal
   NOFEAS and return0 when phase I establishes no primal feasible solution
   (`:1341`–1360). Its driver (`:1602`–1856) then writes the native statuses and
   calls `spx_store_sol`; only EFAIL skips storage (`:1764`–1801).
4. The complete dual search (`spydual.c:1217`–1830) likewise sets primal NOFEAS,
   dual FEAS and return0 for dual unboundedness (`:1627`–1643). Its driver
   (`:1832`–2097) stores the corresponding original point (`:2008`–2036).
5. `spx_store_sol` (`spxprob.c:568`–664, complete function) writes every original
   auxiliary/structural value, unscales/unshifts the working point, and writes
   the original objective. It does not require primal FEAS.

INFEAS means the stored candidate is infeasible under the native check; it does
not by itself prove the problem has no feasible point. NOFEAS additionally
retains GLPK's problem-level claim, while the stored candidate remains useful
for the common calculator's residuals. Candidate checks and native status remain
separate. UNBND with primal FEAS also permits a retained basic point even though
Cobra may raise rather than return its Solution.

### Why finite getter values and presolver claims are insufficient

`src/api/prob1.c:52`–115 initializes an empty problem with UNDEF statuses and
objective0. `glp_add_rows` (`:248`–327) and `glp_add_cols` (`:352`–414)
initialize primal/dual values to0. Thus finite zeros can predate all solving.
Later `glp_simplex` invocations reset statuses/objective but need not overwrite
every previous row/column primal before failing. A finite vector after UNDEF
can be default or stale data, not newly established point evidence.

The complete `preprocess_and_solve_lp` (`glpapi06.c:258`–362) uses a separate
transformed LP. It calls `npp_postprocess` and `npp_unload_sol` for the original
only after an optimal transformed solution or the equivalent empty transformed
problem. All nonoptimal/failure exits leave the original UNDEF. The manual
states this limitation at `doc/glpk02.tex:1707`–1711. The complete
`npp_unload_sol` (`src/npp/npp1.c:699`–904) confirms explicit original status,
value and objective writes. A presolver ENOPFS observation and a direct
simplex NOFEAS point are therefore different evidence.

The ordinary EFAIL branches set both statuses UNDEF and skip storing a basic
point. Dual simplex has a special internal `ret=-1` instability path that can
write working values before being returned publicly as EFAIL; it still sets
primal/dual UNDEF (`spydual.c:1343`–1350,2017–2036,2096). This is another reason
to require the status and code together rather than trusting getter values.

### Per-pass preservation and final output

The selected optlang code can call multiple native passes inside one public
invocation: full `glpk_interface.Model._optimize` at698–720 and full generic
`interface.Model.optimize` at1490–1512. Auto presolving can start a later pass
after a nonoptimal earlier pass. Every new `glp_simplex` entry can invalidate
the original final state as described above.

The passive observer must therefore capture each normally returned pass's
actual original-P raw getters immediately, before returning to optlang. Keep
the values, their qualification, native parameters/statuses/code, pass position
and original effective-problem identity together in native evidence. This is
read-only observation of work already selected; it introduces no solve,
retry, warm-up, basis repair, native helper, or producer feasibility calculation.

Final `SolutionPayload.point_state=basic_solution` requires admission of the
last actually returned original-P pass, no later entered/unreturned native pass,
and evidence that final extraction still refers to that same unchanged point
and numerical problem. Final native statuses belong to final state. An earlier
pass's qualified raw point must remain explicitly attached to that pass even
when final state is UNDEF. **Do not silently use an earlier pass as the final
point, overwrite final statuses, mix vectors/objectives across passes, or
reconstruct missing values.** The normalized679 NativePass contains no point
arrays; contract679/007 requires this per-pass raw getter evidence in the
solution's native capture carrier. A later typed earlier-point selection would need its own explicit
source association; it is not authorized or implemented by this source note.

For an admitted point, populate each actually captured finite native value with
the existing full-native token/hex/source encoding. A failed getter is missing
with a located failure; a nonfinite getter remains nonfinite with its token.
Do not erase the independently valid remainder merely because one value failed.
For an unestablished final point, keep raw getters only in diagnostics and emit
missing candidate primal/activity/flux Numbers with `primal_not_established`
(or `not_executed` when no original call occurred). Likewise do not promote a
reset/default objective to a usable native objective. Actual returned Cobra
fields, if any, remain separately retained raw evidence and are not proof of
point establishment. Native dual values retain their status qualifications and
must not imply valid sensitivity estimates for a nonoptimal point.

Cobra's complete `Model.optimize`/`slim_optimize` and `get_solution` paths were
read in677 sources. `get_solution` calls `check_solver_status`, whose
`has_primals` list includes nonoptimal strings without verifying GLPK's raw
status. It may also raise after native solving, notably for unbounded status.
Use the independent final capture; do not call `get_solution` again, fabricate
a Solution, or copy absent Cobra reaction flux/objective values from raw GLPK.
The shared calculator already owns forward-minus-reverse derived values.

## Handoff and remaining work

These sources resolve native ranges and the admission rule for the pinned
continuous GLPK route. They do not establish implemented production validation,
emitted point formats, actual nonoptimal native fixtures, requested child
returns, saved replay, or resource integration.677's single optimal observation
is reused and remains the only native FBA solve in these two packets.

Required producer consequences are: validate selected options before setters;
retain unsupported public optimality distinctly; use actual returned-pass
evidence for point admission; capture per-pass raw values before library retries;
keep final state separate; and preserve each value's finite/missing/nonfinite
qualification.679/680 still own shared records/parser/calculator semantics.
Contract679/007 freezes the additive evidence carrier; root owns later contract amendments. No tool
inventory completion count or broader goal-completion claim changes here.
