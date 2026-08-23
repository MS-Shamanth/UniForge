# UniForge

**The product-content compiler that learns its own rule book from the catalogue.**

`LLM extracts. Rules decide. Evidence proves.`

Shamanth · Shreya BJ — UniHack 2026, AI-Powered Product Intelligence for Industrial Commerce

---

UniForge turns a 6-column industrial catalogue row into a verified 252-column
commerce-ready record, and cites the evidence behind every field.

```
49-94-0013   Milw 5"x.045"x7/8" Metal Cut Off Disc   -- Unbranded --   ...
```

becomes a record with a resolved manufacturer, a classpath, five description formats
written to their own character limits, eleven attributes, and a character-span citation on
every sourced value.

---

## Run it

```bash
pip install -r requirements.txt

python -m uniforge.cli compile        # compile, write every artefact, print the report
python -m uniforge.cli inspect 0      # everything known about one record, and why
python -m uniforge.cli serve          # the web app on http://127.0.0.1:8000
```

Frontend development, with hot reload and `/api` proxied to the Python server:

```bash
cd web
npm install
npm run dev                           # http://localhost:5173
```

`/` is the landing page. `/console` is the working prototype: it reads a live run, so
nothing it shows is typed in by hand.

Deployment, including the `Could not import module "app"` fix: **[DEPLOY.md](DEPLOY.md)**.

---

## The idea

The Solution Guide describes a 27,000-row approved manufacturer list, a 161,000-row List of
Values, ~500 approved UOM abbreviations and 200 labelled input-vs-output rows. What arrived
was 1,000 raw rows, 252 headers and 2 enriched examples.

> No dictionary was provided. So the catalogue became the dictionary.

Six rows differing in exactly one token are not six unrelated products:

```
3MABR-7100075678   3M 775L Stikit Film [P150] - Cubitron II 50 Disc/Box
3MABR-7100045865   3M 775L Stikit Film [P120] - Cubitron II 50 Disc/Box
3MABR-7100048736   3M 775L Stikit Film [P80 ] - Cubitron II 50 Disc/Box
```

- tokens that **vary** across siblings → variant axes → **these are the attributes**
- tokens that **hold constant** → invariant facts → safe to propagate to siblings
- and the guard: **a variant axis is never propagated**, so inference cannot amplify a guess

A second engine works on co-occurrence: values that never share a row are alternatives of
one attribute. That alone recovers AZEK's real structure — three collections across six
colours — from statistics, with nothing declaring either.

---

## Architecture

Nine stages. Four of them read across rows, which is why a per-row prompt cannot reproduce
this.

| # | Stage | Owner |
|---|---|---|
| 1 | Input analysis | deterministic code |
| 2 | Family & variant-axis discovery | **cross-row statistics** |
| 3 | Vocabulary induction | **cross-row statistics** |
| 4 | Manufacturer & brand resolution | entity resolution + rules |
| 5 | Classification & attribute extraction | deterministic code |
| 5b | Sibling propagation | **cross-row**, with the axis guard |
| 6 | Enrichment from manufacturer documents | documents, gated before any request |
| 7 | Cleansing & normalisation | deterministic code |
| 8 | Description building | deterministic code |
| 9 | Autonomous validation | deterministic code |

**The pipeline is complete with zero model calls.** When a model is enabled it is charged
per family, not per row — ~165 calls instead of 1,000.

### Who decides what

| Decision | Owner |
|---|---|
| Units, fractions, character limits, casing | deterministic code |
| Attribute discovery, vocabulary induction | cross-row statistics |
| Manufacturer/brand resolution, contradictions | entity resolution + rules |
| Naming an ambiguous attribute | model (optional) **or human** |
| Marketing prose | sourced, or left empty |

---

## The rules that make it defensible

**A fact with no locator cannot be published.** Enforced in `evidence.py`, not requested in
a prompt. Every value carries at least one `Evidence` record, and the kinds are ranked:

```
sourced  (4)  a manufacturer document says so, at these characters
supplier (3)  the supplied row says so, at these characters
vocab    (2)  an approved vocabulary says so
derived  (1)  a deterministic rule computed it from something already evidenced
inferred (0)  borrowed from a sibling; the weakest claim we will publish
```

