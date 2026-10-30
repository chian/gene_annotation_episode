# Candidate workflow005 review

The original candidate005 process (session53479, PID1061403) terminated with
exit1: five tests passed and one failed in946.80seconds. Retain its original
XML, log, source hashes and run `mauve-v4-tgiaqo3q` unchanged.

The numerical-return test compared an artifact's saved task association kind
to `manifest_member`. That string describes the selected request operand.
The actual output contract uses `task_result_manifest`, and the retained
artifact contains that value. This is a test expectation error, not evidence
of a production association failure. Correct only the isolated test.

Both source guards report300used paths, no changed sources and no missing
before hashes. Replay preserved26actions,27model calls,26observations,
226receipts and5report attempts, with zero new HTTP calls. Explicitly changing
the selected segments produced677/693coverage, preserving the original sheet.

The replay guard listed169blocked implementations/aliases. An earlier test
patch replaced native parser owners before the alias-discovery guard ran.
Confine these parser patches to the explicit recalculation context so replay
discovers the restored original functions and their aliases. Keep acquisition
barriers for both operations. This strengthens the test; it changes no
production behavior. Verify the complete candidate again after both test fixes.

Original production verification processes161/162 remain untouched. Candidate
source changes are still isolated; no production integration is claimed.
