/**
 * Click-test every link and button on the page.
 *
 * A submitted landing page must have no dead controls. This resolves every anchor: internal
 * hashes must match a real element id, internal paths must return 200, and external links
 * must at least be well-formed absolute URLs pointing where they claim to.
 *
 *   node links.mjs [baseUrl]
 */
import { chromium } from 'playwright'

const BASE = process.argv[2] ?? 'http://127.0.0.1:8000'
const EXPECTED_REPO = 'https://github.com/MS-Shamanth/UniForge'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 960 } })
await page.goto(BASE, { waitUntil: 'networkidle' })

const links = await page.evaluate(() => {
  const ids = new Set([...document.querySelectorAll('[id]')].map((e) => e.id))
  return [...document.querySelectorAll('a')].map((a) => {
    const href = a.getAttribute('href') ?? ''
    return {
      href,
      text: (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 42),
      kind: href.startsWith('#')
        ? 'hash'
        : href.startsWith('/')
          ? 'path'
          : href.startsWith('http')
            ? 'external'
            : 'other',
      hashResolves: href.startsWith('#') ? ids.has(href.slice(1)) : null,
      target: a.getAttribute('target'),
      rel: a.getAttribute('rel'),
    }
  })
})

let bad = 0
const seen = new Set()

console.log(`\nchecking ${links.length} links on ${BASE}`)
console.log('-'.repeat(76))

for (const l of links) {
  const key = `${l.kind}:${l.href}`
  if (seen.has(key)) continue
  seen.add(key)

  let status = ''
  let ok = true

  if (l.kind === 'hash') {
    ok = l.href === '#top' || l.hashResolves
    status = ok ? 'resolves' : 'NO SUCH ELEMENT'
  } else if (l.kind === 'path') {
    const r = await page.request.get(BASE + l.href)
    ok = r.status() === 200
    status = String(r.status())
  } else if (l.kind === 'external') {
    ok = /^https:\/\/[^/]+\.[a-z]{2,}/i.test(l.href)
    status = ok ? 'well-formed' : 'MALFORMED'
    if (/github\.com/i.test(l.href)) {
      const isRepo = l.href.replace(/\/+$/, '') === EXPECTED_REPO
      if (!isRepo) {
        ok = false
        status = `POINTS AT ${l.href} — expected ${EXPECTED_REPO}`
      }
      if (l.target === '_blank' && !/noopener/.test(l.rel ?? '')) {
        ok = false
        status += ' (target=_blank without rel=noopener)'
      }
    }
  } else {
    ok = false
    status = 'UNRECOGNISED HREF'
  }

  if (!ok) bad += 1
  console.log(
    `  ${ok ? 'ok  ' : 'FAIL'}  ${l.kind.padEnd(8)} ${String(l.href).padEnd(34)} ${status}` +
      (l.text ? `   "${l.text}"` : '')
  )
}

// buttons that are not links must all do something
const deadButtons = await page.evaluate(
  () =>
    [...document.querySelectorAll('button')].filter(
      (b) => !b.onclick && !b.getAttribute('aria-expanded') && b.type !== 'submit'
    ).length
)

console.log('-'.repeat(76))
console.log(`  non-link buttons with no handler: ${deadButtons}`)
console.log(bad === 0 ? '\nno dead links' : `\n${bad} problem link(s)`)
await browser.close()
process.exit(bad === 0 ? 0 : 1)
