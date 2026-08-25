# Solution brief

Paste target for the dashboard's **Solution Brief Overview** field. 2,041 characters,
inside the 2,056 limit.

---

UniForge turns a 6-column industrial catalogue row into a verified 252-column
commerce-ready record, and cites the evidence behind every field.

Enriching one SKU by hand takes an analyst 30-45 minutes. That labour is the problem.

UniForge attacks it in two layers. First it learns the rule book from the catalogue itself,
because the Solution Guide's 27,000-row manufacturer list, 161,000-row List of Values, UOM
standard and 200 labelled examples were not available to us - we had 1,000 raw rows and 2
enriched examples. Six 3M rows differing in exactly one token prove that abrasives have a
grit attribute. Values that never co-occur on a product are alternatives of one attribute,
which recovered AZEK's real collections and colour names from statistics alone. 165
families, 158 variant axes and 48 attributes induced, with zero model calls.

Second, it reads the manufacturer's own documents - the websites and technical documents
the challenge statement names. On the 39 products with a cached source, attributes rise
from 4.74 to 9.79 each and filled delivery cells from 26 to 57, with marketing copy and 374
feature bullets taken from the maker's own pages. Crucially it enforces the sourcing rule:
Home Depot, Ace, SupplyHouse and Ferguson were rejected before a request was ever made,
because marketplaces and distributor sites are excluded. Every sourced value cites a
character span in a document committed to the repository.

The layers check each other. Cross-row inference said Package Quantity = 10; Milwaukee's
page says 25. The document wins and the disagreement is logged. "DKO", which we had refused
to expand, is now evidenced from Milwaukee's own wording.

It abstains rather than guesses: cells stay empty for want of a source, 142 abbreviations
stay unexpanded, and a fact with no locator cannot be published. A round-trip check
re-parses our own output and traces every number to a source - 0 hallucinations across
1,000 records, needing no ground truth.

It audits its inputs too: 184 manufacturers unmasked from behind distributors, and in the
reference file row 1 pairs "Rheem Manufacturing" with brand "FRIGIDAIRE". Rheem makes water
heaters. UniForge flags it and asks a human.

Measured, not asserted: on buyer queries using trade vocabulary the supplier never wrote,
the raw catalogue returns the right product 0% of the time; after compiling, 33.5%. We also
report the one metric that went the wrong way. 1,000 rows compile in under a second.

---

## Submission checklist

| Field | Value |
|---|---|
| Prototype deck | PDF exported from the mandatory template, under 5 MB. Content: [`prototype-deck.md`](prototype-deck.md) |
| Solution brief | the text above |
| Live prototype link | the Render URL — see [`../DEPLOY.md`](../DEPLOY.md) |
| GitHub repository | https://github.com/MS-Shamanth/UniForge |

**Before submitting**

- [ ] Deck exported as PDF from `[EXT] UniHack-Protoype Template .pptx`, under 5 MB
- [ ] Live URL opens the landing page, and `/console` compiles
- [ ] `python tools/verify_all.py <live-url>` passes against the deployed service
- [ ] Repository is public
- [ ] Team set up under Team Management on the dashboard

**A note on the figures.** The numbers above and in the deck are from the submission run.
The pipeline recomputes all of them on every compile into `data/out/metrics.json`, and the
console shows the live values. Because this repository ships a reconstruction catalogue
rather than the client's own 1,000-row file, a local run will not reproduce them exactly —
see the data provenance section of the [README](../README.md). Drop the real files into
`data/in/` and the loaders use them instead.
