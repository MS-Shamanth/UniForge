import { FOOTER_LINKS, GITHUB_URL } from '../data/content'
import Icon, { Wordmark } from './ui/Icon'

export default function Footer() {
  return (
    <footer className="foot">
      <div className="shell foot__inner">
        <div className="foot__brand">
          <div className="foot__mark">
            <Wordmark size={24} />
            <span className="foot__name">UniForge</span>
          </div>
          <p className="foot__blurb">AI-Powered Product Intelligence</p>
        </div>

        <nav className="foot__nav" aria-label="Footer">
          {FOOTER_LINKS.map((l) => (
            <a className="foot__link" href={l.href} key={l.href}>
              {l.label}
            </a>
          ))}
          <a
            className="foot__link"
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer noopener"
          >
            <Icon name="github" size={13} />
            GitHub
          </a>
        </nav>
      </div>

      <div className="shell foot__base">
        <span className="foot__tag mono">
          LLM extracts. Rules decide. Evidence proves.
        </span>
        <span className="foot__proto meta">Prototype — UniHack 2026</span>
      </div>
    </footer>
  )
}
