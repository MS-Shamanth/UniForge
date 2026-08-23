import { useEffect, useState } from 'react'

import Navbar from './components/Navbar'
import Hero from './components/Hero'
import Problem from './components/Problem'
import Methodology from './components/Methodology'
import Architecture from './components/Architecture'
import LearningEngine from './components/LearningEngine'
import Enrichment from './components/Enrichment'
import Evidence from './components/Evidence'
import TrustBoundary from './components/TrustBoundary'
import Contradiction from './components/Contradiction'
import HumanLoop from './components/HumanLoop'
import Results from './components/Results'
import FinalCTA from './components/FinalCTA'
import Footer from './components/Footer'
import Console from './console/Console'

/**
 * Two views, one bundle.
 *
 * `/` is the landing page. `/console` is the working prototype, which reads a real
 * compile through the API. Keeping them in one app means the demo link on the page is
 * the demo, not a screenshot of one.
 */
function usePath() {
  const [path, setPath] = useState(() => window.location.pathname)

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname)
    window.addEventListener('popstate', onPop)

    // Intercept in-app links so navigation does not reload the bundle.
    const onClick = (e) => {
      const a = e.target.closest?.('a')
      if (!a) return
      const href = a.getAttribute('href')
      if (!href || !href.startsWith('/') || a.target === '_blank') return
      e.preventDefault()
      if (href !== window.location.pathname) {
        window.history.pushState({}, '', href)
        setPath(href)
        window.scrollTo(0, 0)
      }
    }
    document.addEventListener('click', onClick)
    return () => {
      window.removeEventListener('popstate', onPop)
      document.removeEventListener('click', onClick)
    }
  }, [])

  return path
}

function Landing() {
  return (
    <>
      <a className="skip-link" href="#product">
        Skip to content
      </a>
      <Navbar />
      <main>
        <Hero />
        <hr className="rule rule--shell" />
        <Problem />
        <Methodology />
        <hr className="rule rule--shell" />
        <Architecture />
        <LearningEngine />
        <hr className="rule rule--shell" />
        <Enrichment />
        <Evidence />
        <TrustBoundary />
        <Contradiction />
        <HumanLoop />
        <hr className="rule rule--shell" />
        <Results />
        <FinalCTA />
      </main>
      <Footer />
    </>
  )
}

export default function App() {
  const path = usePath()
  if (path.replace(/\/+$/, '') === '/console') return <Console />
  return <Landing />
}
