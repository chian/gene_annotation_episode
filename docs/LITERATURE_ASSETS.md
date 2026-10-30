# Selected literature assets and native document views

These ordinary tools let an Episode examine methods, conditions, controls,
tables and figures that may revise its interpretation. They do not choose an
article version, supplement, archive member, page or biological conclusion.
They are included with header, chemistry and image access in the canonical
package; exact promotion is recorded in BUILD_STATUS.md.
There is no mandatory reading pipeline, extra composer, scientific review gate
or change to credit/continuation. A useful interpretation still requires the
Episode's source-linked scientific reasoning; acquisition activity alone earns
no credit.

## Current public PMC catalogs

The installed `ncbi-pmc-skill` was read. It implements the legacy OA service,
which NCBI retired in August 2026; this adapter does not invoke that endpoint.
The implementation follows the current official public cloud documentation:

- `public.pmc.versions {pmcid}` reads one actual `ListObjectsV2` page of version
  prefixes. Optional continuation tokens retain provider pagination. No highest
  version, newest version, manuscript status or license is selected for you.
- `public.pmc.files {version_ref}` reads the selected version's actual object
  inventory. Its documented JSON metadata object is fetched only if that exact
  key is advertised in this returned inventory page. This is fixed catalog
  protocol, not guessed supplementary filenames or an adaptive investigation.
  It returns typed `pmc_object` and metadata-advertised `pmc_asset` identities.
- `public.pmc.asset {asset_ref}` accepts one of those actual registered
  identities. The Episode cannot substitute a URL, host path or version name.
  An advertised S3 URI is converted to the documented public HTTPS equivalent
  while preserving its original URI, key and checksum parameter.

Higher version numbers are not necessarily newer or preferred. Objects can be
updated without a new version prefix; captured metadata, retrieval time and
hashes identify the actual source used. Metadata status/license fields remain
source statements, not scientific acceptance decisions.

Optional metadata transport/JSON failure preserves the acquired inventory,
listed-object handles and original sources. A listed file can still be
explicitly acquired. ETags remain ETags; they are never assumed to be MD5.
When metadata explicitly advertises an MD5, both the advertised and actual
digests are recorded. A mismatch preserves the actual downloaded bytes and
returns qualified partial execution rather than pretending they match or
discarding the source.

The raw HTTP bodies, actual request/response metadata and effective URL are
retained. No new filename is inferred from a title, citation or media label.
No entire version tree is downloaded automatically.

## Archives

`source.archive.members {source_ref,offset?,limit?}` inventories one page of an
actual ZIP or TAR source. `archive_member` identities preserve ordinal,
filename, size, offset, type and native checksum fields. Duplicate filenames
remain distinct. The caller selects a returned member ID for
`source.archive.extract {member_ref}`.

Extraction reads that selected regular member's actual byte stream. It does not
write a source-supplied path, follow links or expand the entire archive. The
original archive, selection identity, Python/software version and output hash
remain attached. A link/directory does not supply regular file bytes; that
representation failure preserves the original source and returns specific
feedback. No biological absence or failure of a scientific hypothesis follows
from an archive error.

## PDF information, text and pages

`source.pdf.info {source_ref}` returns native `pdfinfo` output and its measured
physical page count. `source.pdf.text {source_ref,page,layout?}` extracts exactly
one chosen physical page with native `pdftotext`. Reading-order, layout and raw
content-stream modes remain explicit processing choices. The output is UTF-8
with Unix newlines and native page breaks. No OCR, table judgment, source
paraphrase or scientific interpretation is inserted.

The returned text source is a **derivative**. Its exact anchor offsets refer to
its own normalized UTF-8 bytes, not byte offsets in the original PDF or inferred
physical table cells. An unreadable font, absent text layer or incorrect page
request remains a limitation/error, not proof that the corresponding controls
or biological entities are absent.

`source.pdf.page {source_ref,page,dpi?}` renders that one physical PDF page with
native `pdftoppm` as a reusable PNG source. Default DPI=150 is the documented
native setting; the effective value and command are recorded. Native one-based
physical page numbers are distinct from printed page labels and zero-based
image pixels. Source images and transformations are retained, with no
measurement of bands, labels or plotted values implied by rendering.

The PNG is `source.artifact_ref`, with artifact media type `image/png`. The tool
returns its `image_source_ref` and typed derivation reference; it does not put
large base64 images in normal model JSON. The integrated ordinary `image.view`
action selects a registered source/frame and binds its verified PNG to native
`localImage` input in the next existing REASONING decision call. Rendering alone
does not interpret the pixels. A model visual observation retains its reasoning
origin, actual view/PNG/pixel-region provenance and separate source subjects;
it does not become a literal quotation or a performed target assay. See
[IMAGE_EVIDENCE.md](IMAGE_EVIDENCE.md).

## Configuration and execution ownership

Native resources are caller-owned, for example:

```toml
[local_tools]
pdfinfo_executable = "/caller/installation/bin/pdfinfo"
pdftotext_executable = "/caller/installation/bin/pdftotext"
pdftoppm_executable = "/caller/installation/bin/pdftoppm"
```

The same arguments are available on `ToolRegistry`. There is no model-selected
host path, environment executable override, work timeout or automatic scientific
retry. Actual invocation path, SHA256, version output, command, parameters,
stdout/stderr and transformed bytes are recorded. Callers can select other
resources for later measurements without invalidating committed earlier work.

