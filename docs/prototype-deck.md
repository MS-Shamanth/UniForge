# Prototype deck — slide by slide

Content for the mandatory template. Export as PDF, max 5 MB.

The deck is reviewed first and gates everything else, so it carries the whole argument on
its own: assume the reviewer never opens the repository. Every number here is in
`data/out/metrics.json`. Do not type a figure that is not.

---

## Slide 1 · Title

**UniForge**

**The product-content compiler that learns its own rule book from the catalogue.**

`LLM extracts. Rules decide. Evidence proves.`

Shamanth · Shreya BJ — UniHack 2026, AI-Powered Product Intelligence for Industrial Commerce

---

## Slide 2 · The problem, shown not described

Put the raw row and the compiled record side by side. No prose above them.

| Before — 6 columns, 3 are placeholders | After — 252-column record |
|---|---|
| `49-94-0013` | `MANUFACTURER_NAME` Milwaukee Tool |
| `Milw 5"x.045"x7/8" Metal Cut Off Disc` | `BRAND_NAME` Milwaukee® |
| `-- Unbranded --` | `CLASSPATH` Tools & Equipment>Power Tool Accessories>Cut-Off Wheels |
| `-- No Unilog Brand --` | `INVOICE_DESC` CUT-OFF DISC 5 IN .045 IN 7/8 IN 36/40 |
| `-- No DIB Brand --` | `SHORT_DESC` Milwaukee® 49-94-0013 Cut-Off Wheel, 5 in, .045 in, 7/8 in |
| `Milwaukee Accessory (4031)` | `ATTRIBUTES` Diameter 5 in · Thickness .045 in · Arbor Size 7/8 in · Qty 25 pc |

Footer: **86.5%** of brand cells in the supplied file are placeholders. Mean description
length: **38 characters**.

---

## Slide 3 · The constraint that became the idea

Two columns.

**What the Solution Guide describes**

- 27,000-row approved manufacturer & brand list
- 161,000-row List of Values
- ~500 approved UOM abbreviations
- Content guidelines with every formula and limit
- 200 labelled input-vs-output rows

**What we actually received**

- 1,000 raw rows
- 252 headers and **2** enriched examples

Then the turn, large and centred:

> **No dictionary was provided. So the catalogue became the dictionary.**

---

## Slide 4 · How it learns an attribute nobody defined

Show the six 3M rows with the varying token highlighted in one colour.

```
3MABR-7100075678   3M 775L Stikit Film [P150] - Cubitron II 50 Disc/Box
3MABR-7100045865   3M 775L Stikit Film [P120] - Cubitron II 50 Disc/Box
3MABR-7100048736   3M 775L Stikit Film [P80 ] - Cubitron II 50 Disc/Box
3MABR-7100075690   3M 775L Stikit Film [P180] - Cubitron II 50 Disc/Box
3MABR-7100075692   3M 775L Stikit Film [P220] - Cubitron II 50 Disc/Box
3MABR-7100145365   3M 775L Stikit Film [P320] - Cubitron II 50 Disc/Box
```

- tokens that **vary** → variant axes → **these are the attributes**
- tokens that **hold constant** → invariant facts → **safe to propagate to siblings**
- safety rule: **a variant axis is never propagated**, so inference cannot amplify a guess

**165 families · 158 axes discovered · 16 attribute labels induced · 0 model calls**

Second panel — the same idea on co-occurrence. Values that never share a row are
alternatives of one attribute, which recovered AZEK's real structure from statistics alone:

`Collection: Harvest · Landmark · Vintage`

`Colour: Brownstone · Coastline · Mahogany · Weathered Teak · Slate Gray · Castle Gate`

**48 categorical attributes induced. 46 need one human name each — not one per row.**

---

## Slide 5 · The enrichment — it reads the manufacturer's own documents

Open with the cost, because this is a margin problem for Unilog:

> Enriching one SKU by hand takes an analyst **30 to 45 minutes**. At 100,000 SKUs that is
> roughly **30 analysts for a year**.

Then one product, before and after:

