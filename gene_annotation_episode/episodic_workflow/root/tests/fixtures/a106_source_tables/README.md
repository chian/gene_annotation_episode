# A106 table-reader input

`gawand_2015_table2.xml` is the exact Table 2 fragment from Gawand et al.,
DOI `10.1039/c5ib00096c`, PMC archive version `PMC4789104.1`.
It is retained test input, not generated execution output.

- Original article SHA-256: `55eba68675b5b4c00acda30f1c1e6d34c282b3d850753d86b4d867b0e95e5ac9`.
- Fragment: original UTF-8 byte interval `[93145, 97186)`, 4,041 bytes.
- Fragment SHA-256: `45ad34acfdd72e84b9e6bd954120261fa6ae8053fd6949516783ec02b8708a72`.
- Publication: <https://pmc.ncbi.nlm.nih.gov/articles/PMC4789104/>.

The tests check reading and source association only. The grouped headings,
repeated model names, empty cells, superscripts and original values are intact.
They do not establish that a model is appropriate for an A106 claim or supply
an observed effect, effect variance, model calibration or a positive score.
This fixture is separate from anonymous-sequence evaluation inputs.