Network/native/archive work happens off the event-loop thread and outside a
Store write transaction. Immutable resolved source operands cross that
boundary. Publication and operation journaling happen on the owner thread.
The existing operation key replays an already committed result exactly; it
does not download, extract, render or add another action observation. Failures
remain failures. A selected retry is a new ordinary action, with its own key and
actual outcome; there is no helper-owned investigation/retry loop.

## Provenance closure and immutable targets

New catalog, member and derivative records are host/native custody records,
excluded from model-authored reasoning writes. Existing closed parent report
forms remain unchanged. No acquired document or parsed member becomes another
annotation target, and no target denominator is expanded.

Catalog/version/file/member/derivation identities and the earlier material,
material-link, collection and parse-attempt identities describe file custody or
representation. They remain usable as provenance dependencies, query selections
and declared parent-report references. They cannot stand for a biological entity
inside an ATOM reference or relation value, just as a source, artifact or native
image view cannot stand for an enzyme substrate. Independent valid reasoning
rows survive a malformed value in another row; no scientific judgment or
continuation rule is added by that representation check.

Optional typed `source.parent_source_refs` provides forward source lineage:
PNG/text/information → PDF → original archive/acquired supplement → actual
metadata or file-advertisement source → file inventory → version inventory.
The PDF page, archive member and software settings also remain in typed
`source_derivative` records and exact request provenance.

The existing exporter follows these source parents and, for each selected
source, streams its exact source-bound native derivation/catalog/member records
through an indexed `source_ref` query. Those handles are labeled source-only
inventory. It does not reverse-follow every child of a PDF, parse arbitrary
request JSON as a semantic graph, scan unrelated archived investigations, or
change biological memberships/credit scope. Exported artifact bundles retain
the actual original/archive/PDF/image/text/catalog bytes needed to reconstruct
this lineage.

Native document sources also expose optional typed `stdout_ref` and `stderr_ref`
artifact fields. The captured stream bytes remain in the Store and in a portable
export, including successful warnings, empty streams and non-UTF8 bytes. Exact
request metadata retains the same stream identities. The exporter follows the
declared source fields through its existing reference closure; it does not parse
arbitrary request JSON as another semantic graph. These host fields cannot be
authored through a reasoning commit and create no observations or credit.
An Episode can select `source.read` with `representation="stdout"` or `"stderr"`
to read the actual stream through the existing bounded UTF-8 paging path. Missing
streams return explicit unavailable-representation feedback, without substituting
original content or text. Returned artifact offsets support the same exact-byte
source anchors. A binary stream retains the existing unreadable-text feedback;
its raw bytes remain available in the portable artifact bundle.

## Verification and limits

Saved-replay tests use the actual historical supplementary ZIP and metadata for
PMC12608037.1. Their synthetic object-inventory protocol fixture is explicitly
labeled; it is not described as a saved actual inventory response.

A separate small **actual current public catalog calibration** acquired the
version listing, selected object inventory and its listed JSON metadata through
the implemented client: one version, 13 actual objects and 12 advertisements.
The already acquired ZIP was reused with its original HTTP/hash provenance,
without another ZIP/PDF download. Native extraction matched the audited PDF
SHA256; `pdfinfo` returned 40 pages, and selected page 7 produced text containing
Figure S6 and a native PNG. Credit and annotation counts remained zero. This is
retrospective access/adapter calibration, not unknown-target success or a model
biological interpretation.

Tests also cover metadata failures retaining usable objects, qualified checksum
changes, opaque pagination/encoded keys, duplicate member names, TAR links,
incorrect native PDF input/page requests, replay, source-only target identity,
and export closure. A combined saved-source regression follows selected archive
member/PDF page through `image.view`, a scripted nondiscriminating interpretation,
current annotation and portable export. Its toy target is unrelated to the paper;
the zero-credit fixture is not a biological annotation result. One separate
actual model call recognized synthetic shapes through native image transport;
it did not interpret the paper's figure or run an annotation investigation.

The frozen combined 359-test baseline finished with 355 passes and four outdated
HTTP fixture failures; those four passed after fixture repair. Later custody and
native-stream corrections had 77 affected passes and one incorrect new test
expectation, followed by all three new tests passing after that assertion was
corrected. These counts overlap and do not establish a final full-suite result.
Exact manifests/reports and evidence limits are in
[BUILD_STATUS.md](../BUILD_STATUS.md). The test fixture helper finds the repository
audit directory by parent traversal; required files are `cloud-acquisition.json`,
`cloud-versions.xml`, `PMC12608037.1.metadata.json` and
`ijms-26-10351-s001.zip`. A separate PDF fixture is unnecessary.

Primary documentation read: [PMC cloud service](https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/),
[current dataset README](https://pmc-oa-opendata.s3.amazonaws.com/README.txt),
[retired OA service notice](https://pmc.ncbi.nlm.nih.gov/tools/oa-service/),
[AWS ListObjectsV2](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html),
and the installed complete `pdfinfo(1)`, `pdftotext(1)` and `pdftoppm(1)` manuals.
The local supplement-audit `REVIEW.md`, acquisition and extraction records were
read before implementation. That manual review is historical source examination,
not a verdict imposed on the Episode's investigation.
