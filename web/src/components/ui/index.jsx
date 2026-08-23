import Icon from './Icon'
import { useCountUp, useInView } from '../../hooks/useInView'

/* ── SectionLabel ─────────────────────────────────────────────────────────── */
export function SectionLabel({ children, muted = false, as: As = 'p' }) {
  return (
    <As className={`eyebrow${muted ? ' eyebrow--muted' : ''}`}>
      <span className="eyebrow__tick" aria-hidden="true" />
      {children}
    </As>
  )
}

/* ── Reveal ───────────────────────────────────────────────────────────────── */
export function Reveal({ children, delay = 0, as: As = 'div', className = '', ...rest }) {
  const [ref, inView] = useInView()
  return (
    <As
      ref={ref}
      data-d={delay || undefined}
      className={`reveal${inView ? ' is-in' : ''}${className ? ' ' + className : ''}`}
      {...rest}
    >
      {children}
    </As>
  )
}

/* ── Metric ───────────────────────────────────────────────────────────────── */
export function Metric({
  value,
  label,
  sub,
  countTo,
  decimals = 0,
  suffix = '',
  prefix = '',
  size = 'md',
  tone = 'default',
  align = 'left',
}) {
  const [ref, counted] = useCountUp(countTo ?? 0, { decimals })
  const shown =
    countTo != null
      ? `${prefix}${decimals ? counted.toFixed(decimals) : Math.round(counted).toLocaleString()}${suffix}`
      : value

  return (
    <div
      ref={countTo != null ? ref : undefined}
      className={`metric metric--${size} metric--${tone} metric--${align}`}
    >
      <span className="metric__value mono">{shown}</span>
      <span className="metric__label">{label}</span>
      {sub ? <span className="metric__sub">{sub}</span> : null}
    </div>
  )
}

/* ── Delta: a before → after pair, which is most of this story ────────────── */
export function Delta({ before, after, label, tone = 'default', note }) {
  return (
    <div className={`delta delta--${tone}`}>
      <div className="delta__row">
        <span className="delta__before mono">{before}</span>
        <Icon name="arrow" size={13} className="delta__arrow" />
        <span className="delta__after mono">{after}</span>
      </div>
      <span className="metric__label">{label}</span>
      {note ? <span className="metric__sub">{note}</span> : null}
    </div>
  )
}

/* ── StatusBadge ──────────────────────────────────────────────────────────── */
const STATUS_ICON = {
  verified: 'check',
  review: 'warning',
  abstain: 'minus',
}

export function StatusBadge({ tone = 'verified', children, icon = true }) {
  return (
    <span className={`badge badge--${tone}`}>
      {icon ? <Icon name={STATUS_ICON[tone] ?? 'check'} size={11} /> : null}
      {children}
    </span>
  )
}

/* ── DataCard: a real-looking record panel ───────────────────────────────── */
export function DataCard({ title, meta, children, tone = 'default', footer }) {
  return (
    <div className={`datacard datacard--${tone}`}>
      {(title || meta) && (
        <header className="datacard__head">
          <span className="datacard__title meta">{title}</span>
          {meta ? <span className="datacard__meta mono">{meta}</span> : null}
        </header>
      )}
      <div className="datacard__body">{children}</div>
      {footer ? <footer className="datacard__foot">{footer}</footer> : null}
    </div>
  )
}

/** One key/value line inside a DataCard. */
export function Field({ label, value, tone = 'default', mono = true }) {
  return (
    <div className={`field field--${tone}`}>
      <span className="field__key">{label}</span>
      <span className={`field__val${mono ? ' mono' : ''}`}>{value}</span>
    </div>
  )
}

/* ── Connector: the thin vertical line between stacked stages ─────────────── */
export function Connector({ label, height = 40, active = true }) {
  return (
    <div
      className={`connector${active ? ' is-active' : ''}`}
      style={{ '--h': `${height}px` }}
      aria-hidden="true"
    >
      <span className="connector__line" />
      {label ? <span className="connector__label meta">{label}</span> : null}
      <Icon name="arrowDown" size={12} className="connector__cap" />
    </div>
  )
}

export { Icon }
