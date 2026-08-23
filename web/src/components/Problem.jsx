import { RAW_RECORD } from '../data/content'
import { INPUT } from '../data/metrics'
import { Field, Metric, Reveal, SectionLabel } from './ui'

/**
 * Section 02. The spreadsheet row on the left looks populated. Three of its six cells
 * are placeholders. Showing it beats describing it.
 */
export default function Problem() {
  return (
    <section className="section" id="product">
      <div className="shell">
        <div className="section__head">
          <Reveal>
            <SectionLabel>The input is broken</SectionLabel>
          </Reveal>
          <Reveal delay={1} as="h2" className="h-section">
            Industrial product data arrives looking complete.
            <br />
            <span className="dim">It isn&rsquo;t.</span>
          </Reveal>
        </div>

        <div className="split problem__body">
          <Reveal delay={2}>
            <div className="datacard">
              <header className="datacard__head">
                <span className="datacard__title meta">Raw supplier record</span>
                <span className="datacard__meta mono">
                  {INPUT.rawColumns} columns
                </span>
              </header>
              <div className="datacard__body">
                {RAW_RECORD.map((f) => (
                  <Field
                    key={f.label}
                    label={f.label}
                    value={f.value}
                    tone={f.tone}
                  />
                ))}
              </div>
              <footer className="datacard__foot">
                Three of six cells carry no information. A placeholder is not data.
              </footer>
            </div>
          </Reveal>

          <Reveal delay={3} className="problem__stats">
            <div className="problem__stat">
              <Metric
                size="xl"
                tone="accent"
                countTo={INPUT.placeholderBrandPct}
                decimals={1}
                suffix="%"
                label="Brand cells were placeholders"
              />
            </div>
            <div className="problem__stat">
              <Metric
                size="lg"
                countTo={INPUT.meanDescriptionChars}
                label="Average description characters"
              />
            </div>
            <div className="problem__stat">
              <Metric
                size="lg"
                countTo={INPUT.deliveryHeaders}
                label="Headers to interpret"
              />
            </div>
          </Reveal>
        </div>

        {/* the transformation line */}
        <Reveal delay={4} className="transform">
          <span className="transform__end meta">Raw data</span>
          <span className="transform__line" aria-hidden="true">
            <span className="transform__pulse" />
          </span>
          <span className="transform__end transform__end--to meta">
            Structured intelligence
          </span>
        </Reveal>
      </div>
    </section>
  )
}
