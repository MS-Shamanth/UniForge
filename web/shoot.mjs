/**
 * Render the page in a real browser and capture it, plus any console errors.
 *
 * A build that compiles is not a page that renders. This catches the failures a bundler
 * cannot see: a component that throws on mount, an IntersectionObserver that never
 * fires so everything stays at opacity 0, an overflowing grid.
 *
 *   node tools/shoot.mjs [baseUrl]
 */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const BASE = process.argv[2] ?? 'http://127.0.0.1:8000'
const OUT = '../data/out/screens'
mkdirSync(OUT, { recursive: true })

const VIEWPORTS = [
  { name: 'desktop', width: 1440, height: 960 },
  { name: 'tablet', width: 834, height: 1100 },
  { name: 'mobile', width: 390, height: 844 },
]

const browser = await chromium.launch()
let problems = 0

for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    deviceScaleFactor: 1,
  })
  const page = await ctx.newPage()

  const errors = []
  page.on('console', (m) => {
    if (m.type() === 'error') errors.push(m.text())
  })
  page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))

  await page.goto(BASE, { waitUntil: 'networkidle' })

  // Scroll the whole page so every IntersectionObserver fires.
  //
  // Pace matters. Stepping faster than a frame or two lets the browser coalesce
  // observer callbacks, and reading opacity before the longest transition-delay (0.56s)
  // has elapsed reports elements as stuck when they are merely settling. Both produce
  // false failures, so: half-viewport steps, 220ms apart, then a settle pause.
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.5
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y)
      await new Promise((r) => setTimeout(r, 220))
    }
    await new Promise((r) => setTimeout(r, 1400))
    window.scrollTo(0, 0)
    await new Promise((r) => setTimeout(r, 300))
  })

  const audit = await page.evaluate(() => {
    const de = document.documentElement

    // An element wider than the viewport only matters if nothing clips it. A decorative
    // radial glow inside `overflow: hidden` is intentional, not a layout bug.
    const clippedByAncestor = (el) => {
      let p = el.parentElement
      while (p) {
        const o = getComputedStyle(p)
        if (o.overflowX === 'hidden' || o.overflow === 'hidden') return true
        p = p.parentElement
      }
      return false
    }
    const wide = [...document.querySelectorAll('*')]
      .filter(
        (el) =>
          el.getBoundingClientRect().width > de.clientWidth + 2 &&
          !clippedByAncestor(el)
      )
      .slice(0, 6)
      .map((el) => `${el.tagName.toLowerCase()}.${el.className?.toString().slice(0, 40)}`)

    // A reveal is stuck only if it never received .is-in. Opacity alone is ambiguous.
    const stuck = [...document.querySelectorAll('.reveal')].filter(
      (el) => !el.classList.contains('is-in')
    ).length

    const ids = [...document.querySelectorAll('[id]')].map((e) => e.id)
    const anchors = [...document.querySelectorAll('a[href^="#"]')]
      .map((a) => a.getAttribute('href').slice(1))
      .filter((h) => h && h !== 'top')
    const broken = [...new Set(anchors.filter((h) => !ids.includes(h)))]

    return {
      scrollWidth: de.scrollWidth,
      clientWidth: de.clientWidth,
      overflow: de.scrollWidth > de.clientWidth + 2,
      wide,
      stuck,
      revealTotal: document.querySelectorAll('.reveal').length,
      broken,
      sections: document.querySelectorAll('section').length,
      h1: document.querySelector('h1')?.innerText?.replace(/\n/g, ' ') ?? null,
    }
  })

  console.log(`\n[${vp.name}] ${vp.width}x${vp.height}`)
  console.log(`  sections rendered   ${audit.sections}`)
  console.log(`  h1                  ${audit.h1}`)
  console.log(
    `  horizontal overflow ${audit.overflow ? 'YES' : 'no'}  ` +
      `(scroll ${audit.scrollWidth} vs client ${audit.clientWidth})`
  )
  if (audit.wide.length) console.log(`  too wide            ${audit.wide.join(', ')}`)
  console.log(`  reveals stuck at 0  ${audit.stuck} of ${audit.revealTotal}`)
  if (audit.broken.length) console.log(`  broken anchors      ${audit.broken.join(', ')}`)
  console.log(`  console errors      ${errors.length}`)
  errors.slice(0, 5).forEach((e) => console.log(`      ${e.slice(0, 160)}`))

  if (audit.overflow || audit.stuck > 0 || audit.broken.length || errors.length) {
    problems += 1
  }

  // Viewport shot first, and re-pin the scroll each time: a full-page capture moves the
  // scroll position, so taking the viewport shot afterwards photographs empty space.
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(450)
  await page.screenshot({ path: `${OUT}/hero-${vp.name}.png`, fullPage: false })

  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(250)
  await page.screenshot({ path: `${OUT}/landing-${vp.name}.png`, fullPage: true })
  await ctx.close()
}

// the console, which needs the API up
{
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 960 } })
  const page = await ctx.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto(`${BASE}/console`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const title = await page.evaluate(
    () => document.querySelector('.cons__title')?.innerText ?? null
  )
  const stats = await page.evaluate(
    () => document.querySelectorAll('.cstat').length
  )
  console.log(`\n[console] title=${title} stats=${stats} errors=${errors.length}`)
  errors.slice(0, 4).forEach((e) => console.log(`      ${e.slice(0, 160)}`))
  if (!title || errors.length) problems += 1
  await page.screenshot({ path: `${OUT}/console.png`, fullPage: true })
  await ctx.close()
}

await browser.close()
console.log(`\n${problems === 0 ? 'clean' : problems + ' viewport(s) with problems'}`)
process.exit(problems === 0 ? 0 : 1)
