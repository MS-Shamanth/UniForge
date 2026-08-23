import { COMPLIANCE, SEARCH } from '../data/metrics'
import { Reveal, SectionLabel } from './ui'
import { useCountUp } from '../hooks/useInView'

/**
 * Section 11. A 2×3 grid of measured results, then the one metric that went the wrong
 * way — given its own panel rather than a footnote, because volunteering it is the point.
 */
function Cell({ index, value, label, sub, tone = 'default' }) {
  return (
    <div className={`result result--${tone}`}>
      <span className="result__idx mono">Metric {index}</span>
      <span className="result__value mono">{value}</span>
      <span className="result__label">{label}</span>
      {sub ? <span className="result__sub mono">{sub}</span> : null}
    </div>
  )
}

export default function Results() {
  const [pcRef, pcVal] = useCountUp(COMPLIANCE.populatedCellsAfter)

  const cells = [
    {
      value: COMPLIANCE.rowsCompiled.toLocaleString(),
      label: 'Rows compiled',
      sub: `${COMPLIANCE.compileSeconds} s`,
    },
    {
      value: `${COMPLIANCE.characterLimitPct.toFixed(2)}%`,
      label: 'Character-limit compliance',
      sub: `${COMPLIANCE.characterLimitChecks.toLocaleString()} checks`,
    },
    {
      value: `${COMPLIANCE.approvedUnitPct.toFixed(2)}%`,
      label: 'Approved-unit compliance',
    },
    {
      value: `${COMPLIANCE.roundTripPct.toFixed(2)}%`,
      label: 'Round-trip verification',
      sub: `${COMPLIANCE.hallucinations} hallucinations`,
    },
    {
      value: `${COMPLIANCE.populatedCellsBefore.toLocaleString()} → ${COMPLIANCE.populatedCellsAfter.toLocaleString()}`,
      label: 'Populated cells',
      sub: `×${COMPLIANCE.populatedCellFactor}`,
      tone: 'accent',
    },
    {
      value: `${SEARCH.mrrBefore} → ${SEARCH.mrrAfter}`,
      label: 'MRR@10, trade queries',
      tone: 'accent',
    },
  ]

  return (
    <section className="section res" id="results">
      <div className="shell">
        <div className="section__head">
          <Reveal>
            <SectionLabel>Results</SectionLabel>
          </Reveal>
          <Reveal delay={1} as="h2" className="h-section">
            Measured, not marketed.
          </Reveal>
        </div>

        <Reveal delay={2} className="res__grid" ref={pcRef}>
          {cells.map((c, i) => (
            <Cell
              key={c.label}
              index={String(i + 1).padStart(2, '0')}
              value={c.value}
              label={c.label}
              sub={c.sub}
              tone={c.tone}
            />
          ))}
        </Reveal>

        <div className="res__lower">
          {/* search readiness */}
          <Reveal delay={2} className="res__search">
            <p className="meta res__searchHead">
              Search readiness — does the buyer find the part?
            </p>
            <div className="res__searchRows">
              <div className="searchrow">
                <span className="searchrow__label">
                  recall@10, vocabulary-gap queries
                </span>
                <span className="searchrow__pair mono">
                  <span className="dim">{SEARCH.gapRecallBefore.toFixed(1)}%</span>
                  <span className="searchrow__arrow">→</span>
                  <span className="accent">{SEARCH.gapRecallAfter}%</span>
                </span>
              </div>
              <div className="searchrow">
                <span className="searchrow__label">zero-result rate</span>
                <span className="searchrow__pair mono">
                  <span className="dim">{SEARCH.zeroResultBefore}%</span>
                  <span className="searchrow__arrow">→</span>
                  <span className="accent">{SEARCH.zeroResultAfter.toFixed(1)}%</span>
                </span>
              </div>
              <div className="searchrow">
                <span className="searchrow__label">MRR@10, trade queries</span>
                <span className="searchrow__pair mono">
                  <span className="dim">{SEARCH.mrrBefore}</span>
                  <span className="searchrow__arrow">→</span>
                  <span className="accent">{SEARCH.mrrAfter}</span>
                </span>
              </div>
            </div>
            <p className="note res__searchNote">
              Queries are built only from raw supplier text expanded through the seed
              lexicon. No generated text is used to build any query, and part numbers are
              stripped because a unique key inflates any baseline.
            </p>
          </Reveal>

          {/* the honest metric */}
          <Reveal delay={3} className="res__honest">
            <div className="honest">
              <header className="honest__head">
                <span className="meta">Exact-item recall@10</span>
                <span className="honest__tag">Trade-off observed</span>
              </header>
              <div className="honest__pair mono">
                <span className="honest__before">{SEARCH.exactRecallBefore}%</span>
                <span className="honest__arrow">→</span>
                <span className="honest__after">
                  {SEARCH.exactRecallAfter.toFixed(1)}%
                </span>
              </div>
              <p className="honest__why">
                Family normalization improves category-level retrieval while exact-row
                ranking can decline. Members of a normalised family look more alike, so
                they compete with each other for the same query.
              </p>
              <p className="honest__foot meta">
                Reported because it did not flatter us
              </p>
            </div>
          </Reveal>
        </div>

        <Reveal delay={2} className="res__checks">
          <span className="mono res__checksValue">
            {COMPLIANCE.selfChecksPassed}/{COMPLIANCE.selfChecksTotal}
          </span>
          <span className="metric__label">
            Self-checks passing — the run asserts these about itself on every compile
          </span>
        </Reveal>
      </div>
    </section>
  )
}
