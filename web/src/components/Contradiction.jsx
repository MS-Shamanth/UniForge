import { CONTRADICTION } from '../data/content'
import { ENTITY } from '../data/metrics'
import { Field, Icon, Reveal, SectionLabel, StatusBadge } from './ui'

/**
 * Section 09. Amber appears here and almost nowhere else. The point is not that
 * UniForge found an error — it is that it refused to resolve one silently.
 */
export default function Contradiction() {
  return (
    <section className="section section--tight contra">
      <div className="shell">
        <div className="section__head">
          <Reveal>
            <SectionLabel>Contradiction detection</SectionLabel>
          </Reveal>
          <Reveal delay={1} as="h2" className="h-section">
            What happens when the data disagrees?
          </Reveal>
        </div>

        <div className="split split--even contra__body">
          <Reveal delay={2}>
            <div className="datacard datacard--muted">
              <header className="datacard__head">
                <span className="datacard__title meta">Reference record, as supplied</span>
                <span className="datacard__meta mono">row 1</span>
              </header>
              <div className="datacard__body">
                <Field
                  label="Manufacturer"
                  value={CONTRADICTION.manufacturer}
                  tone="strong"
                />
                <Field label="Brand" value={CONTRADICTION.brand} tone="strong" />
                <Field label="Mobile desc" value={CONTRADICTION.mobileDesc} tone="dim" />
              </div>
              <footer className="datacard__foot">
                The error has already propagated into the generated description.
              </footer>
            </div>
          </Reveal>

          <Reveal delay={3} className="contra__verdict">
            <div className="contra__flag">
              <Icon name="warning" size={15} />
              <span className="meta">Contradiction detected</span>
            </div>

            <p className="contra__reason">{CONTRADICTION.reasoning}</p>
            <p className="contra__cannot">{CONTRADICTION.verdict}</p>

            <div className="contra__outcome">
              <div className="contra__conf">
                <span className="contra__confValue mono">
                  {ENTITY.contradictionConfidence}%
                </span>
                <span className="metric__label">Confidence</span>
              </div>
              <div className="contra__status">
                <StatusBadge tone="review">Human review required</StatusBadge>
                <p className="note note--amber">
                  UniForge does not overwrite a sourced value.
                </p>
              </div>
            </div>

            <ul className="contra__points">
              <li>
                The same code path found{' '}
                <span className="mono">{ENTITY.contradictionsFound}</span> contradictions
                across the supplied rows — precision, not volume.
              </li>
              <li>
                <span className="mono">{ENTITY.manufacturersUnmasked}</span> manufacturers
                were unmasked from behind distributors and buying co-ops, because the
                manufacturer field names whoever invoiced the goods.
              </li>
            </ul>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
