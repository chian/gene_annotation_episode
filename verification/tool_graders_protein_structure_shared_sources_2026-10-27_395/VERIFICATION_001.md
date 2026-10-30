# Same original file in separate structure roles — verification 395

A comparison may select two different chains or models from one original file.
The original input paths may now coincide only when their entire FileIdentity
values agree. Input identifiers and staged paths remain distinct. Unequal
ancestor/descendant paths, contradictory identities and aliased staged paths
still reject. This implements contract addendum 009 without adding a host copy.

## Executed verification

- check001 preserved the expected failing regression: the previous validator
  rejected one source path used for two valid chain selections.
- check002 passed 57 tests in 80.64 seconds: all 52 native execution component
  tests and five shared-source tests.
- The actual native driver parsed the same eight-atom synthetic PDB twice with
  separate chain selections, retained separate staged inputs, and compared four
  matched residues. The fitted translation was approximately (-3, 0, 0) angstrom;
  RMSD was 1.2065475977771465e-16 angstrom, consistent with the expected zero.
- The exact native values, units, selections and original result identity are in
  FILLED_NATIVE_EXAMPLE_001.json. They are copied from retained output.
- Execution used local_jobs with 20 GiB RAM, 4 GiB scratch, zero swap and no wall
  budget. The executed snapshot remained unchanged.
- One live checkout file changed concurrently: protein_structure_result_worker.py
  from workload 393. These tests did not import that module. The execution
  contract and its actual dependencies remained at the tested versions.

This verifies native execution and the path constraint repair. It does not verify
production publication, parent receipt authorization, later sequence consumption,
or a complete episode path. The protein tool remains outside the completed tally.
