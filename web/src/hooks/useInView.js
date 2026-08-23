import { useEffect, useRef, useState } from 'react'

const reduced = () =>
  typeof window !== 'undefined' &&
  window.matchMedia('(prefers-reduced-motion: reduce)').matches

/**
 * Reveal-on-scroll. Fires once, then unobserves — nothing re-animates when the
 * reader scrolls back up, which is what makes repeated passes over a long page
 * feel calm rather than busy.
 */
export function useInView({ threshold = 0.16, rootMargin = '0px 0px -8% 0px' } = {}) {
  const ref = useRef(null)
  const [inView, setInView] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node) return
    if (reduced() || typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            setInView(true)
            io.unobserve(e.target)
          }
        })
      },
      { threshold, rootMargin }
    )
    io.observe(node)
    return () => io.disconnect()
  }, [threshold, rootMargin])

  return [ref, inView]
}

/** Count a number up when it enters the viewport. Skipped under reduced-motion. */
export function useCountUp(target, { duration = 1150, decimals = 0 } = {}) {
  const [ref, inView] = useInView({ threshold: 0.4 })
  const [value, setValue] = useState(() => (reduced() ? target : 0))

  useEffect(() => {
    if (!inView) return
    if (reduced()) {
      setValue(target)
      return
    }
    let raf = 0
    const start = performance.now()
    const tick = (now) => {
      const t = Math.min(1, (now - start) / duration)
      // ease-out cubic: fast arrival, gentle settle
      const eased = 1 - Math.pow(1 - t, 3)
      setValue(Number((target * eased).toFixed(decimals)))
      if (t < 1) raf = requestAnimationFrame(tick)
      else setValue(target)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [inView, target, duration, decimals])

  return [ref, value, inView]
}

/** Activate a list of nodes one after another once the group is in view. */
export function useSequence(count, { step = 220, threshold = 0.28 } = {}) {
  const [ref, inView] = useInView({ threshold })
  const [active, setActive] = useState(-1)

  useEffect(() => {
    if (!inView) return
    if (reduced()) {
      setActive(count - 1)
      return
    }
    let i = 0
    setActive(0)
    const id = setInterval(() => {
      i += 1
      if (i >= count) {
        clearInterval(id)
        return
      }
      setActive(i)
    }, step)
    return () => clearInterval(id)
  }, [inView, count, step])

  return [ref, active, inView]
}

export const prefersReducedMotion = reduced
