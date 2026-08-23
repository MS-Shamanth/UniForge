/**
 * UniForge figures.
 *
 * PROVENANCE — read this before changing a number.
 *
 * These are the measured figures from the UniHack submission run. Nothing here is
 * illustrative and nothing is rounded up. The pipeline recomputes all of them on every
 * compile and writes them to data/out/metrics.json.
 *
 * To show the numbers from a run on your own machine instead:
 *
 *     python -m uniforge.cli compile
 *     python tools/export_web_metrics.py     # regenerates ./live.js
 *
 * then set USE_LIVE_FIGURES to true. Live figures will differ from the submission run,
 * because data/in/ holds a reconstruction catalogue rather than the client's own 1,000-row
 * file — which is exactly why this switch is explicit rather than silent.
 *
 * A figure that is not in metrics.json does not belong on this page.
 */
import * as LIVE from './live'

export const USE_LIVE_FIGURES = false

/** Live values override the submission run key by key, so a missing key never blanks. */
const pick = (submission, live) =>
  USE_LIVE_FIGURES && live ? { ...submission, ...live } : submission

export const TAGLINE = 'LLM extracts. Rules decide. Evidence proves.'

export const AUTHORS = ['Shamanth', 'Shreya BJ']

export const EVENT = {
  name: 'UniHack 2026',
  challenge: 'AI-Powered Product Intelligence for Industrial Commerce',
}

/* ── the input, as received ───────────────────────────────────────────────── */
const S_INPUT = {
  placeholderBrandPct: 86.5,
  meanDescriptionChars: 38,
  deliveryHeaders: 252,
  rawRows: 1000,
  rawColumns: 6,
}

/* ── what was learned from the catalogue, with no dictionary supplied ─────── */
const S_DISCOVERY = {
  families: 165,
  variantAxes: 158,
  inferredLabels: 16,
  modelCalls: 0,
  categoricalAttributes: 48,
  labelsNeedingOneName: 46,
}

/* ── enrichment from manufacturer documents ───────────────────────────────── */
const S_ENRICHMENT = {
  attributesBefore: 4.74,
  attributesAfter: 9.79,
  factor: 2.06,
  deliveryCellsBefore: 26,
  deliveryCellsAfter: 57,
  marketingDescriptions: 39,
  featureBullets: 374,
  documentReferences: 78,
  candidatesConsidered: 57,
  admitted: 39,
  rejectedBeforeRequest: 4,
  blockedBySite: 2,
  inferencesCorrected: 20,
  sourcedRows: 39,
  sourcedOfTotal: 1000,
}

/* ── compliance and integrity ─────────────────────────────────────────────── */
const S_COMPLIANCE = {
  rowsCompiled: 1000,
  compileSeconds: 0.66,
  characterLimitPct: 100.0,
  characterLimitChecks: 5000,
  approvedUnitPct: 100.0,
  roundTripPct: 100.0,
  hallucinations: 0,
  populatedCellsBefore: 3405,
  populatedCellsAfter: 22460,
  populatedCellFactor: 6.6,
  selfChecksPassed: 14,
  selfChecksTotal: 14,
}

/* ── search readiness, including the metric that went the wrong way ───────── */
const S_SEARCH = {
  gapRecallBefore: 0.0,
  gapRecallAfter: 33.5,
  zeroResultBefore: 6.3,
  zeroResultAfter: 0.0,
  mrrBefore: 0.787,
  mrrAfter: 0.938,
  exactRecallBefore: 92.7,
  exactRecallAfter: 88.0,
}

/* ── refusals ─────────────────────────────────────────────────────────────── */
const S_ABSTENTION = {
  cellsLeftEmpty: 16000,
  mobileDescriptionsLeftShort: 851,
  abbreviationsLeftUnexpanded: 142,
  propagationsBlocked: 71,
}

/* ── human in the loop ────────────────────────────────────────────────────── */
const S_REVIEW = {
  autoPublishPct: 44.9,
  reviewPct: 55.1,
  itemTypeRecords: 288,
  itemTypeMappings: 245,
  itemTypeUnblocks: 489,
  attributeNameRecords: 161,
  attributeNameDecisions: 31,
  coverageRecords: 86,
  contradictionRecords: 3,
  nameItAppliedTo: 98,
}

/* ── entity resolution ────────────────────────────────────────────────────── */
const S_ENTITY = {
  manufacturersUnmasked: 184,
  contradictionsFound: 3,
  contradictionConfidence: 34,
}

export const INPUT = pick(S_INPUT, LIVE.INPUT)
export const DISCOVERY = pick(S_DISCOVERY, LIVE.DISCOVERY)
export const ENRICHMENT = pick(S_ENRICHMENT, LIVE.ENRICHMENT)
export const COMPLIANCE = pick(S_COMPLIANCE, LIVE.COMPLIANCE)
export const SEARCH = pick(S_SEARCH, LIVE.SEARCH)
export const ABSTENTION = pick(S_ABSTENTION, LIVE.ABSTENTION)
export const REVIEW = pick(S_REVIEW, LIVE.REVIEW)
export const ENTITY = pick(S_ENTITY, LIVE.ENTITY)