| `49-94-0013` — `Milw 5"x.045"x7/8" Metal Cut Off Disc` | |
|---|---|
| From the supplier row alone | **5 attributes**, no marketing copy, no features, no source URL |
| After reading milwaukeetool.com | **11 attributes**, marketing copy, 10 feature bullets, source URL, 2 document references |
| Delivery cells filled | **26 → 57** |

Across all 39 sourced products: **4.74 → 9.79 attributes each (×2.06)**, 39 marketing
descriptions written, **374** feature bullets extracted, 78 document references mapped.

**Then the slide's real point — where it refuses to look.** The brief excludes marketplaces
and distributor sites, so every candidate URL is classified **before** a request is made:

| | |
|---|---|
| Candidates considered | 57 |
| Admitted (manufacturer-owned) | **39** |
| **Rejected, never even requested** | **4** — Home Depot, Ace Hardware, SupplyHouse, Ferguson |
| Blocked by the site itself | 2 — whirlpool.com HTTP 403, frigidaire.com timeout |

Two integrity rules worth one line each:

- a cached page must **name the part number** it is filed under, or it is discarded — a
  generic 200 page would attribute one product's specs to another
- every sourced value cites `doc:<id>#char[a:b]` and the documents are **in the repository**

Close on the moment that shows the architecture working:

> Cross-row inference said `Package Quantity = 10`. Milwaukee's own page says **25**.
> The document wins, and the disagreement is written into the trail. **20 of our own
> inferences were corrected this way.**
>
> And `DKO` — an abbreviation we had refused to guess — is now evidenced: Milwaukee writes
> *"5/8" DKO Arbor"*.

Footer, stated plainly: **coverage is 39 of 1,000 rows (3.9%)** from one manufacturer's
documents. The extraction is not product-specific; `--discover` builds candidate URLs from
a product's own dimensions, which is how 9 hand-listed URLs became 39 cached documents.

---

## Slide 6 · Architecture, and who is allowed to decide what

The four-layer diagram. Then the table that answers the judge's real question — **why isn't
this just a prompt?**

| | Owner |
|---|---|
| Units, fractions, character limits, casing | **deterministic code** |
| Attribute discovery, vocabulary induction | **cross-row statistics** |
| Manufacturer/brand resolution, contradictions | **entity resolution + rules** |
| Naming an ambiguous attribute | **model (optional) or human** |
| Marketing prose | **model (optional), else sourced or empty** |

Callout: **The pipeline is complete with zero model calls.** When a model is enabled it is
charged **per family, not per row** — ~165 calls instead of 1,000.

Callout: **Four of nine stages are cross-row.** That is why a per-row prompt cannot
reproduce this.

---

## Slide 7 · Proof, including the number that went the wrong way

**Compliance and integrity**

| | |
|---|---|
| Rows compiled | 1,000 in **0.66 s** |
| Character-limit compliance | **100.00%** (5,000 checks) |
| Approved-unit compliance | **100.00%** |
| Round-trip verification clean | **100.00%** — 0 hallucinations |
| Populated cells in → out | 3,405 → **22,460** (×6.6) |

**Search readiness — does the buyer find the part?**

| | Before | After |
|---|---|---|
| recall@10, vocabulary-gap queries | **0.0%** | **33.5%** |
| zero-result rate | 6.3% | **0.0%** |
| MRR@10, hand-written trade queries | 0.787 | **0.938** |
| exact-item recall@10 | 92.7% | **88.0%** ⟵ **worse** |

Put the last row in amber and say why: normalising a family makes its members more similar,
so category findability rises while exact-row ranking dips. **Showing the metric that did
not flatter us is the point.**

Small print: queries are built only from raw supplier text expanded through the seed
lexicon; no generated text is used to build any query; part numbers are stripped because
they are unique keys that inflate any baseline.

---

## Slide 8 · The slide that wins the room

Title: **We ran our contradiction check on the reference file we were given.**

Reproduce it verbatim:

```
MANUFACTURER_NAME = Rheem Manufacturing
BRAND_NAME        = FRIGIDAIRE®
MOBILE_DESC       = "Rheem Manufacturing FRIGIDAIRE, Dishwasher, ..."
```

