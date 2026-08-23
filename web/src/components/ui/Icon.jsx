/**
 * Inline SVG icons — thin, technical, currentColor. No icon package.
 * Every icon is decorative unless given a title, in which case it is labelled.
 */
const BASE = {
  width: 16,
  height: 16,
  viewBox: '0 0 16 16',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.25,
  strokeLinecap: 'square',
  strokeLinejoin: 'miter',
}

const PATHS = {
  arrow: <path d="M2.5 8h11M9.5 4l4 4-4 4" />,
  arrowDown: <path d="M8 2.5v11M4 9.5l4 4 4-4" />,
  check: <path d="M2.75 8.5l3.5 3.5 7-9" />,
  warning: (
    <>
      <path d="M8 2L14.5 13.5h-13L8 2z" />
      <path d="M8 6.5v3.25M8 11.5v.6" />
    </>
  ),
  document: (
    <>
      <path d="M3.5 1.5h6l3 3v10h-9v-13z" />
      <path d="M9.5 1.5v3h3M5.5 8h5M5.5 10.5h5" />
    </>
  ),
  database: (
    <>
      <ellipse cx="8" cy="3.5" rx="5" ry="2" />
      <path d="M3 3.5v9c0 1.1 2.24 2 5 2s5-.9 5-2v-9" />
      <path d="M3 8c0 1.1 2.24 2 5 2s5-.9 5-2" />
    </>
  ),
  shield: (
    <>
      <path d="M8 1.5l5 2v4.5c0 3.2-2.1 5.4-5 6.5-2.9-1.1-5-3.3-5-6.5V3.5l5-2z" />
      <path d="M5.75 7.75l1.75 1.75 3-3.25" />
    </>
  ),
  layers: (
    <>
      <path d="M8 1.5l6 3-6 3-6-3 6-3z" />
      <path d="M2 8l6 3 6-3M2 11.5l6 3 6-3" />
    </>
  ),
  graph: (
    <>
      <path d="M2 14V2M2 14h12" />
      <path d="M4.5 11l3-3.5 2.5 2L14 4.5" />
    </>
  ),
  search: (
    <>
      <circle cx="7" cy="7" r="4.5" />
      <path d="M10.5 10.5L14 14" />
    </>
  ),
  node: (
    <>
      <circle cx="8" cy="8" r="2.25" />
      <path d="M8 1.5v4.25M8 10.25v4.25M1.5 8h4.25M10.25 8h4.25" />
    </>
  ),
  slash: <path d="M10.5 2L5.5 14" />,
  minus: <path d="M3 8h10" />,
  github: (
    <path
      d="M8 1.2C4.2 1.2 1.2 4.2 1.2 8c0 3 1.95 5.55 4.65 6.45.35.05.45-.15.45-.35v-1.2c-1.9.4-2.3-.9-2.3-.9-.3-.8-.75-1-.75-1-.6-.4.05-.4.05-.4.7.05 1.05.7 1.05.7.6 1.05 1.6.75 2 .55.05-.45.25-.75.45-.9-1.5-.15-3.1-.75-3.1-3.35 0-.75.25-1.35.7-1.8-.05-.2-.3-.9.05-1.85 0 0 .55-.2 1.85.7A5.2 5.2 0 0 1 8 4.5c.65 0 1.3.1 1.85.25 1.3-.9 1.85-.7 1.85-.7.35.95.1 1.65.05 1.85.45.45.7 1.05.7 1.8 0 2.6-1.6 3.2-3.1 3.35.25.2.45.65.45 1.3v1.9c0 .2.1.4.45.35A6.82 6.82 0 0 0 14.8 8c0-3.8-3-6.8-6.8-6.8z"
      fill="currentColor"
      stroke="none"
    />
  ),
  menu: <path d="M2 4h12M2 8h12M2 12h12" />,
  close: <path d="M3.5 3.5l9 9M12.5 3.5l-9 9" />,
}

export default function Icon({ name, size = 16, title, className = '', ...rest }) {
  const path = PATHS[name]
  if (!path) return null
  const labelled = Boolean(title)
  return (
    <svg
      {...BASE}
      width={size}
      height={size}
      className={className}
      role={labelled ? 'img' : undefined}
      aria-hidden={labelled ? undefined : 'true'}
      focusable="false"
      {...rest}
    >
      {labelled ? <title>{title}</title> : null}
      {path}
    </svg>
  )
}

export function Wordmark({ size = 26 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      focusable="false"
    >
      <rect x="0.6" y="0.6" width="30.8" height="30.8" rx="7" stroke="var(--hair-strong)" />
      <path
        d="M11 9v8a5 5 0 0 0 10 0V9"
        stroke="var(--magenta)"
        strokeWidth="2.2"
        strokeLinecap="square"
      />
      <circle cx="16" cy="23.4" r="1.15" fill="var(--magenta)" />
    </svg>
  )
}
