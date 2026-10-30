# Additive preparation findings

This record adds to the earlier source study. It does not modify that study,
the immutable goal, fixed work rows, or deployment status. Exact producer
hashes and original retrieval receipts are in PRODUCER_SOURCE_REFERENCES.json.
No external requests or native jobs were performed by this workload.

## Duplicate declarations: concrete values, not blanket rejection

An initial implementation proposal would have rejected all three applications
with duplicate parameter declarations. The integration owner corrected this
before that proposal was coded: conflicting defaults do not invalidate a
supplied value, and a source defect must not become a universal runtime gate.
The actual implementation checks every declaration and preserves all of them.

* GenomeAssembly2 `max_bases`: both declarations are optional integers. The
  first has default 10000000000 and describes a downsampling trigger. The last
  omits the default and describes a limit. App-GenomeAssembly2.pl lines 212–214
  and 267–271 forward the same supplied value as `--max_bases`; the source can
  repeat that CLI option. p3x-assembly.py line 1091 declares an integer and
  describes downsampling, and line 1222 calls `constrain_total_bases` with it.
  Explicit integer 4000 passes both declarations. The preparer neither inserts
  10000000000 nor claims a native run was performed.
* ComprehensiveGenomeAnalysis `genome_size`: both declarations are optional
  integers. Defaults are JSON number 5000000 and JSON string "5000000"; both
  values and descriptions remain intact. Explicit integer 1000 passes both
  declarations. The module's `process_reads` constructs AssemblyParams and
  forwards its extracted parameters to GenomeAssembly2. The AssemblyParams
  implementation was not retained in this study, so its forwarding behavior
  is explicitly unverified. No claim is made that a real CGA run used 1000.
* Variation `reference_genome_id`: declarations are both strings but required
  is 1 versus 0. App-Variation.pl line 165 requires a nonempty reference.
  Supplied "123.4" passes both declarations; a missing reference fails. No
  unrelated valid work is blocked by the duplicated declaration.

## Duplicate JSON member in GenomeAnnotation

`parameters[3]` (`code`) has `type` twice: "enum" followed by "int", with
enumeration `[0, 1, 4, 11, 25]`. The source and derived files preserve both
members. The loader retains both values and paths before producing its usable
mapping. This is not silently repaired JSON.

App-GenomeAnnotation.pl lines 109–131 uses the supplied code as `genetic_code`.
It has a distinct native behavior when code is 0 or domain is "auto": taxonomic
metadata may replace the supplied code/domain. Preparation preserves 0 and
reports that native lookup selection; it does not fetch or invent taxonomy.
Integer 11 passes, while 2 violates the declared enumeration, "11" violates
integer typing, and booleans do not masquerade as numbers. The same module
explicitly rejects simultaneous nonempty `workflow` and `recipe` values.

## Shapes and source behaviors not established by type labels alone

* GeneTree `sequences` is an array of objects. The App's preflight and
  `retrieve_sequence_data` consume `type` and `filename`; `feature_ids` mode
  consumes `feature_ids` as a list. This differs from scalar
  `alignment_program` type choices. The producer does not reference
  `alignment_program`, and its bootstrap setter is commented out. Supplied
  controls are retained with `source_parameter_not_consumed` qualifications.
  Neither a chosen aligner nor bootstrap execution is falsely certified.
* TnSeq declares a repeated `group` without nested fields. App-TnSeq.pl lines
  81–103 actually iterates a mapping of named library objects containing
  `replicates` arrays. Each replicate has read/read1/read2 fields. The source
  overwrites read1 when both read and read1 are supplied; preparation diagnoses
  that concrete conflict and does not rename or drop either input. Other
  supplied replicate/library metadata remains explicitly unvalidated.
* FastqUtils declares `allow_multiple: false` on paired/single groups but its
  App and fastq_utils.py `setup` consume arrays. Their shape is checked without
  rewriting the request. The native steps recognized by `run_fq_util` are
  TRIM, PAIRED_FILTER, FASTQC, ALIGN, and SCRUB_HUMAN (case-insensitive in the
  producer). Original strings/order are retained. ALIGN needs the explicitly
  supplied reference genome; no reference is selected.
* MetagenomeBinning and MetagenomicReadMapping pass their read inputs into a
  ReadSet implementation absent from the retained sources. List-shaped read
  groups are accepted with a specific unvalidated-shape qualification, and
  their nested declared fields are checked. No actual input content, pairing,
  cardinality constraint, or Workspace object type is certified.
* MetagenomicReadMapping's producer accepts only CARD/VFDB for predefined
  lists even though its enum also lists feature_group/fasta_file. The latter
  are distinct gene_set_type modes and cannot stand in for a predefined name.
  Supplied FASTA alphabet is unverified; the annotation task does not become
  clinical resistance or virulence screening.
* CGA `run` calls `process_genbank` for the genbank branch, but that method is
  absent from the complete retained module, whose base is Class::Accessor.
  Preparation reports `source_mode_implementation_unverified` for this mode.
  No deployed mode behavior is inferred, and the required mode is retained.
* SubspeciesClassification's `fetch_or_write_input_fasta` implements only
  fasta_file/fasta_data. The declared id_list/genome_group modes are diagnosed
  as unsupported for this retained source. A different actual retained
  service definition is checked against its own declarations, with producer
  behavior explicitly unverified; old-source semantics are not imposed on it.

## Limits

This preparer checks supplied values and retained contracts. Workspace ACLs,
object content/types, database/reference availability/releases, complete native
scientific output, actual algorithm behavior, service deployment, and episode
communication require their separate acquisition, execution, and integration
work. A source catalogue or valid preparation is not evidence those checks ran.
