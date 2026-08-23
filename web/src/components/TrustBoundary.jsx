import { useSequence } from '../hooks/useInView'
import { TRUST_STATES } from '../data/content'
import { ABSTENTION } from '../data/metrics'
import { Icon, Reveal, SectionLabel } from './ui'

/**
 * Section 08. Three states, activated in sequence. The strongest section on the page,
 * because refusing to guess is the differentiator and it deserves the space.
 */
const MARK_ICON = { verified: 'check', review: 'warning', abstain: 'minus' }

export default function TrustBoundary() {
  const [ref, active] = useSequence(TRUST_STATES.length, { step: 320, threshold: 0.24 })

  const refusals = [
    { value: ABSTENTION.cellsLeftEmpty, label: 'Delivery cells left empty' },
    {
      value: ABSTENTION.mobileDescriptionsLeftShort,
      label: 'Mobile descriptions left short',
    },
    {
      value: ABSTENTION.abbreviationsLeftUnexpanded,
      label: 'Abbreviations left unexpanded',
    },
    {
      value: ABSTENTION.propagationsBlocked,
      label: 'Propagations blocked by the axis rule',
    },
  ]

  return (
    <section className="section trust">
      <div className="shell">
        <div className="section__head trust__head">
          <Reveal>
            <SectionLabel>Trust boundaries</SectionLabel>
          </Reveal>
          <Reveal delay={1} as="h2" className="h-section">
            UniForge Knows When Not to Guess.
          </Reveal>
          <Reveal delay={2} as="p" className="lede">
            Missing data is acceptable. Unsupported data is not.
          </Reveal>
        </div>

        <div className="trust__states" ref={ref}>
          {TRUST_STATES.map((s, i) => (
            <article
              key={s.id}
              className={`state state--${s.tone}${i <= active ? ' is-on' : ''}`}
            >
              <header className="state__head">
                <span className="state__id mono">{s.id}</span>
                <span className="state__name">{s.name}</span>
              </header>
              <p className="state__action mono">{s.action}</p>
              <p className="state__blurb">{s.blurb}</p>
              <footer className="state__foot">
                <Icon name={MARK_ICON[s.tone]} size={12} />
                <span className="meta">{s.marker}</span>
              </footer>
            </article>
          ))}
        </div>

        <Reveal delay={2} className="trust__refusals">
          <p className="meta trust__refusalsHead">
            Measured refusals, from the last compile
          </p>
          <div className="trust__refusalGrid">
            {refusals.map((r) => (
              <div className="trust__refusal" key={r.label}>
                <span className="trust__refusalValue mono">
                  {r.value.toLocaleString()}
                </span>
                <span className="metric__label">{r.label}</span>
              </div>
            ))}
          </div>
          <p className="note trust__rule">
            A fact with no locator cannot be published. Enforced in code, not requested in
            a prompt.
          </p>
        </Reveal>

        <Reveal delay={3} className="trust__closer">
          <span className="trust__closerText">
            Evidence <span className="accent">&gt;</span> Inference
          </span>
        </Reveal>
      </div>
    </section>
  )
}
