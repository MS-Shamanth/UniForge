/**
 * Where does page load time go? Navigation timings plus every request, slowest first.
 *
 *   node perf.mjs [baseUrl] [path]
 */
import { chromium } from 'playwright'

const BASE = process.argv[2] ?? 'http://127.0.0.1:8000'
const PATH = process.argv[3] ?? '/console'

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await ctx.newPage()

const reqs = new Map()
page.on('request', (r) => reqs.set(r, Date.now()))
const done = []
page.on('requestfinished', (r) => {
  const started = reqs.get(r)
  if (started) done.push({ url: r.url(), ms: Date.now() - started, type: r.resourceType() })
})
page.on('requestfailed', (r) => {
  const started = reqs.get(r)
  done.push({
    url: r.url(),
    ms: started ? Date.now() - started : -1,
    type: r.resourceType(),
    failed: r.failure()?.errorText ?? 'failed',
  })
})

const t0 = Date.now()
await page.goto(BASE + PATH, { waitUntil: 'domcontentloaded' })
const domReady = Date.now() - t0
await page.waitForLoadState('networkidle').catch(() => {})
const idle = Date.now() - t0

const nav = await page.evaluate(() => {
  const n = performance.getEntriesByType('navigation')[0]
  const paint = performance.getEntriesByType('paint')
  return {
    ttfb: Math.round(n?.responseStart ?? 0),
    domContentLoaded: Math.round(n?.domContentLoadedEventEnd ?? 0),
    load: Math.round(n?.loadEventEnd ?? 0),
    firstPaint: Math.round(paint.find((p) => p.name === 'first-paint')?.startTime ?? 0),
    firstContentful: Math.round(
      paint.find((p) => p.name === 'first-contentful-paint')?.startTime ?? 0
    ),
  }
})

console.log(`\n${BASE}${PATH}`)
console.log('-'.repeat(72))
console.log(`  TTFB                    ${nav.ttfb} ms`)
console.log(`  first paint             ${nav.firstPaint} ms`)
console.log(`  first contentful paint  ${nav.firstContentful} ms`)
console.log(`  DOMContentLoaded        ${nav.domContentLoaded} ms  (wall ${domReady} ms)`)
console.log(`  load event              ${nav.load} ms`)
console.log(`  network idle            ${idle} ms  (wall)`)
console.log('-'.repeat(72))
console.log('  requests, slowest first:')
done
  .sort((a, b) => b.ms - a.ms)
  .slice(0, 14)
  .forEach((r) => {
    const short = r.url.replace(BASE, '').slice(0, 62)
    console.log(
      `    ${String(r.ms).padStart(6)} ms  ${r.type.padEnd(10)} ${short}` +
        (r.failed ? `   ${r.failed}` : '')
    )
  })

const external = done.filter((r) => !r.url.startsWith(BASE))
if (external.length) {
  console.log('-'.repeat(72))
  console.log('  external requests (these gate networkidle):')
  external.forEach((r) =>
    console.log(`    ${String(r.ms).padStart(6)} ms  ${r.url.slice(0, 68)}`)
  )
}

await browser.close()