Then UniForge's output:

> FRIGIDAIRE® is a brand of Electrolux Home Products, Inc., but the record names Rheem
> Manufacturing as the manufacturer. Rheem makes water heaters, boilers and HVAC equipment.
> Electrolux makes major kitchen and laundry appliances. **These cannot both be correct.**
>
> Confidence **34%** → **human review required.** UniForge does not overwrite a sourced
> value.

Three supporting bullets:

- The error has already propagated into `MOBILE_DESC`.
- The same code path found **3** contradictions in the 1,000 supplier rows — precision, not
  volume.
- `Part_Manuf` names whoever invoiced the goods: **184 manufacturers unmasked** from behind
  distributors and buying co-ops (Jam Industrial Supply → 3M; Appliance Dealers Cooperative
  → Electrolux).

Closing line: *the Solution Guide says spotting this is a strength. So we built the thing
that spots it.*

---

## Slide 9 · Refusing to guess is a feature

| Abstention | Count | Why |
|---|---|---|
| Delivery cells left empty | **16,000** | assets, UPC/GTIN, UNSPSC, price need manufacturer sources we did not retrieve |
| Mobile descriptions left short | **851** | the 60-char floor is unreachable honestly from a 38-char input |
| Abbreviations left unexpanded | **142** | e.g. `DKO` — no source confirms its meaning |
| Propagations blocked by the axis rule | **71** | the value varies between siblings, so it cannot be borrowed |

Plus the structural rule: **a fact with no locator cannot be published.** Enforced in code,
not requested in a prompt.

And: **we make no compliance claim against files we never had.** Everything is reported
against the **derived** vocabulary, with provenance shown per vocabulary in the UI.

Quote the guide: **"A fluent description made of invented values scores zero."**

---

## Slide 10 · Human-in-the-loop as leverage, not labour

44.9% auto-publish · 55.1% to review — then immediately reframe it:

> The review queue is **not** 551 rows of work. It is a short list of
> **one-decision-per-group** actions.

| Blocker | Records | The one action that clears it |
|---|---|---|
| Item type outside the derived taxonomy | 288 | map **245** item types to a classpath → unblocks **489** records |
| Attribute label awaiting a name | 161 | name **31** induced groups, once each |
| Attribute coverage below target | 86 | confirm induced attributes |
| Source contradiction | 3 | resolve with the manufacturer |

Screenshot the **name it** interaction: one click → **applied to 98 products**.

---

## Slide 11 · Impact and what we would build next

**Why a distributor cares**

- 6 columns → 252, with **×6.6** more populated cells and evidence on every field
- products become reachable by trade vocabulary that previously returned nothing
- a review queue sized in **decisions** rather than rows
- an audit trail per field, so content can be defended to a supplier or an auditor

**Next, in order**

1. Ingest the real LOV, UOM and 27k manufacturer list — every module already reads a
   vocabulary interface, so this is a data swap, not a rewrite
2. Manufacturer-domain retrieval under the sourcing hierarchy, to fill the 16,000 withheld
   cells with cited values
3. Learn from reviewer corrections so the derived vocabulary compounds
4. Vision extraction from spec-sheet tables

Close on the tagline: **`LLM extracts. Rules decide. Evidence proves.`**

---

## Speaker notes — the three questions judges ask

**"Isn't this just a prompt?"** Four of the nine stages read across rows. Nothing you can
say to a model about one row makes it notice that six 3M part numbers differ in exactly one
position. Slide 4 is the answer, and the zero model-call count is the proof.

**"How do I know it didn't make this up?"** Round-trip verification re-parses our own output
and demands a character-span locator for every number and value. It needs no ground truth,
so it runs on all 1,000 rows rather than only the 200 with a labelled answer. Zero
hallucinations. And any value in the console can be clicked through to the exact characters
that justify it.

**"What about the data you didn't have?"** Reported honestly, twice: the abstention slide
counts what we refused to publish, and every vocabulary shows whether it is `supplied`,
`seed` or `derived`. We make no compliance claim against a file we were never given.
