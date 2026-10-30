# Reaction and chemical evidence access

This stage adds ordinary source acquisitions for reasoning about chemistry.
It does not assign a reaction, cofactor, substrate, pathway or physiological role
to an input sequence. It makes no thermodynamic calculation or organism-capability
claim and changes no credit dimension, weight, denominator or continuation rule.

The biological motivation is in
[FUNCTION_AND_COMPARISON.md](research/FUNCTION_AND_COMPARISON.md) and
[ORGANISM_AND_ENVIRONMENT.md](research/ORGANISM_AND_ENVIRONMENT.md): family
similarity, plausible reaction chemistry and actual physiological role are distinct.
The owning Episode selects relevant comparisons and interpretations.

## Ordinary tools

| Tool | Caller-selected input | Source scope |
|---|---|---|
| `public.rhea.search` | `query`, optional positive `limit` (default 10) | One limited native JSON search response; no total/exhaustion or biological absence inferred. |
| `public.rhea.reaction` | Rhea `accession` | Selected-ID JSON search, limited to one returned entry. Requested and returned identities remain separate. |
| `public.chebi.search` | `term`, optional positive `size` (10) and `page` (1) | One native text search page with the provider's total/page count and next-query arguments. |
| `public.chebi.compound` | ChEBI `accession` | Actual compound detail. A secondary accession may resolve to a different primary accession; both are reported. |

The installed Rhea/ChEBI skill scripts perform their HTTP requests. Caller-owned
`PublicClients` timeout/skill-root configuration remains operational configuration;
actual script identity/digest, HTTP entity bytes, headers, selected parameters and
retrieval time are retained per operation. There is no entire-investigation
resource equality gate, automatic provider retry or endpoint/ID substitution.
Acquisition runs off the Store thread; scientific publication runs on its owning
thread. A repeated operation key replays the exact saved outcome without HTTP.

The official current ChEBI OpenAPI specifies **`term`**, not the skill example's
`query`. Actual calibration showed `query=caffeine` was ignored and returned the
whole database; `term=caffeine` returned 18 matching records. The implementation
uses the documented parameter. This is recorded interface evidence, not a
scientific relevance or quality threshold.

## Source facts and identities

Each imported entry has a reusable `reference` with actual accession, source and
`native_record_ref`. Labels use the accession; names and equations remain in their
source detail fields. This avoids truncating a long chemical name or treating a
reaction equation as a newly assigned enzyme product name.

`reaction_record` retains source equation, its displayed arrow/direction, source
status/balance/transport/comment, and ordered participant rows. Each participant
has source left/right side, source identifier/name/location, original coefficient
text, coefficient expression and a source-bound chemical identity reference.
Rhea's blank coefficient means one by its documented notation; symbolic values
such as `n+1` stay symbolic. A participant may be a Rhea-specific class or
macromolecule (`rhea-comp:...`), not a ChEBI small molecule. No ChEBI lookup occurs
silently while importing a reaction.

Rhea explicitly gives its left and right equation sides no substrate/product
meaning by themselves. Direction is what the selected source record states;
it is not a measured target-organism flux, equilibrium estimate or inference from
an enzyme name. A source field such as `status: approved` is preserved as source
data and is never a host acceptance rule.

`chemical_record` distinguishes `search_summary` from `compound_detail`. It retains
source name/definition, formula/charge, reported masses without inventing units,
SMILES/InChI/InChIKey/WURCS and structure identity/R-group flag where supplied,
secondary accessions and literal source ontology relations. Source roles or
origin statements are not experiments on the unknown target. Missing summary
ontology/structure data do not establish biological absence or identity equality.

Raw native responses retain fields beyond this first typed projection, including
synonym provenance, citations, origins and further classifications. They can be
read through the existing bounded `source.read` original representation. No new
freeform summarization call is introduced.

## Bounded communication and complete access

Acquisition outcomes preview at most six successfully projected entries. Each
preview names its actual reference/detail IDs. Complete typed details are read
using ordinary `state.query` with exact IDs, or the returned source-filtered
`details_query` and its next pages. Raw bodies are read through the returned
`complete_source_read_query`. New full detail kinds are deliberately absent from
automatic `reasoning_view` categories; small reference pointers remain visible.

The parent can request source-bound semantic references through its existing
closed form. New detail kinds are host-generated typed records; scientific
reasoning cannot author them. A reference/detail source, accession and type must
agree. Referenced details and participant identities survive ordinary export
closure. Acquiring these records alone creates no observation, annotation or
credit. Actual scientific application remains an explicit reasoning contribution
under the existing state and credit contracts.

One malformed row does not discard earlier or later independent valid rows.
The result retains the original source and reports typed row index/cause under
`projection_errors`; the operation is partial. If response bytes arrived before
a skill-client parse failure/timeout, diagnostics retain those bytes, status,
headers and actual request. A local failure without an HTTP response is not
fabricated as a provider response. Failed attempts are durable operational
outcomes and replay without a new request.

## Known limits and calibration

The Rhea JSON search interface exercised here returns undefined-direction master
records. Actual queries for directional `RHEA:47149` and the REST documentation's
`RHEA:10661` produced empty JSON results. The tool reports `no_search_match` with
that interface scope; it does not declare those identifiers invalid, substitute
another reaction or claim a chemical/biological absence. Directional quartet
resolution and RXN/RD/RDF entry ingestion are **not implemented** in this first
binding. The parser's other-direction tests are labelled synthetic notation
fixtures, not proof that this JSON interface exposes those entries.

This binding does not calculate mass/charge balance, pH/protonation transformations,
reaction equivalence, atom mapping, kinetic capacity, concentration dependence,
transport energetics, thermodynamic feasibility or physiological direction. It
performs no automatic ontology expansion, exhaustive pathway search, cofactor
classification or gap filling. It does not claim every chemical has a concrete
molecular structure. These remain scientific questions or later capabilities.

Official interfaces read and used:

- [Rhea REST API](https://www.rhea-db.org/help/rest-api): entry/search interface,
  table scope and directional-format limitation. JSON search was additionally
  confirmed through the installed skill's actual response.
- [Rhea reaction sides and directions](https://www.rhea-db.org/help/reaction-side-direction):
  equation-side semantics and separate directional identities.
- [ChEBI API documentation](https://www.ebi.ac.uk/chebi/backend/api/docs/) and
  [OpenAPI schema](https://www.ebi.ac.uk/chebi/backend/api/schema/): full compound
  lookup, required search term, page and size.
- Installed `life-science-research:rhea-skill` and
  `life-science-research:chebi-skill` instructions were read; no skill code was
  copied into the application.

Actual public calibration snapshots, requests and metadata are under
`validation/calibration/`. Tests use these saved responses or explicitly synthetic
transport/notation fixtures. They establish source, representation and execution
behavior, not intelligent annotation or a new biological finding.
