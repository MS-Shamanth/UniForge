import { ENRICHMENT } from '../data/metrics'
import { Delta, Metric, Reveal, SectionLabel } from './ui'

/**
 * Section 06. The enrichment result, and the reason it is trustworthy: coverage is
 * stated, not implied. 39 of 1,000 rows have a cached manufacturer source, and that
 * limit is printed next to the gain rather than buried.
 */
export default function Enrichment() {
  const coverage = (
    (ENRICHMENT.sourcedRows / ENRICHMENT.sourcedOfTotal) *
    100
  ).toFixed(1)

  return (
    <section className="section enrich">
      <div className="shell">
        <div className="section__head">
          <Reveal>
            <SectionLabel>Enrichment</SectionLabel>
          </Reveal>
          <Reveal delay={1} as="h2" className="h-section">
            More data is useful.
            <br />
            <span className="accent">Verified data is valuable.</span>
          </Reveal>
        </div>

        {/* the centrepiece: before, factor, after */}
        <Reveal delay={2} className="enrich__core">
          <div className="enrich__side">
            <Metric
              size="lg"
              countTo={ENRICHMENT.attributesBefore}
              decimals={2}
              label="Avg attributes / product"
              sub="From the supplier row alone"
            />
          </div>

          <div className="enrich__mid" aria-hidden="true">
            <span className="enrich__track">
              <span className="enrich__fill" />
            </span>
            <div className="enrich__factor">
              <span className="enrich__factorValue mono">×{ENRICHMENT.factor}</span>
              <span className="metric__label">Enrichment factor</span>
            </div>
            <span className="enrich__track">
              <span className="enrich__fill" />
            </span>
          </div>

          <div className="enrich__side enrich__side--after">
            <Metric
              size="lg"
              tone="accent"
              countTo={ENRICHMENT.attributesAfter}
              decimals={2}
              label="Avg attributes / product"
              sub="After reading the manufacturer's own documents"
            />
          </div>
        </Reveal>

        {/* supporting figures, hairline-separated rather than carded */}
        <Reveal delay={3} className="statstrip statstrip--4 enrich__stats">
          <Delta
            before={ENRICHMENT.deliveryCellsBefore}
            after={ENRICHMENT.deliveryCellsAfter}
            label="Delivery cells filled"
            tone="accent"
          />
          <Metric
            size="sm"
            countTo={ENRICHMENT.marketingDescriptions}
            label="Marketing descriptions"
            sub="Written by the manufacturer, not by us"
          />
          <Metric
            size="sm"
            countTo={ENRICHMENT.featureBullets}
            label="Feature bullets"
            sub="Extracted from maker pages"
          />
          <Metric
            size="sm"
            countTo={ENRICHMENT.documentReferences}
            label="Document references"
            sub="Spec sheets and safety data"
          />
        </Reveal>

        {/* the limit, stated plainly */}
        <Reveal delay={4} className="enrich__limit">
          <span className="meta">Coverage</span>
          <p className="enrich__limitText">
            <span className="mono">{ENRICHMENT.sourcedRows}</span> of{' '}
            <span className="mono">
              {ENRICHMENT.sourcedOfTotal.toLocaleString()}
            </span>{' '}
            rows have a cached manufacturer source —{' '}
            <span className="mono accent">{coverage}%</span>. The extraction is not
            product-specific; candidate URLs are built from a product&rsquo;s own
            dimensions, which is how a handful of hand-listed pages became{' '}
            <span className="mono">{ENRICHMENT.admitted}</span> cached documents.
          </p>
        </Reveal>
      </div>
    </section>
  )
}
