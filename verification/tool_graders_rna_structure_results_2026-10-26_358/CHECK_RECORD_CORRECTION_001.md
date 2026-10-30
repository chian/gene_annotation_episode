# Additive working-directory metadata correction

The retained command.json files through check_20261027T021819991815Z incorrectly
label the repository launcher directory as the test process cwd. The actual
run_local_job call in every retained run_checks.py source snapshot explicitly
uses cwd=RUN: the absolute directory containing that run's command.json,
stdout.txt, stderr.txt, source_snapshots and receipt.json. All test operands and
the Python executable are absolute. Each process receives the repository through
PYTHONPATH. This changes neither a command argument nor an execution result.

For the full passing run, the actual child working directory is:

    /home/chia/repos/gene_annotation_episode/verification/tool_graders_rna_structure_results_2026-10-26_358/check_20261027T021057670712Z

For the final focused passing run, it is:

    /home/chia/repos/gene_annotation_episode/verification/tool_graders_rna_structure_results_2026-10-26_358/check_20261027T021819991815Z

Original command files, receipts, snapshots and outputs are preserved. After
the final focused run, only the wrapper's metadata recording was corrected to
store launcher_cwd separately and cwd=RUN for any future invocation. The six
production modules, five tests and scientific fixtures are unchanged after that
run. Its source_unchanged=true records the actual comparison at job completion;
it is not a claim that this later metadata-only wrapper edit was already tested.
