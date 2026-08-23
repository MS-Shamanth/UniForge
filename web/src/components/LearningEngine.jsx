import { useInView } from '../hooks/useInView'
import { COOCCURRENCE, FAMILY_ROWS, FAMILY_SUFFIX } from '../data/content'
import { DISCOVERY } from '../data/metrics'
import { Icon, Metric, Reveal, SectionLabel, StatusBadge } from './ui'

/**
 * Section 05. Six rows differing in exactly one token. The varying token is the
 * attribute. This is the section that shows the method rather than asserting it.
 */
export default function LearningEngine() {
  const [ref, inView] = useInView({ threshold: 0.22 })

  return (
    <section className="section learn" id="technology">
      <div className="shell">
        <div className="section__head">
          <Reveal>
            <SectionLabel>The learning engine</SectionLabel>
          </Reveal>
          <Reveal delay={1} as="h2" className="h-section">
            Learning Attributes Without Definitions
          </Reveal>
          <Reveal delay={2} as="p" className="lede">
            Nothing in the supplied data says that abrasives have a grit. Six part numbers
            that differ in exactly one position do.
          </Reveal>
        </div>

        <div className="learn__body" ref={ref}>
          <Reveal delay={2} className="learn__rows">
            <div className="panel">
              <div className="panel__head">
                <span className="meta">One family · six members</span>
                <span className="meta mono">fam · 3M 775L</span>
              </div>
              <div className="codeblock learn__code">
                {FAMILY_ROWS.map((r, i) => (
                  <div
                    className={`codeblock__row learn__row${inView ? ' is-in' : ''}`}
                    key={r.pn}
                    style={{ transitionDelay: `${i * 70}ms` }}
                  >
                    <span className="codeblock__pn">{r.pn}</span>
                    <span className="codeblock__txt">
                      <span className="tok--hold">{r.pre}</span>
                      <span className="tok--vary">{r.axis}</span>
                      <span className="tok--hold">
                        {r.post}
                        {FAMILY_SUFFIX}
                      </span>
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="learn__derive">
              <div className="learn__deriveArrow" aria-hidden="true">
                <span className="learn__deriveLine" />
                <Icon name="arrowDown" size={13} />
              </div>
              <div className="learn__deriveOut">
                <span className="meta">Variant axis</span>
                <span className="learn__deriveLabel mono">Grit</span>
                <StatusBadge tone="verified">Attribute induced</StatusBadge>
              </div>
            </div>

            <ul className="learn__rules">
              <li>
                Tokens that <strong>vary</strong> across siblings are variant axes — these
                are the attributes.
              </li>
              <li>
                Tokens that <strong>hold constant</strong> are invariant facts, safe to
                propagate to siblings.
              </li>
              <li className="learn__rules--guard">
                A variant axis is <strong>never</strong> propagated, so inference cannot
                amplify a guess.
              </li>
            </ul>
          </Reveal>

          {/* second engine: co-occurrence */}
          <Reveal delay={3} className="learn__cooc">
            <p className="meta learn__coocHead">
              The same idea, run on co-occurrence
            </p>
            <p className="note learn__coocNote">
              Values that never share a row are alternatives of one attribute. That alone
              recovered a real product structure from statistics — three collections across
              six colours, with nothing declaring either.
            </p>
            {COOCCURRENCE.map((group) => (
              <div className="coocgroup" key={group.label}>
                <div className="coocgroup__head">
                  <span className="coocgroup__label mono">{group.label}</span>
                  <StatusBadge tone={group.named ? 'verified' : 'review'}>
                    {group.named ? 'Named by rule' : 'Needs one name'}
                  </StatusBadge>
                </div>
                <div className="coocgroup__vals">
                  {group.values.map((v) => (
                    <span className="coocval" key={v}>
                      {v}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            <p className="note">
              <span className="mono">{DISCOVERY.categoricalAttributes}</span> categorical
              attributes induced.{' '}
              <span className="mono">{DISCOVERY.labelsNeedingOneName}</span> need one human
              name each — not one per row.
            </p>
          </Reveal>
        </div>

        <Reveal delay={4} className="statstrip statstrip--4 learn__stats">
          <Metric size="md" countTo={DISCOVERY.families} label="Families" />
          <Metric size="md" countTo={DISCOVERY.variantAxes} label="Variant axes" />
          <Metric size="md" countTo={DISCOVERY.inferredLabels} label="Inferred labels" />
          <Metric
            size="md"
            tone="accent"
            countTo={DISCOVERY.modelCalls}
            label="Model calls"
          />
        </Reveal>
      </div>
    </section>
  )
}
