import { useInView } from '../hooks/useInView'
import { HUMAN_LOOP_CHAIN } from '../data/content'
import { REVIEW } from '../data/metrics'
import { Icon, Reveal, SectionLabel } from './ui'

/**
 * Section 10. The review queue is not a list of rows, it is a list of decisions. The
 * fan-out visual says that in one glance: one node, many records.
 */
export default function HumanLoop() {
  const [ref, inView] = useInView({ threshold: 0.28 })

  const blockers = [
    {
      records: REVIEW.itemTypeRecords,
      actions: REVIEW.itemTypeMappings,
      label: 'Item type outside the taxonomy',
      action: `Map item types to a classpath → unblocks ${REVIEW.itemTypeUnblocks} records`,
    },
    {
      records: REVIEW.attributeNameRecords,
      actions: REVIEW.attributeNameDecisions,
      label: 'Attribute label awaiting a name',
      action: `Name ${REVIEW.attributeNameDecisions} induced groups, once each`,
    },
    {
      records: REVIEW.coverageRecords,
      actions: null,
      label: 'Attribute coverage below target',
      action: 'Confirm the induced attributes for the family',
    },
    {
      records: REVIEW.contradictionRecords,
      actions: REVIEW.contradictionRecords,
      label: 'Source contradiction',
      action: 'Resolve with the manufacturer',
    },
  ]

  // 12 satellite records fanned around one decision node
  const satellites = Array.from({ length: 12 }, (_, i) => {
    const angle = (i / 12) * Math.PI * 2 - Math.PI / 2
    return {
      x: 50 + Math.cos(angle) * 37,
      y: 50 + Math.sin(angle) * 37,
      d: i * 55,
    }
  })

  return (
    <section className="section loop">
      <div className="shell">
        <div className="section__head">
          <Reveal>
            <SectionLabel>Human in the loop</SectionLabel>
          </Reveal>
          <Reveal delay={1} as="h2" className="h-section">
            Human review becomes <span className="accent">leverage.</span>
          </Reveal>
          <Reveal delay={2} as="p" className="lede">
            The queue is not{' '}
            {Math.round(
              (REVIEW.reviewPct / 100) * 1000
            ).toLocaleString()}{' '}
            rows of work. It is a short list of one-decision-per-group actions, and each
            one carries its own leverage.
          </Reveal>
        </div>

        <div className="split loop__body">
          {/* the fan-out */}
          <Reveal delay={2}>
            <div className={`fan${inView ? ' is-in' : ''}`} ref={ref}>
              <svg className="fan__svg" viewBox="0 0 100 100" aria-hidden="true">
                {satellites.map((s, i) => (
                  <line
                    key={i}
                    x1="50"
                    y1="50"
                    x2={s.x}
                    y2={s.y}
                    className="fan__edge"
                    style={{ transitionDelay: `${s.d}ms` }}
                  />
                ))}
                {satellites.map((s, i) => (
                  <circle
                    key={`n${i}`}
                    cx={s.x}
                    cy={s.y}
                    r="2"
                    className="fan__node"
                    style={{ transitionDelay: `${s.d + 180}ms` }}
                  />
                ))}
                <circle cx="50" cy="50" r="12" className="fan__halo" />
                <circle cx="50" cy="50" r="5.5" className="fan__core" />
              </svg>
              <div className="fan__caption">
                <span className="meta">One decision</span>
                <span className="fan__value mono">
                  applied to {REVIEW.nameItAppliedTo} products
                </span>
              </div>
            </div>

            <ol className="loop__chain">
              {HUMAN_LOOP_CHAIN.map((step, i) => (
                <li className="loop__step" key={step}>
                  <span className="loop__stepNum mono">{i + 1}</span>
                  <span className="loop__stepText">{step}</span>
                  {i < HUMAN_LOOP_CHAIN.length - 1 && (
                    <Icon name="arrowDown" size={11} className="loop__stepArrow" />
                  )}
                </li>
              ))}
            </ol>
          </Reveal>

          {/* the blockers, each with the action that clears it */}
          <Reveal delay={3} className="loop__blockers">
            <div className="loop__ratio">
              <div className="loop__ratioBar" aria-hidden="true">
                <span
                  className="loop__ratioFill"
                  style={{ width: `${REVIEW.autoPublishPct}%` }}
                />
              </div>
              <div className="loop__ratioLabels">
                <span className="mono">
                  {REVIEW.autoPublishPct}% <span className="dim">auto-publish</span>
                </span>
                <span className="mono dim">{REVIEW.reviewPct}% to review</span>
              </div>
            </div>

            {blockers.map((b) => (
              <div className="blocker" key={b.label}>
                <div className="blocker__nums">
                  <span className="blocker__records mono">{b.records}</span>
                  <span className="blocker__unit meta">records</span>
                  {b.actions != null && (
                    <>
                      <span className="blocker__sep" aria-hidden="true" />
                      <span className="blocker__actions mono">{b.actions}</span>
                      <span className="blocker__unit meta">
                        {b.actions === 1 ? 'action' : 'actions'}
                      </span>
                    </>
                  )}
                </div>
                <p className="blocker__label">{b.label}</p>
                <p className="blocker__action">{b.action}</p>
              </div>
            ))}
          </Reveal>
        </div>
      </div>
    </section>
  )
}
