/** Capture one section by id, for eyeballing a single composition.
 *
 *   node shotsection.mjs demo            -> ../data/out/screens/section-demo.png
 *   node shotsection.mjs demo 390        -> at a mobile width
 */
import { chromium } from 'playwright'

const id = process.argv[2] ?? 'demo'
const width = Number(process.argv[3] ?? 1440)
const BASE = process.argv[4] ?? 'http://127.0.0.1:8000'

const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width, height: 1000 } })
await page.goto(BASE, { waitUntil: 'networkidle' })

await page.evaluate(async (target) => {
  const el = document.getElementById(target)
  if (el) el.scrollIntoView({ block: 'center' })
  await new Promise((r) => setTimeout(r, 1600))
}, id)

const el = await page.$(`#${id}`)
if (!el) {
  console.log(`no #${id} on the page`)
} else {
  const out = `../data/out/screens/section-${id}-${width}.png`
  await el.screenshot({ path: out })
  const box = await el.boundingBox()
  console.log(`wrote ${out}  ${Math.round(box.width)}x${Math.round(box.height)}`)
}
await browser.close()
