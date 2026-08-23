"""Stage 6 - enrichment from manufacturer sources. Where the pipeline refuses to look.

The brief names websites, catalogues and technical documents as the sources, and excludes
marketplaces and distributor sites. So the classification happens BEFORE a request is
made, not as a filter on what came back:

    admitted   the domain is the resolved manufacturer's own property
    rejected   marketplace or distributor - never requested
    blocked    admitted, but the site itself refused to serve the page

Two integrity rules sit on top of the gate.

    A cached page must NAME the part number it is filed under, or it is discarded.
    Without that check a generic 200 page would quietly attribute one product's
    specifications to another.

    Every sourced value cites `doc:<id>#char[a:b]`, and the documents are committed to
    the repository, so any figure in the output can be read back to the characters that
    justify it.

WHEN THE LAYERS DISAGREE
    Cross-row inference concluded Package Quantity = 10. Milwaukee's own page says 25.
    The document outranks the inference in the evidence ledger, so the document wins
    without any special case, and the disagreement is recorded rather than smoothed
    over. The same mechanism is what finally evidences `DKO`, an abbreviation the
    pipeline had refused to expand: Milwaukee writes '5/8" DKO Arbor'.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from . import config as C
from . import normalize as N
from . import trade_tokens as TT
from .evidence import SOURCED, RecordEvidence
from .extract import Extraction, _add
from .ingest import Row
from .vocab import Vocabulary, norm_key

ADMITTED = "admitted"
REJECTED = "rejected"
BLOCKED = "blocked"


@dataclass
class Document:
    doc_id: str
    part_number: str
    text: str
    url: str
    domain: str
    brand: str
    reconstructed: bool = True

    def spec_block(self) -> dict[str, tuple[str, int, int]]:
        """'Label: Value' pairs with the character span of each value."""
        out: dict[str, tuple[str, int, int]] = {}
        in_specs = False
        for m in re.finditer(r"^(.*)$", self.text, re.MULTILINE):
            line = m.group(1)
            low = line.strip().lower()
            if low == "specifications":
                in_specs = True
                continue
            if low in ("documents", "features", "applications", "overview"):
                in_specs = False
                continue
            if not in_specs or ":" not in line:
                continue
            label, _sep, value = line.partition(":")
            label, value = label.strip(), value.strip()
            if not label or not value:
                continue
            v_start = m.start(1) + line.index(value, len(label))
            out[label] = (value, v_start, v_start + len(value))
        return out

    def features(self) -> list[tuple[str, int, int]]:
        out: list[tuple[str, int, int]] = []
        in_block = False
        for m in re.finditer(r"^(.*)$", self.text, re.MULTILINE):
            line = m.group(1)
            low = line.strip().lower()
            if low == "features":
                in_block = True
                continue
            if low in ("applications", "specifications", "documents", ""):
                if in_block and low:
                    in_block = False
                continue
            if in_block and line.lstrip().startswith("- "):
                val = line.lstrip()[2:].strip()
                s = m.start(1) + line.index(val)
                out.append((val, s, s + len(val)))
        return out

    def applications(self) -> list[tuple[str, int, int]]:
        out: list[tuple[str, int, int]] = []
        in_block = False
        for m in re.finditer(r"^(.*)$", self.text, re.MULTILINE):
            line = m.group(1)
            low = line.strip().lower()
            if low == "applications":
                in_block = True
                continue
            if low in ("features", "specifications", "documents"):
                in_block = False
                continue
            if in_block and line.lstrip().startswith("- "):
                val = line.lstrip()[2:].strip()
                s = m.start(1) + line.index(val)
                out.append((val, s, s + len(val)))
        return out

    def marketing(self) -> tuple[str, int, int] | None:
        m = re.search(r"^Overview\s*\n(?P<body>.+?)(?:\n\s*\n)", self.text,
                      re.MULTILINE | re.DOTALL)
        if not m:
            return None
        body = re.sub(r"\s+", " ", m.group("body")).strip()
        return body, m.start("body"), m.end("body")

    def documents(self) -> list[tuple[str, str, int, int]]:
        out: list[tuple[str, str, int, int]] = []
        in_block = False
        for m in re.finditer(r"^(.*)$", self.text, re.MULTILINE):
            line = m.group(1)
            low = line.strip().lower()
            if low == "documents":
                in_block = True
                continue
            if not in_block or ":" not in line:
                continue
            label, _sep, url = line.partition(":")
            url = url.strip()
            if not url.startswith("http"):
                continue
            s = m.start(1) + line.index(url)
            out.append((label.strip(), url, s, s + len(url)))
        return out

    def title(self) -> tuple[str, int, int] | None:
        lines = self.text.split("\n")
        if len(lines) < 2:
            return None
        title = lines[1].strip()
        if not title:
            return None
        s = self.text.index(title, len(lines[0]))
        return title, s, s + len(title)

    def names_part(self, part_number: str) -> bool:
        if not part_number:
            return False
        squash = re.sub(r"[^A-Za-z0-9]", "", part_number).lower()
        body = re.sub(r"[^A-Za-z0-9]", "", self.text).lower()
        return squash in body


@dataclass
class GateDecision:
    url: str
    domain: str
    verdict: str
    reason: str
    part_number: str = ""

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass
class SourcingModel:
    documents: dict[str, Document] = field(default_factory=dict)
    by_part: dict[str, str] = field(default_factory=dict)
    decisions: list[GateDecision] = field(default_factory=list)
    discarded_unnamed: list[dict] = field(default_factory=list)
    reconstructed: bool = True
    index_note: str = ""

    # counters filled during enrichment
    enriched_rows: int = 0
    attrs_before: int = 0
    attrs_after: int = 0
    marketing_written: int = 0
    features_extracted: int = 0
    document_references: int = 0
    inferences_corrected: int = 0
    abbreviations_evidenced: list[dict] = field(default_factory=list)
    delivery_cells_before: int = 0
    delivery_cells_after: int = 0
    per_row: dict[int, dict] = field(default_factory=dict)

    @property
    def admitted(self) -> int:
        return sum(1 for d in self.decisions if d.verdict == ADMITTED)

    @property
    def rejected(self) -> list[GateDecision]:
        return [d for d in self.decisions if d.verdict == REJECTED]

    @property
    def blocked(self) -> list[GateDecision]:
        return [d for d in self.decisions if d.verdict == BLOCKED]

    def to_dict(self) -> dict[str, Any]:
        b, a = self.attrs_before, self.attrs_after
        n = max(1, self.enriched_rows)
        return {
            "reconstructed": self.reconstructed,
            "note": self.index_note,
            "candidates_considered": len(self.decisions),
            "admitted": self.admitted,
            "rejected_before_request": [d.to_dict() for d in self.rejected],
            "rejected_count": len(self.rejected),
            "blocked_by_site": [d.to_dict() for d in self.blocked],
            "blocked_count": len(self.blocked),
            "discarded_because_page_did_not_name_the_part":
                len(self.discarded_unnamed),
            "documents_cached": len(self.documents),
            "rows_enriched": self.enriched_rows,
            "attributes_before": b,
            "attributes_after": a,
            "attributes_before_mean": round(b / n, 3),
            "attributes_after_mean": round(a / n, 3),
            "attribute_multiple": round(a / b, 3) if b else 0.0,
            "marketing_descriptions_written": self.marketing_written,
            "feature_bullets_extracted": self.features_extracted,
            "document_references_mapped": self.document_references,
            "inferences_corrected_by_a_document": self.inferences_corrected,
            "abbreviations_evidenced": self.abbreviations_evidenced,
            "delivery_cells_before": self.delivery_cells_before,
            "delivery_cells_after": self.delivery_cells_after,
        }


# ======================================================================================
# the gate
# ======================================================================================


def domain_of(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def classify_domain(url: str, manufacturer: str, vocab: Vocabulary) -> tuple[str, str]:
    """Runs before any request. Returns (verdict, reason)."""
    dom = domain_of(url)
    if not dom:
        return REJECTED, "unparseable URL"
    if dom in C.EXCLUDED_DOMAINS:
        kind = ("retail marketplace" if dom in {
            "amazon.com", "ebay.com", "walmart.com", "homedepot.com", "lowes.com",
            "acehardware.com", "truevalue.com", "menards.com"} else "distributor")
        return REJECTED, f"{kind} - excluded by the sourcing hierarchy"
    base = dom.rsplit(".", 1)[0].split(".")[-1]
    if any(k in base for k in C.EXCLUDED_DOMAIN_KEYWORDS):
        return REJECTED, ("domain name indicates a distributor or reseller - excluded "
                          "by the sourcing hierarchy")
    owned = vocab.manufacturer_domains.get(manufacturer, set())
    if dom in owned or any(dom.endswith("." + o) or o.endswith("." + dom)
                           for o in owned):
        return ADMITTED, "manufacturer-owned domain"
    # allow a manufacturer-looking domain that carries the brand token
    mk = norm_key(manufacturer).replace(" ", "")
    if mk and mk[:6] and mk[:6] in re.sub(r"[^a-z0-9]", "", dom):
        return ADMITTED, "domain carries the manufacturer name"
    return REJECTED, "not established as a manufacturer-owned source"


# ======================================================================================
# cache
# ======================================================================================


def load_cache(vocab: Vocabulary) -> SourcingModel:
    model = SourcingModel()
    index_path = C.DATA_DOCS / "index.json"
    if not index_path.exists():
        model.index_note = ("no document cache found; run "
                            "`python tools/make_documents.py` or "
                            "`uniforge source --fetch`")
        model.reconstructed = False
        return model

    index = json.loads(index_path.read_text(encoding="utf-8"))
    model.reconstructed = bool(index.get("reconstructed", False))
    model.index_note = index.get("note", "")

    for entry in index.get("rejected_before_request", []):
        model.decisions.append(GateDecision(
            url=entry.get("url", ""), domain=entry.get("domain", ""),
            verdict=REJECTED, reason=entry.get("reason", ""),
            part_number=entry.get("part_number", "")))
    for entry in index.get("blocked_by_site", []):
        model.decisions.append(GateDecision(
            url=entry.get("url", ""), domain=entry.get("domain", ""),
            verdict=BLOCKED, reason=entry.get("reason", ""),
            part_number=entry.get("part_number", "")))

    for entry in index.get("documents", []):
        path = C.DATA_DOCS / entry["file"]
        if not path.exists():
            continue
        doc = Document(
            doc_id=entry["doc_id"],
            part_number=entry.get("part_number", ""),
            text=path.read_text(encoding="utf-8"),
            url=entry.get("url", ""),
            domain=entry.get("domain", ""),
            brand=entry.get("brand", ""),
            reconstructed=bool(entry.get("reconstructed", True)),
        )
        # integrity rule: the page must name the part it is filed under
        if C.T.doc_must_name_part and not doc.names_part(doc.part_number):
            model.discarded_unnamed.append({
                "doc_id": doc.doc_id, "part_number": doc.part_number,
                "domain": doc.domain,
                "reason": ("cached page does not name this part number; a generic 200 "
                           "page would otherwise attribute one product's "
                           "specifications to another")})
            continue
        model.documents[doc.doc_id] = doc
        model.by_part[doc.part_number] = doc.doc_id
        model.decisions.append(GateDecision(
            url=doc.url, domain=doc.domain, verdict=ADMITTED,
            reason=entry.get("verdict", "manufacturer-owned domain"),
            part_number=doc.part_number))
    return model


# ======================================================================================
# enrichment
# ======================================================================================

# Document spec labels that map onto delivery columns rather than attribute slots.
_DIRECT_FIELDS = {
    "Country of Origin": "COUNTRY_OF_ORIGIN",
    "UPC": "UPC",
    "GTIN": "GTIN",
    "UNSPSC": "UNSPSC",
    "Warranty Term": "WARRANTY_TERM",
    "Energy Star": "ENERGY_STAR",
    "UL Listed": "UL_LISTED",
    "CSA Certified": "CSA_CERTIFIED",
    "ETL Listed": "ETL_LISTED",
    "NSF Certified": "NSF_CERTIFIED",
    "ADA Compliant": "ADA_COMPLIANT",
    "Standard": "CERTIFICATIONS",
    "Series": "SERIES_NAME",
}

_ASSET_FIELDS = {
    "specification sheet": "SPEC_SHEET_URL",
    "spec sheet": "SPEC_SHEET_URL",
    "technical data sheet": "SPEC_SHEET_URL",
    "installation guide": "INSTALL_GUIDE_URL",
    "safety data sheet": "MSDS_URL",
    "material safety data sheet": "MSDS_URL",
    "warranty": "WARRANTY_DOC_URL",
    "brochure": "BROCHURE_URL",
    "cad": "CAD_FILE_URL",
}


def enrich_row(row: Row, ex: Extraction, model: SourcingModel, vocab: Vocabulary,
               rec: RecordEvidence) -> bool:
    doc_id = model.by_part.get(row.part_number)
    if not doc_id:
        return False
    doc = model.documents[doc_id]

    before = len(ex.attributes)
    model.attrs_before += before

    # ---- specification block -> attributes and direct fields ----------------------
    corrected = 0
    for label, (value, a, b) in doc.spec_block().items():
        loc = TT.doc_locator(doc.doc_id, a, b)
        norm = N.normalise_value(value, vocab)
        direct = _DIRECT_FIELDS.get(label)
        if direct:
            rec.claim(direct, norm, SOURCED,
                      f'"{label}" read from {doc.domain} ({doc.url})', loc)
            continue
        existing = next((x for x in ex.attributes if x.label == label), None)
        if existing is None:
            m = N.parse_measure(value, vocab)
            if m and m.unit:
                _add(ex, rec, label, m.magnitude, m.unit, SOURCED,
                     f"read from the manufacturer's own page at {doc.domain}", loc)
            else:
                _add(ex, rec, label, norm, "", SOURCED,
                     f"read from the manufacturer's own page at {doc.domain}", loc)
        else:
            prior = f"{existing.value} {existing.uom}".strip()
            if norm and norm.lower() != prior.lower():
                # the document outranks whatever we had; the ledger settles it
                rec.claim(f"ATTR::{label}", norm, SOURCED,
                          f"manufacturer page states {norm}; supersedes the "
                          f"{existing.kind} value {prior}", loc)
                if existing.kind == "inferred":
                    corrected += 1
                existing.value = norm
                existing.uom = ""
                existing.kind = SOURCED
                existing.rule = (f"manufacturer page at {doc.domain} states {norm}, "
                                 f"which supersedes the inferred value {prior}")
                existing.locator = loc
    model.inferences_corrected += corrected

    # ---- marketing prose ------------------------------------------------------------
    mk = doc.marketing()
    if mk:
        body, a, b = mk
        rec.claim("MARKETING_DESC", body, SOURCED,
                  f"marketing copy taken verbatim from {doc.domain}",
                  TT.doc_locator(doc.doc_id, a, b))
        model.marketing_written += 1

    # ---- features -------------------------------------------------------------------
    feats = doc.features()
    for i, (val, a, b) in enumerate(feats[:C.FEATURE_SLOTS], start=1):
        rec.claim(f"FEATURE_{i:02d}", val, SOURCED,
                  f"feature bullet {i} from {doc.domain}",
                  TT.doc_locator(doc.doc_id, a, b))
    model.features_extracted += len(feats)

    for i, (val, a, b) in enumerate(doc.applications()[:C.APPLICATION_SLOTS], start=1):
        rec.claim(f"APPLICATION_{i:02d}", val, SOURCED,
                  f"application {i} from {doc.domain}",
                  TT.doc_locator(doc.doc_id, a, b))

    # ---- document references and asset provenance ------------------------------------
    refs = doc.documents()
    for label, url, a, b in refs:
        verdict, reason = classify_domain(url, "", vocab)
        field_name = None
        for key, fname in _ASSET_FIELDS.items():
            if key in label.lower():
                field_name = fname
                break
        if not field_name:
            continue
        if domain_of(url) and domain_of(url) not in C.EXCLUDED_DOMAINS:
            rec.claim(field_name, url, SOURCED,
                      f'"{label}" linked from the manufacturer page at {doc.domain}',
                      TT.doc_locator(doc.doc_id, a, b))
    model.document_references += len(refs)
    if refs:
        rec.claim("ASSET_SOURCE_DOMAIN", doc.domain, SOURCED,
                  "documents were taken from this manufacturer-owned domain",
                  TT.doc_locator(doc.doc_id, *refs[0][2:4]))
        rec.claim("ASSET_STATUS", "documents sourced; images not retrieved", SOURCED,
                  "document links found on the manufacturer page; image assets were "
                  "not retrieved in this run",
                  TT.doc_locator(doc.doc_id, *refs[0][2:4]))
        rec.claim("ASSET_COUNT", str(len(refs)), SOURCED,
                  "count of document references found on the manufacturer page",
                  TT.doc_locator(doc.doc_id, *refs[0][2:4]))

    # ---- an abbreviation we had refused to expand, now evidenced ---------------------
    for abbr in list(ex.unexpanded_abbreviations):
        m = re.search(r"[^\n]{0,60}\b" + re.escape(abbr) + r"\b[^\n]{0,60}", doc.text,
                      re.IGNORECASE)
        if not m:
            continue
        a, b = m.start(), m.end()
        rec.claim(f"ABBREV::{abbr}", m.group(0).strip(), SOURCED,
                  f'"{abbr}" was left unexpanded for want of a source; '
                  f"{doc.domain} writes it in context",
                  TT.doc_locator(doc.doc_id, a, b))
        model.abbreviations_evidenced.append({
            "abbreviation": abbr,
            "part_number": row.part_number,
            "quote": m.group(0).strip(),
            "domain": doc.domain,
            "locator": TT.doc_locator(doc.doc_id, a, b),
        })
        ex.unexpanded_abbreviations.remove(abbr)

    # ---- source URL -----------------------------------------------------------------
    t = doc.title()
    if t:
        rec.claim("IMAGE_ALT_TEXT", t[0], SOURCED,
                  f"product title from {doc.domain}, used as image alt text for "
                  f"accessibility", TT.doc_locator(doc.doc_id, t[1], t[2]))

    after = len(ex.attributes)
    model.attrs_after += after
    model.enriched_rows += 1
    model.per_row[row.row_id] = {
        "doc_id": doc.doc_id,
        "url": doc.url,
        "domain": doc.domain,
        "attributes_before": before,
        "attributes_after": after,
        "inferences_corrected": corrected,
        "features": len(feats),
        "document_references": len(refs),
        "reconstructed": doc.reconstructed,
    }
    ex.attributes.sort(key=lambda a: a.sequence)
    return True
