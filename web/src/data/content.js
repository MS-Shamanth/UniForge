/**
 * Copy and structural data, kept out of the components.
 *
 * Nothing in here is a statistic. Figures live in metrics.js so there is exactly one
 * place to check a number against data/out/metrics.json.
 */

export const GITHUB_URL = 'https://github.com/'

export const NAV_LINKS = [
  { label: 'Product', href: '#product' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Evidence', href: '#evidence' },
  { label: 'Results', href: '#results' },
  { label: 'Technology', href: '#technology' },
]

export const HERO_PILLS = ['LLM Extraction', 'Rule-Based Logic', 'Traceable Evidence']

/* The record used as the hero centrepiece — a real row from the compiled catalogue. */
export const HERO_RECORD = {
  sku: '49-94-0013',
  description: 'Metal Cut Off Disc',
  brand: 'Milwaukee',
  attributes: '5 → 11',
  evidence: '2 documents',
  status: 'VERIFIED',
}

export const PIPELINE_STAGES = ['Raw Row', 'Enrich', 'Verify', 'Publish']

/* Section 02 — the raw supplier record, verbatim. */
export const RAW_RECORD = [
  { label: 'SKU', value: '49-94-0013', tone: 'strong' },
  {
    label: 'Description',
    value: 'Milw 5"x.045"x7/8" Metal Cut Off Disc',
    tone: 'default',
  },
  { label: 'Brand', value: '-- Unbranded --', tone: 'placeholder' },
  { label: 'DIB Brand', value: '-- No DIB Brand --', tone: 'placeholder' },
  { label: 'Manufacturer', value: '-- incomplete --', tone: 'placeholder' },
]

/* Section 03 — normalisation rules discovered, not configured. */
export const DISCOVERED_RULES = [
  { from: '5"', to: '5 in' },
  { from: '0.045"', to: '0.045 in' },
  { from: '7/8"', to: '7/8 in' },
]

/* Section 04 — the three layers. */
export const LAYERS = [
  {
    id: '01',
    title: 'LLM Extraction',
    blurb: 'Extract candidate values from messy product text.',
    items: ['Candidate attributes', 'Ambiguous labels', 'Free-text signals'],
    tone: 'default',
  },
  {
    id: '02',
    title: 'Deterministic Rule Engine',
    blurb: 'Decide what is publishable, and in what form.',
    items: [
      'Units',
      'Formatting',
      'Limits',
      'UOM',
      'Vocabulary',
      'Cross-row consistency',
    ],
    tone: 'accent',
  },
  {
    id: '03',
    title: 'Evidence / Provenance',
    blurb: 'Prove it, or withhold it.',
    items: [
      'Manufacturer source',
      'Document',
      'Character span',
      'Confidence',
      'Audit trail',
    ],
    tone: 'default',
  },
]

/* Section 05 — the six 3M rows that reveal an attribute nobody defined. */
export const FAMILY_ROWS = [
  { pn: '3MABR-7100075678', pre: '3M 775L Stikit Film [', axis: 'P150', post: ']' },
  { pn: '3MABR-7100045865', pre: '3M 775L Stikit Film [', axis: 'P120', post: ']' },
  { pn: '3MABR-7100048736', pre: '3M 775L Stikit Film [', axis: 'P80', post: ' ]' },
  { pn: '3MABR-7100075690', pre: '3M 775L Stikit Film [', axis: 'P180', post: ']' },
  { pn: '3MABR-7100075692', pre: '3M 775L Stikit Film [', axis: 'P220', post: ']' },
  { pn: '3MABR-7100145365', pre: '3M 775L Stikit Film [', axis: 'P320', post: ']' },
]

export const FAMILY_SUFFIX = ' - Cubitron II 50 Disc/Box'

/* Section 05b — co-occurrence recovers a structure nothing declared. */
export const COOCCURRENCE = [
  {
    label: 'Collection',
    values: ['Harvest', 'Landmark', 'Vintage'],
    named: false,
  },
  {
    label: 'Colour',
    values: [
      'Brownstone',
      'Coastline',
      'Mahogany',
      'Weathered Teak',
      'Slate Gray',
      'Castle Gate',
    ],
    named: true,
  },
]

/* Section 07 — one evidence chain, top to bottom. */
export const EVIDENCE_CHAIN = [
  { step: 'Product Attribute', value: 'Package Quantity: 25 pc', icon: 'node' },
  { step: 'Source', value: 'Manufacturer document', icon: 'shield' },
  { step: 'Document', value: 'milwaukeetool.com — product page', icon: 'document' },
  { step: 'Location', value: 'doc:49-94-0013#char[1310:1315]', icon: 'search' },
]

/* Section 08 — the three trust states. */
export const TRUST_STATES = [
  {
    id: '01',
    name: 'Verified',
    action: 'Publish',
    blurb: 'Manufacturer source confirms the value.',
    marker: 'Source match',
    tone: 'verified',
  },
  {
    id: '02',
    name: 'Inferred',
    action: 'Flag',
    blurb: 'Pattern suggests a value, but evidence is incomplete.',
    marker: 'Review required',
    tone: 'review',
  },
  {
    id: '03',
    name: 'Unsupported',
    action: 'Abstain',
    blurb: 'No authoritative evidence available.',
    marker: 'Do not guess',
    tone: 'abstain',
  },
]

/* Section 09 — the contradiction, reproduced from the reference file. */
export const CONTRADICTION = {
  manufacturer: 'Rheem Manufacturing',
  brand: 'FRIGIDAIRE®',
  mobileDesc: 'Rheem Manufacturing FRIGIDAIRE, Dishwasher, ...',
  reasoning:
    'FRIGIDAIRE® is a brand of Electrolux Home Products, Inc., but the record names Rheem Manufacturing as the manufacturer. Rheem makes water heaters, boilers and HVAC equipment. Electrolux makes major kitchen and laundry appliances.',
  verdict: 'These cannot both be correct.',
}

/* Section 10 — one decision, many records. */
export const HUMAN_LOOP_CHAIN = [
  '1 human decision',
  'Multiple product records',
  'Rule / group update',
  'Catalogue improves',
]

/* Section 12 / footer */
export const FOOTER_LINKS = [
  { label: 'Product', href: '#product' },
  { label: 'Technology', href: '#technology' },
  { label: 'Evidence', href: '#evidence' },
  { label: 'Results', href: '#results' },
]
