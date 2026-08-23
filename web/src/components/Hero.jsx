import { useSequence } from '../hooks/useInView'
import { HERO_PILLS, HERO_RECORD, PIPELINE_STAGES } from '../data/content'
import { ENRICHMENT } from '../data/metrics'
import { Field, Icon, Reveal, StatusBadge } from './ui'

/**
 * The hero carries the whole argument in five seconds: a raw row becomes a verified
 * record, and the record shows its evidence. The right-hand composition is a product
 * interface, not an illustration — the values are the ones the compiler produces.
 */
export default function Hero() {
  const [vizRef, activeStage] = useSequence(PIPELINE_STAGES.length, { step: 260 })

  return (
    <section className="hero" id="top">
      <div className="hero__grid" aria-hidden="true" />
      <div className="hero__glow" aria-hidden="true" />

      <div className="shell hero__inner">
        {/* ── left: the claim ─────────────────────────────────────────── */}
        <div className="hero__copy">
          <Reveal as="p" className="hero__eyebrow meta">
            AI-Powered Product Intelligence
          </Reveal>

          <Reveal delay={1} as="h1" className="h-display hero__head">
            From Raw Product Data
            <br />
            to <span className="accent">Verified Intelligence.</span>
          </Reveal>

          <Reveal delay={2} as="p" className="lede hero__lede">
            UniForge transforms sparse supplier data into structured, enriched and
            evidence-backed product intelligence — without guessing what the source does
            not prove.
          </Reveal>

          <Reveal delay={3} className="hero__actions">
            <a className="btn btn--primary" href="#how-it-works">
              Explore the Pipeline
              <Icon name="arrow" size={14} className="btn__arrow" />
            </a>
            <a className="btn btn--ghost" href="#evidence">
              See the Evidence
            </a>
          </Reveal>

          <Reveal delay={4} className="hero__pills">
            {HERO_PILLS.map((p) => (
              <span className="pill" key={p}>
                <span className="pill__dot" aria-hidden="true" />
                {p}
              </span>
            ))}
          </Reveal>
        </div>

        {/* ── right: the record, and the path it travelled ────────────── */}
        <div className="hero__viz" ref={vizRef}>
          <div className="hero__rail" aria-hidden="true">
            {PIPELINE_STAGES.map((stage, i) => (
              <div
                key={stage}
                className={`rail__stop${i <= activeStage ? ' is-on' : ''}`}
              >
                <span className="rail__node" />
                <span className="rail__label meta">{stage}</span>
                {i < PIPELINE_STAGES.length - 1 && <span className="rail__link" />}
              </div>
            ))}
          </div>

          <Reveal delay={3} className="hero__card">
            <div className="datacard datacard--accent">
              <header className="datacard__head">
                <span className="datacard__title meta">Compiled Record</span>
                <StatusBadge tone="verified">{HERO_RECORD.status}</StatusBadge>
              </header>
              <div className="datacard__body">
                <Field label="SKU" value={HERO_RECORD.sku} tone="strong" />
                <Field label="Description" value={HERO_RECORD.description} />
                <Field label="Brand" value={HERO_RECORD.brand} />
                <Field label="Attributes" value={HERO_RECORD.attributes} tone="accent" />
                <Field label="Evidence" value={HERO_RECORD.evidence} tone="accent" />
              </div>
              <footer className="datacard__foot">
                <span className="mono">doc:49-94-0013#char[1310:1315]</span>
              </footer>
            </div>
          </Reveal>
        </div>
      </div>

      {/* ── the floor: two restrained figures ──────────────────────────── */}
      <div className="shell">
        <Reveal delay={5} className="hero__floor">
          <div className="hero__floorItem">
            <span className="hero__floorValue mono">
              {ENRICHMENT.attributesBefore} <span className="dim">→</span>{' '}
              {ENRICHMENT.attributesAfter}
            </span>
            <span className="metric__label">Avg. attributes / product</span>
          </div>
          <span className="hero__floorDiv" aria-hidden="true" />
          <div className="hero__floorItem">
            <span className="hero__floorValue mono accent">
              ×{ENRICHMENT.factor}
            </span>
            <span className="metric__label">Enrichment factor</span>
          </div>
          <span className="hero__floorSpacer" />
          <a className="hero__scroll" href="#product">
            <span className="meta">Scroll</span>
            <Icon name="arrowDown" size={13} />
          </a>
        </Reveal>
      </div>
    </section>
  )
}
