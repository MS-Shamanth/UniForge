/**
 * Distinguish a real reveal bug from an audit artefact.
 *
 * `opacity === 0` is not enough to conclude anything: an element that has been given
 * `is-in` may simply be mid-transition, and delays on this page run to 0.56s. So this
 * reports the class state separately from the computed opacity, and only calls an element
 * broken when it never received the class at all.
 *
 * It also checks whether an element wider than the viewport is actually clipped by an
 * ancestor, because a decorative glow inside `overflow: hidden` is not an overflow bug.
 */
import { chromium } from 'playwright'

const BASE = process.argv[2] ?? 'http://127.0.0.1:8000'
const browser = await chromium.launch()

for (const vp of [
  { name: 'desktop', width: 1440, height: 960 },
  { name: 'mobile', width: 390, height: 844 },
]) {
  const ctx = await browser.newContext({ viewport: vp })
  const page = await ctx.newPage()
  await page.goto(BASE, { waitUntil: 'networkidle' })

  // Scroll slowly enough that IntersectionObserver is not coalesced, then let the
  // longest transition-delay finish before reading anything.
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.5
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      window.scrollTo(0, y)
      await new Promise((r) => setTimeout(r, 220))
    }
    await new Promise((r) => setTimeout(r, 1400))
    window.scrollTo(0, 0)
    await new Promise((r) => setTimeout(r, 400))
  })

  const r = await page.evaluate(() => {
    const reveals = [...document.querySelectorAll('.reveal')]
    const noClass = reveals.filter((el) => !el.classList.contains('is-in'))
    const zeroWithClass = reveals.filter(
      (el) => el.classList.contains('is-in') && getComputedStyle(el).opacity === '0'
    )

    const de = document.documentElement
    const wide = [...document.querySelectorAll('*')]
      .filter((el) => el.getBoundingClientRect().width > de.clientWidth + 2)
      .map((el) => {
        // is anything above it clipping the overflow?
        let p = el.parentElement
        let clipped = false
        while (p) {
          const o = getComputedStyle(p)
          if (o.overflowX === 'hidden' || o.overflow === 'hidden') {
            clipped = true
            break
          }
          p = p.parentElement
        }
        return {
          sel: `${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]}`,
          w: Math.round(el.getBoundingClientRect().width),
          clipped,
        }
      })

    return {
      total: reveals.length,
      noClass: noClass.length,
      noClassSel: noClass.slice(0, 8).map((el) => {
        const r = el.getBoundingClientRect()
        const cls = String(el.className).replace('reveal', '').replace('is-in', '').trim()
        const section = el.closest('section')?.id || el.closest('section')?.className || '?'
        return `<${el.tagName.toLowerCase()} class="${cls || '(bare)'}"> in [${section}] ` +
          `size=${Math.round(r.width)}x${Math.round(r.height)} top=${Math.round(r.top)}`
      }),
      zeroWithClass: zeroWithClass.length,
      wide,
      docScroll: de.scrollWidth,
      docClient: de.clientWidth,
    }
  })

  console.log(`\n[${vp.name}]`)
  console.log(`  reveal elements                 ${r.total}`)
  console.log(`  never given .is-in  (REAL BUG)  ${r.noClass}`)
  if (r.noClass) console.log(`      ${r.noClassSel.join(', ')}`)
  console.log(`  .is-in but opacity 0 (settling) ${r.zeroWithClass}`)
  console.log(`  document overflow               ${r.docScroll > r.docClient + 2 ? 'YES' : 'no'} (${r.docScroll} vs ${r.docClient})`)
  for (const w of r.wide) {
    console.log(
      `  wider than viewport: ${w.sel} = ${w.w}px  ${w.clipped ? '(clipped by an ancestor — harmless)' : '*** NOT CLIPPED ***'}`
    )
  }
  await ctx.close()
}

await browser.close()
