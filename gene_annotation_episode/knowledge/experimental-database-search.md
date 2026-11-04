# Experimental database search and reading

A105 investigates actual experiments and their relation to the supplied molecule.
Use database search to supplement publication discovery when the source covers
the question. Its records feed the same protocol-based readers, assay graders,
and reliability, validity, relevance and attribution sheets as literature.

- `public.sabiork.search` accepts native query syntax, including UniProtKB_AC,
  Organism and ECNumber. `public.sabiork.read` selects an entry ID. The current
  service is `/export-api/sabio/kinlaw-entry/json`; legacy REST paths have moved.
- `public.brenda.search` searches the public full-text interface. Select fields
  when useful. A category-summary page returns `search_result_queries`; follow
  a selected query with `result_field` to retrieve the category's actual hits.
  `enzyme_name` selects synonyms and `recommended_name` selects recommended
  names. `public.brenda.read` retrieves an enzyme page or one linked
  literature record. The HTML text projection preserves table boundaries;
  original HTML retains links and markup. This access route uses public pages.
- `public.brenda.graph_search` searches BRENDA's public prototype knowledge
  graph by accession, EC number, enzyme name, organism or publication title.
  Returned identifiers and publication links are discovery leads. Follow their
  enzyme-page reads and original publications for measurements. The graph is
  an additional access route when full-text search is unavailable; its coverage
  is not the complete database and it does not supply kinetic measurements.
- `public.bioassay.search` searches PubChem's pcassay index. Read an AID's
  description for target, protocol, result-column definitions and related
  controls, then its results or summary. Large result downloads have an explicit
  byte limit; a selected SID can restrict a result request.
- `public.chembl.search` discovers targets by exact accession or text, and
  assays by target ID or text. `public.chembl.read` retrieves targets, assays,
  documents and paged assay activities. Inspect species and assay descriptions
  even when the target mapping is present. Preserve standardized and native
  value relations and validity comments.
- `public.mavedb.search` discovers score sets by text. Read metadata for the
  experimental construct, measured phenotype and score definitions, then a
  selected page of processed scores. Native variant identifiers and the
  experimental reference sequence are part of the measurement's scope.

`source.experimental.records` inspects retained responses with stable row
indexes and literal filters. A `next_query` requests another provider page;
`next_records_query` reads another page already retained locally. A search page
is not an exhaustive statement about database coverage or experiment absence.
Use `contains_all` to combine literal organism, section or other record terms.
BRENDA records preserve native table headers, column positions, row identifiers
and links. Its `next_links_query` pages through whole-page links independently of
the filtered records. Large enzyme pages can require a larger `max_bytes`.
If an HTML page contains invalid UTF-8 bytes, its readable projection displays
those bytes as literal hex escapes and reports their original byte offsets.
The original response remains unchanged; an undecodable character is unresolved,
including when it occurs inside a unit or condition.

The `database_measurement` selector is an effect input to
`literature.assay_grading.populate`. It names an authenticated source, native
record index and field; the reader retrieves the numerical value itself.
PubChem results and MaveDB scores require a matching metadata_source_ref.
BRENDA's readable source spans use the ordinary literature readers. A source
number, its uncertainty and an experimental evidence score have different
meanings. Missing uncertainty, controls or independent predictions remain
specific unresolved requirements. A native MaveDB score preserves its reported
scale; interpret the actual assay before selecting a relative binding response.

For a reported kinetic parameter whose unit is in a shared table header,
`literature.kinetic.populate` accepts separate number and unit witnesses. A
single parameter uses the numerator with no denominator. Its saved
`literature_kinetic_cells` / `numerator_parameter` component can supply the
assay grader's effect. Select the complete unit token, retaining exponent
markup when needed. The grader's `source_number` shortcut requires an adjacent
printed unit; a rejected shortcut does not establish missing source data.

Retain the common experiment identity when a publication and a database record
represent the same experiment. Repeated representations, compound rows and
variant rows do not automatically establish independent experiments. Apply the
existing A105 aggregation only to the actual selected experiment assessments.

Provider documentation: https://sabiork.h-its.org/ui/export-api ;
https://www.brenda.dsmz.de/faq.php ;
https://sparql.dsmz.de/brenda ;
https://www.brenda-enzymes.org/news.php?news_id=2025-09-01-sparql ;
https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest ;
https://chembl.gitbook.io/chembl-interface-documentation/web-services/chembl-data-web-services ;
https://mavedb.org/docs/mavedb/programmatic-access/api-quickstart.html .
