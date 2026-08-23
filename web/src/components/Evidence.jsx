import { useSequence } from '../hooks/useInView'
import { EVIDENCE_CHAIN } from '../data/content'
import { COMPLIANCE, ENRICHMENT } from '../data/metrics'
import { Icon, Reveal, SectionLabel, StatusBadge } from './ui'

/**
 * Section 07. One value, traced all the way down to the characters that justify it.
 *
 * The right-hand panel is the important half: it shows the funnel from candidate to
 * admitted source, so it is clear that most candidates were refused. Presenting
 * 57 → 39 without the refusals would imply every candidate passed.
 */
export default function Evidence() {
  const [ref, active] = useSequence(EVIDENCE_CHAIN.length, { step: 260 })

  const funnel = [
    {
      label: 'Candidates considered',
      value: ENRICHMENT.candidatesConsidered,
      tone: 'neutral',
    },
    {
      label: 'Admitted — manufacturer-owned',
      value: ENRICHMENT.admitted,
      tone: 'pass',
    },
    {
      label: 'Rejected before any request',
      value: ENRICHMENT.rejectedBeforeRequest,
      tone: 'stop',
      note: 'Marketplaces and distributor sites are excluded by the brief',
    },
    {
      label: 'Admitted, then refused by the site',
      value: ENRICHMENT.blockedBySite,
      tone: 'warn',
      note: 'HTTP 403 and a connection timeout',
    },
  ]

  return (
    <section className="section ev" id="evidence">
      <div className="grid-bleed" aria-hidden="true" />
      <div className="shell">
        <div className="section__head">
          <Reveal>
            <SectionLabel>Evidence</SectionLabel>
          </Reveal>
          <Reveal delay={1} as="h2" className="h-section">
            Every populated value needs
            <br />
            <span className="accent">somewhere to point.</span>
          </Reveal>
        </div>

        <div className="split ev__body">
          {/* the chain */}
          <Reveal delay={2}>
            <div className="ev__chain" ref={ref}>
              {EVIDENCE_CHAIN.map((node, i) => (
                <div key={node.step}>
                  <div className={`evnode${i <= active ? ' is-on' : ''}`}>
                    <span className="evnode__icon">
                      <Icon name={node.icon} size={14} />
                    </span>
                    <div className="evnode__main">
                      <span className="evnode__step meta">{node.step}</span>
                      <span className="evnode__value mono">{node.value}</span>
                    </div>
                  </div>
                  {i < EVIDENCE_CHAIN.length - 1 && (
                    <div
                      className={`evnode__link${i < active ? ' is-on' : ''}`}
                      aria-hidden="true"
                    >
                      <span />
                    </div>
                  )}
                </div>
              ))}
              <div className={`evnode evnode--final${active >= 3 ? ' is-on' : ''}`}>
                <span className="evnode__icon evnode__icon--ok">
                  <Icon name="check" size={14} />
                </span>
                <div className="evnode__main">
                  <span className="evnode__step meta">Status</span>
                  <StatusBadge tone="verified">Verified</StatusBadge>
                </div>
              </div>
            </div>

            <p className="note ev__note">
              A cached page must name the part number it is filed under or it is discarded.
              Without that check a generic 200 response would quietly attribute one
              product&rsquo;s specifications to another.
            </p>
          </Reveal>

          {/* the funnel */}
          <Reveal delay={3} className="ev__right">
            <div className="ev__proof">
              <span className="ev__proofValue mono">
                {COMPLIANCE.roundTripPct.toFixed(2)}%
              </span>
              <span className="metric__label">Character-level proofs</span>
              <p className="note">
                Round-trip verification re-parses UniForge&rsquo;s own output and traces
                every number to a source. It needs no ground truth, so it works on the
                full catalogue and not only on the rows with a known answer.{' '}
                <span className="mono">{COMPLIANCE.hallucinations}</span> hallucinations
                across {COMPLIANCE.rowsCompiled.toLocaleString()} records.
              </p>
            </div>

            <div className="funnel">
              <p className="meta funnel__head">The sourcing gate</p>
              {funnel.map((f) => (
                <div className={`funnel__row funnel__row--${f.tone}`} key={f.label}>
                  <span className="funnel__value mono">{f.value}</span>
                  <span className="funnel__label">
                    {f.label}
                    {f.note ? <em className="funnel__note">{f.note}</em> : null}
                  </span>
                </div>
              ))}
              <p className="note funnel__foot">
                Classification happens <strong>before</strong> a request is made, so an
                excluded source is never even contacted.
              </p>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
