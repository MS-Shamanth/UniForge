/**
 * Walk every console tab, capture each, and report per-tab render time and errors.
 *
 *   node shotconsole.mjs [baseUrl]
 */
import { chromium } from 'playwright'
import { mkdirSync } from 'node:fs'

const BASE = process.argv[2] ?? 'http://127.0.0.1:8000'
const OUT = '../data/out/screens'
mkdirSync(OUT, { recursive: true })

const TABS = ['Overview', 'Records', 'Discovery', 'Sourcing gate', 'Review queue', 'Search']

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
const page = await ctx.newPage()

const errors = []
page.on('pageerror', (e) => errors.push(`pageerror: ${e.message}`))
page.on('console', (m) => {
  if (m.type() === 'error') errors.push(m.text())
})

const t0 = Date.now()
await page.goto(`${BASE}/console`, { waitUntil: 'networkidle' })
await page.waitForSelector('.cons__title', { timeout: 120000 })
console.log(`\nconsole first paint: ${Date.now() - t0} ms`)
console.log('-'.repeat(64))

let problems = 0
for (const tab of TABS) {
  const t = Date.now()
  await page.getByRole('button', { name: tab, exact: true }).click()
  await page.waitForTimeout(700)

  const info = await page.evaluate(() => ({
    title: document.querySelector('.cons__title')?.innerText ?? null,
    panels: document.querySelectorAll('.cpanel').length,
    rows: document.querySelectorAll('.ctable tbody tr').length,
    stats: document.querySelectorAll('.cstat').length,
    offline: Boolean(document.querySelector('.cons__stateIcon')),
    spinner: Boolean(document.querySelector('.cons__spinner')),
    // an unresolved template literal left in a className is a real bug
    literalBraces: document.body.innerHTML.includes('badge--{'),
  }))

  const bad = info.offline || info.spinner || !info.title || info.literalBraces
  if (bad) problems += 1
  console.log(
    `  ${bad ? 'FAIL' : 'ok  '} ${String(Date.now() - t).padStart(5)} ms  ` +
      `${tab.padEnd(14)} "${info.title}"  panels=${info.panels} rows=${info.rows} ` +
      `stats=${info.stats}` +
      (info.offline ? '  OFFLINE' : '') +
      (info.spinner ? '  STILL LOADING' : '') +
      (info.literalBraces ? '  UNRESOLVED CLASSNAME' : '')
  )

  await page.screenshot({
    path: `${OUT}/console-${tab.toLowerCase().replace(/\s+/g, '-')}.png`,
    fullPage: true,
  })
}

// exercise the gate form, which is the interaction the user reported on
await page.getByRole('button', { name: 'Sourcing gate', exact: true }).click()
await page.waitForTimeout(500)
await page.getByRole('button', { name: 'Classify' }).click()
await page.waitForTimeout(700)
const gate = await page.evaluate(() => {
  const el = document.querySelector('.gateverdict')
  const rows = [...document.querySelectorAll('.gatelist li')].map((li) =>
    li.innerText.replace(/\s+/g, ' ').trim()
  )
  return { verdict: el?.innerText.replace(/\s+/g, ' ').trim() ?? null, rows }
})
console.log('-'.repeat(64))
console.log(`  gate verdict: ${gate.verdict}`)
console.log('  gate lists:')
gate.rows.forEach((r) => console.log(`      ${r}`))

const dupes = gate.rows.filter(
  (r, i) => gate.rows.findIndex((x) => x.split(' ')[0] === r.split(' ')[0]) !== i
)
if (dupes.length) {
  console.log(`  FAIL duplicate domain rows: ${dupes.join(' | ')}`)
  problems += 1
} else {
  console.log('  ok   no duplicate domain rows')
}

console.log('-'.repeat(64))
console.log(`  console errors: ${errors.length}`)
errors.slice(0, 5).forEach((e) => console.log(`      ${e.slice(0, 150)}`))
if (errors.length) problems += 1

await browser.close()
console.log(problems === 0 ? '\nconsole clean' : `\n${problems} problem(s)`)
process.exit(problems === 0 ? 0 : 1)
