import { useSequence } from '../hooks/useInView'
import { LAYERS } from '../data/content'
import { DISCOVERY } from '../data/metrics'
import { Icon, Reveal, SectionLabel } from './ui'

/**
 * Section 04. Three layers, thin connecting lines, and the note that answers the
 * judge's real question: why isn't this just a prompt?
 */
export default function Architecture() {
  const [ref, active] = useSequence(LAYERS.length, { step: 300, threshold: 0.2 })

  return (
    <section className="section arch" id="how-it-works">
      <div className="shell">
        <div className="split split--wide-left arch__top">
          <div>
            <Reveal>
              <SectionLabel>Architecture</SectionLabel>
            </Reveal>
            <Reveal delay={1} as="h2" className="h-section arch__head">
              LLM extracts.
              <br />
              Rules decide.
              <br />
              <span className="accent">Evidence proves.</span>
            </Reveal>
          </div>
          <Reveal delay={2} className="arch__aside">
            <p className="lede">
              Each layer owns a different kind of decision. Units, limits and casing are
              not judgement calls, so no model is asked to make them. Structure is found
              across rows, which is why a per-row prompt cannot reproduce it.
            </p>
            <p className="note note--accent arch__zeroNote">
              Zero model calls required for the core deterministic pipeline.
            </p>
          </Reveal>
        </div>

        <div className="arch__layers" ref={ref}>
          {LAYERS.map((layer, i) => (
            <div key={layer.id}>
              <div
                className={`layer layer--${layer.tone}${i <= active ? ' is-on' : ''}`}
              >
                <div className="layer__rail" aria-hidden="true">
                  <span className="layer__id mono">Layer {layer.id}</span>
                  <span className="layer__tick" />
                </div>
                <div className="layer__main">
                  <h3 className="h-sub layer__title">{layer.title}</h3>
                  <p className="layer__blurb">{layer.blurb}</p>
                </div>
                <ul className="layer__items">
                  {layer.items.map((it) => (
                    <li key={it} className="layer__item mono">
                      {it}
                    </li>
                  ))}
                </ul>
              </div>
              {i < LAYERS.length - 1 && (
                <div
                  className={`arch__link${i < active ? ' is-on' : ''}`}
                  aria-hidden="true"
                >
                  <span className="arch__linkLine" />
                  <Icon name="arrowDown" size={12} />
                </div>
              )}
            </div>
          ))}
        </div>

        <Reveal delay={2} className="arch__ownership">
          <p className="meta arch__ownershipHead">Who is allowed to decide what</p>
          <dl className="owner">
            {[
              ['Units, fractions, character limits, casing', 'Deterministic code'],
              ['Attribute discovery, vocabulary induction', 'Cross-row statistics'],
              ['Manufacturer / brand resolution, contradictions', 'Entity resolution + rules'],
              ['Naming an ambiguous attribute', 'Model (optional) or human'],
              ['Marketing prose', 'Sourced, or left empty'],
            ].map(([what, who]) => (
              <div className="owner__row" key={what}>
                <dt className="owner__what">{what}</dt>
                <dd className="owner__who mono">{who}</dd>
              </div>
            ))}
          </dl>
          <p className="note arch__ownershipNote">
            Four of the nine pipeline stages read across rows rather than within one. When
            a model is enabled it is charged per family, not per row —{' '}
            <span className="mono">{DISCOVERY.families}</span> calls instead of{' '}
            <span className="mono">1,000</span>.
          </p>
        </Reveal>
      </div>
    </section>
  )
}