That ranking is what lets a document overrule an inference with no special case. Cross-row
inference concluded `Package Quantity = 10`; Milwaukee's own page says `25`. The document
wins, and the disagreement is written into the trail rather than smoothed over.

**Where it refuses to look.** The brief excludes marketplaces and distributor sites, so
every candidate URL is classified *before* a request is made. Home Depot, Ace Hardware,
SupplyHouse and Ferguson are rejected without being contacted.

**A cached page must name the part number it is filed under**, or it is discarded — a
generic 200 response would otherwise attribute one product's specifications to another.

**No compliance claim against files we never had.** Every table reports its provenance:
`supplied` when the client's own XLSX is in `data/in/`, `seed` for a derived reference
table, `derived` for something induced at run time. The console shows this per vocabulary.

---

## Verification

`compile` asserts 15 things about itself and fails the command if any of them break:

```
character limits hold                      only approved units are written
round trip finds no hallucination          no claim published without a locator
delivery format is 252 columns             written file re-reads with 252 headers
every record has a status, a confidence score, a SKU and its part number
```

The round trip needs **no ground truth**: it re-parses UniForge's own output and demands a
locator for every number and value. That is why it works on the full catalogue and not only
on the rows where a labelled answer exists.

```bash
python tools/smoke_api.py     # 27 assertions against a running server
python tools/smoke_web.py     # the built page, plus the brief's content rules
python tools/diagnose.py all   # why any record is in review
```

---

## Layout

```
uniforge/            the compiler
  trade_tokens.py    tokenizer; every token keeps its character offsets
  evidence.py        the ledger, the kind ranking, the publishing rule
  families.py        skeleton clustering and variant-axis discovery
  induce.py          two induction engines, neither of which calls a model
  propagate.py       sibling propagation, and the axis guard
  entity.py          resolution, distributor unmasking, contradiction detection
  sourcing.py        the gate, the cache, document extraction
  normalize.py       units, fractions, casing, character limits
  compose.py         the five description formats
  verify.py          round trip, compliance, confidence, abstention
  review.py          the queue, sized in decisions rather than rows
  search_eval.py     BM25 over both catalogues, with the guards stated
  seed/              derived vocabularies (UOM, fractions, taxonomy, lexicon, 252 headers)

server/app.py        FastAPI over the compiler
web/                 React + Vite: landing page and live console
tools/               dataset and document builders, smoke tests, diagnostics
data/in/             input catalogue
data/docs/           cached manufacturer documents, committed so citations resolve
data/out/            generated: delivery file, metrics, evidence, review queue
```

---

## Data provenance — read this

The client's files are **not** in this repository. Two stand-ins are, and both are labelled
as such in code and in the UI:

- **`data/in/uniforge_reconstruction_1000.xlsx`** — generated by `tools/make_dataset.py`
  with the same pathologies the pack describes: 6 columns, ~86% placeholder brand cells,
  ~36-character descriptions, distributor names sitting where a manufacturer belongs, and
  one row pairing a manufacturer with a brand it does not own.

- **`data/docs/*.txt`** — reconstructed manufacturer-page fixtures from
  `tools/make_documents.py`. Every entry carries `"reconstructed": true` in `index.json`
  and the console labels it. Nothing in the extractor is tuned to their wording; it relies
  on structure real manufacturer pages share.

Drop the real files into `data/in/` under their original names and the loaders use them
instead, flipping each vocabulary's provenance to `supplied`. Every module already reads
through one vocabulary interface, so that is a data swap, not a rewrite.

Figures on the landing page come from the submission run and live in
`web/src/data/metrics.js` with their provenance documented. To show the numbers from a run
on your own machine:

```bash
python -m uniforge.cli compile
python tools/export_web_metrics.py      # writes web/src/data/live.js
# then set USE_LIVE_FIGURES = true in web/src/data/metrics.js
```

---

## What we would build next

1. Ingest the real LOV, UOM and 27k manufacturer list — a data swap through the existing
   vocabulary interface.
2. Manufacturer-domain retrieval under the sourcing hierarchy, to fill the withheld cells
   with cited values.
3. Learn from reviewer corrections so the derived vocabulary compounds.
4. Vision extraction from spec-sheet tables.
