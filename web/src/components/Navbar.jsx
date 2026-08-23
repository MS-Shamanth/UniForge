import { useEffect, useState } from 'react'
import Icon, { Wordmark } from './ui/Icon'
import { GITHUB_URL, NAV_LINKS } from '../data/content'

export default function Navbar() {
  const [stuck, setStuck] = useState(false)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState('')

  useEffect(() => {
    const onScroll = () => setStuck(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // Which section is the reader in? Cheap and accurate enough for a nav highlight.
  useEffect(() => {
    const ids = NAV_LINKS.map((l) => l.href.slice(1))
    const io = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0]
        if (visible) setActive(visible.target.id)
      },
      { rootMargin: '-45% 0px -45% 0px', threshold: [0, 0.2, 0.6] }
    )
    ids.forEach((id) => {
      const el = document.getElementById(id)
      if (el) io.observe(el)
    })
    return () => io.disconnect()
  }, [])

  // Lock the page behind the mobile sheet, and let Escape close it.
  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : ''
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <>
      <header className={`nav${stuck ? ' is-stuck' : ''}`}>
        <nav className="shell nav__inner" aria-label="Primary">
          <a href="#top" className="nav__brand" aria-label="UniForge, back to top">
            <Wordmark size={26} />
            <span className="nav__name">UniForge</span>
          </a>

          <ul className="nav__links">
            {NAV_LINKS.map((l) => (
              <li key={l.href}>
                <a
                  className="nav__link"
                  href={l.href}
                  aria-current={active === l.href.slice(1) ? 'true' : undefined}
                >
                  {l.label}
                </a>
              </li>
            ))}
          </ul>

          <div className="nav__right">
            <a
              className="nav__icon"
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer noopener"
            >
              <Icon name="github" size={15} />
              GitHub
            </a>
            <a className="btn btn--primary nav__cta" href="/console">
              <span className="nav__ctaDot" aria-hidden="true" />
              Live Demo
            </a>
            <button
              type="button"
              className="nav__burger"
              aria-expanded={open}
              aria-controls="nav-sheet"
              aria-label={open ? 'Close menu' : 'Open menu'}
              onClick={() => setOpen((v) => !v)}
            >
              <Icon name={open ? 'close' : 'menu'} size={16} />
            </button>
          </div>
        </nav>
      </header>

      {open && (
        <div className="sheet" id="nav-sheet">
          {NAV_LINKS.map((l) => (
            <a
              key={l.href}
              className="sheet__link"
              href={l.href}
              onClick={() => setOpen(false)}
            >
              {l.label}
            </a>
          ))}
          <div className="sheet__foot">
            <a className="btn btn--primary" href="/console">
              <span className="nav__ctaDot" aria-hidden="true" />
              Open the Live Demo
            </a>
            <a
              className="btn btn--ghost"
              href={GITHUB_URL}
              target="_blank"
              rel="noreferrer noopener"
            >
              <Icon name="github" size={15} />
              GitHub
            </a>
            <p className="sheet__tag mono">LLM extracts. Rules decide. Evidence proves.</p>
          </div>
        </div>
      )}
    </>
  )
}
