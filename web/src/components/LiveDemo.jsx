import { COMPLIANCE, INPUT } from '../data/metrics'
import { Icon, Reveal, SectionLabel } from './ui'

/**
 * The interruption in the middle of the page.
 *
 * Without it the site reads as a write-up about a project rather than the front door of a
 * working one. This states plainly that there is a real console behind the page, names
 * what is inside it, and gives it a target big enough to be unmissable on a first scroll.
 */
const PANELS = [
  {
    id: '01',
    title: 'Every record, with its evidence',
    body:
      'Open any of the compiled records and each attribute shows the rule that produced ' +
      'it and the exact characters that justify it. Click a locator and the source ' +
      'document opens with the span highlighted.',
    icon: 'document',
  },
  {
    id: '02',
    title: 'The sourcing gate, live',
    body:
      'Type any URL and watch it be classified before a request is made. Marketplace and ' +
      'distributor domains are refused without being contacted.',
    icon: 'shield',
  },
  {
    id: '03',
    title: 'Search, both catalogues',
    body:
      'Run the same trade query against the raw rows and the compiled records, side by ' +
      'side, with the same scorer and the same k.',
    icon: 'search',
  },
  {
    id: '04',
    title: 'A review queue that applies',
    body:
      'Name an induced attribute once and the console recompiles and reports how many ' +
      'records that single decision unblocked. Nothing is simulated.',
    icon: 'layers',
  },
]

export default function LiveDemo() {
  return (
    <section className="section demo" id="demo">
      <div className="demo__glow" aria-hidden="true" />
      <div className="shell demo__inner">
        <div className="demo__lead">
          <Reveal>
            <SectionLabel>This is not a write-up</SectionLabel>
          </Reveal>

          <Reveal delay={1} as="h2" className="h-display demo__head">
            There is a working
            <br />
            <span className="accent">console</span> behind this page.
          </Reveal>

          <Reveal delay={2} as="p" className="lede demo__lede">
            Everything on this page is measured by a pipeline you can run. The console
            reads a live compile — {INPUT.rawRows.toLocaleString()} rows through nine
            stages, {COMPLIANCE.selfChecksTotal} self-checks, zero model calls — and it has
            no offline fixtures, so if it renders, it ran.
          </Reveal>

          <Reveal delay={3} className="demo__actions">
            <a className="btn btn--primary demo__cta" href="/console">
              <span className="demo__ctaPulse" aria-hidden="true" />
              Open the live console
              <Icon name="arrow" size={16} className="btn__arrow" />
            </a>
            <a className="btn btn--ghost demo__ctaAlt" href="#evidence">
              Read the evidence model first
            </a>
          </Reveal>

          <Reveal delay={4} className="demo__meta">
            <span className="pill">
              <span className="pill__dot" aria-hidden="true" />
              Compiles on load
            </span>
            <span className="pill">
              <span className="pill__dot" aria-hidden="true" />
              Upload your own catalogue
            </span>
            <span className="pill">
              <span className="pill__dot" aria-hidden="true" />
              Download the 252-column file
            </span>
          </Reveal>
        </div>

        <Reveal delay={3} className="demo__panels">
          {PANELS.map((p) => (
            <a className="demopanel" href="/console" key={p.id}>
              <span className="demopanel__icon">
                <Icon name={p.icon} size={15} />
              </span>
              <span className="demopanel__id mono">{p.id}</span>
              <h3 className="demopanel__title">{p.title}</h3>
              <p className="demopanel__body">{p.body}</p>
              <span className="demopanel__go">
                Open <Icon name="arrow" size={12} />
              </span>
            </a>
          ))}
        </Reveal>
      </div>
    </section>
  )
}
