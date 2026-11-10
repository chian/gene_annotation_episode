The HMMER text and original detector projection are retained from the real
Aurora job 9052184, genomic07, run a107-0f01899bf25b4de082806fd367a880cf.
They use the existing anonymous-case-02 query, annotated reference CDS FASTA
and real NC_014034.1 GenBank window. The FASTA SHA is
9be28f4d52d264612f474e45286aa8cdadb3b6ef20274d90e7fa2fe2b787efde;
the GenBank SHA is
6bb4eed995036f3684bcd5475ce4293ca26375aedcc32b11353806044a56436e.

The expected JSON is the original saved detection projection before its A107
target/binding annotations. It preserves the original numerical and scope
semantics for comparison. Tests parse retained native text and source records;
they do not execute phmmer, launch a job, or establish an autonomous workflow.
The actual source/job custody is retained in the genomic07 run and common
validation directory. These required fixtures do not depend on that disposable
directory remaining present. Their expected answers are not episode inputs.
