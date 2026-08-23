import { AUTHORS, EVENT, TAGLINE } from '../data/metrics'
import { GITHUB_URL } from '../data/content'
import { Icon, Reveal } from './ui'

/**
 * Section 12. A closing statement rather than a sales pitch, and the credit line.
 */
export default function FinalCTA() {
  return (
    <section className="section cta">
      <div className="shell cta__inner">
        <div className="cta__left">
          <Reveal as="h2" className="h-display cta__head">
            Better data.
            <br />
            <span className="accent">Smarter decisions.</span>
          </Reveal>

          <Reveal delay={1} className="cta__tag">
            {TAGLINE.split('. ')
              .filter(Boolean)
              .map((line, i) => (
                <span className="cta__tagLine" key={i}>
                  {line.endsWith('.') ? line : `${line}.`}
                </span>
              ))}
          </Reveal>

          <Reveal delay={2} className="cta__actions">
            <a className="btn btn--primary" href="#how-it-works">
              View the Pipeline
              <Icon name="arrow" size={14} className="btn__arrow" />
            </a>
            <a
              className="btn btn--ghost"
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer noopener"
            >
              Explore the Project
            </a>
          </Reveal>
        </div>

        <Reveal delay={2} className="cta__mark">
          <div className="rings" aria-hidden="true">
            <span className="rings__r rings__r--1" />
            <span className="rings__r rings__r--2" />
            <span className="rings__r rings__r--3" />
            <svg className="rings__u" viewBox="0 0 64 64" fill="none">
              <path
                d="M20 16v18a12 12 0 0 0 24 0V16"
                stroke="var(--magenta)"
                strokeWidth="3"
                strokeLinecap="square"
              />
              <circle cx="32" cy="47" r="2.4" fill="var(--magenta)" />
            </svg>
          </div>
        </Reveal>
      </div>

      <div className="shell">
        <Reveal delay={3} className="cta__credit">
          <div className="cta__authors">
            {AUTHORS.map((a) => (
              <span className="cta__author" key={a}>
                {a}
              </span>
            ))}
          </div>
          <div className="cta__event">
            <span className="cta__eventName">{EVENT.name}</span>
            <span className="cta__eventChallenge">{EVENT.challenge}</span>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
