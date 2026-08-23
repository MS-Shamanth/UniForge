import { DISCOVERED_RULES } from '../data/content'
import { DISCOVERY, INPUT } from '../data/metrics'
import { Icon, Reveal, SectionLabel } from './ui'

/**
 * Section 03. The constraint that became the idea. No manufacturer list, no list of
 * values, no UOM standard — so the catalogue had to serve as its own dictionary. The
 * discovered-rule strip is the proof that normalisation was derived, not configured.
 */
export default function Methodology() {
  const flow = [
    { top: `${INPUT.rawRows.toLocaleString()} raw rows`, bottom: `${INPUT.deliveryHeaders} headers` },
    { top: 'Structure discovery', bottom: 'cross-row statistics' },
    { top: 'Rules', bottom: 'units · limits · vocabulary' },
    { top: 'Normalized catalogue', bottom: 'evidence on every field' },
  ]

  return (
    <section className="section section--tight idea">
      <div className="grid-bleed" aria-hidden="true" />
      <div className="shell">
        <div className="section__head">
          <Reveal>
            <SectionLabel>The constraint that became the idea</SectionLabel>
          </Reveal>
          <Reveal delay={1} as="h2" className="h-section">
            We weren&rsquo;t given the rulebook.
            <br />
            So UniForge <span className="accent">learned it from the catalogue.</span>
          </Reveal>
        </div>

        {/* the flow, as four labelled stops on one line */}
        <Reveal delay={2} className="idea__flow">
          {flow.map((f, i) => (
            <div className="idea__stop" key={f.top}>
              <div className="idea__stopBody">
                <span className="idea__stopTop">{f.top}</span>
                <span className="idea__stopBottom meta">{f.bottom}</span>
              </div>
              {i < flow.length - 1 && (
                <Icon name="arrow" size={14} className="idea__stopArrow" />
              )}
            </div>
          ))}
        </Reveal>

        <div className="idea__proof">
          <Reveal delay={3} className="idea__rules">
            <p className="meta idea__rulesHead">Rules discovered, not configured</p>
            {DISCOVERED_RULES.map((r) => (
              <div className="ruleline" key={r.from}>
                <span className="ruleline__from mono">{r.from}</span>
                <Icon name="arrow" size={13} className="ruleline__arrow" />
                <span className="ruleline__to mono">{r.to}</span>
              </div>
            ))}
            <div className="ruleline ruleline--guard">
              <span className="ruleline__from mono">Variant axis detected</span>
              <Icon name="arrow" size={13} className="ruleline__arrow" />
              <span className="ruleline__to mono ruleline__to--stop">
                Do not propagate
              </span>
            </div>
          </Reveal>

          <Reveal delay={4} className="idea__aside">
            <p className="turn">
              No dictionary was provided.
              <br />
              So the catalogue <em>became</em> the dictionary.
            </p>
            <p className="note idea__note">
              Every module reads a vocabulary through one interface, and each table reports
              its own provenance. Ingesting the real list of values is a data swap, not a
              rewrite — and until then, no compliance claim is made against a file UniForge
              never had.
            </p>
            <div className="idea__zero">
              <span className="mono idea__zeroValue">{DISCOVERY.modelCalls}</span>
              <span className="metric__label">
                Model calls to discover the structure
              </span>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
