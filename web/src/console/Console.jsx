import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Icon, { Wordmark } from '../components/ui/Icon'
import { StatusBadge } from '../components/ui'
import { api, num, pct } from './api'
import '../styles/console.css'

const TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'records', label: 'Records' },
  { id: 'discovery', label: 'Discovery' },
  { id: 'sourcing', label: 'Sourcing gate' },
  { id: 'review', label: 'Review queue' },
  { id: 'search', label: 'Search' },
]

export default function Console() {
  const [tab, setTab] = useState('overview')
  const [health, setHealth] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [progress, setProgress] = useState(null)

  /**
   * The server warms a run at startup, so this usually returns instantly. When it does
   * not — a cold boot, or a freshly uploaded catalogue — we poll /api/status instead of
   * sitting on a blocking /api/metrics request, so the page can say what it is waiting
   * for rather than looking hung.
   */
  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setProgress(null)
    try {
      const h = await api.health()
      setHealth(h)

      if (!h.run?.ready) {
        for (let i = 0; i < 240; i += 1) {
          const st = await api.status()
          setProgress(st)
          if (st.error) throw new Error(st.error)
          if (st.ready) break
          await new Promise((r) => setTimeout(r, 700))
        }
      }

      setMetrics(await api.metrics())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
      setProgress(null)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="cons">
      <header className="cons__bar">
        <a className="cons__brand" href="/">
          <Wordmark size={24} />
          <span className="cons__brandName">UniForge</span>
          <span className="cons__brandTag meta">Console</span>
        </a>

        <nav className="cons__tabs" aria-label="Console sections">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`cons__tab${tab === t.id ? ' is-on' : ''}`}
              aria-current={tab === t.id ? 'page' : undefined}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>

        <div className="cons__barRight">
          {metrics && (
            <span
              className={`cons__pipStatus${
                metrics.self_checks.all_pass ? ' is-ok' : ' is-bad'
              }`}
            >
              <Icon name={metrics.self_checks.all_pass ? 'check' : 'warning'} size={11} />
              {metrics.self_checks.passed}/{metrics.self_checks.total} checks
            </span>
          )}
          <a className="btn btn--ghost cons__back" href="/">
            Back to site
          </a>
        </div>
      </header>

      <main className="cons__main">
        {loading && <Loading progress={progress} />}
        {error && <Offline message={error} onRetry={load} />}
        {!loading && !error && metrics && (
          <>
            {tab === 'overview' && <Overview metrics={metrics} health={health} onReload={load} />}
            {tab === 'records' && <Records />}
            {tab === 'discovery' && <Discovery />}
            {tab === 'sourcing' && <Sourcing />}
            {tab === 'review' && <ReviewQueue onChanged={load} />}
            {tab === 'search' && <SearchLab />}
          </>
        )}
      </main>
    </div>
  )
}

/* ── shared bits ─────────────────────────────────────────────────────────── */
const STAGE_LABELS = {
  ingest: 'Reading the catalogue',
  families: 'Clustering families',
  induction: 'Inducing the vocabulary',
  entity: 'Resolving manufacturers',
  extract: 'Extracting attributes',
  propagate: 'Propagating between siblings',
  sourcing: 'Reading manufacturer documents',
  compose: 'Building descriptions',
  verify: 'Verifying and round-tripping',
  assemble: 'Assembling 252 columns',
  review: 'Grouping the review queue',
  search: 'Scoring search readiness',
}

function Loading({ label = 'Compiling the catalogue…', progress }) {
  const secs = progress?.building_for
  return (
    <div className="cons__state">
      <span className="cons__spinner" aria-hidden="true" />
      <p className="cons__stateText">{label}</p>
      {secs != null && (
        <p className="cons__stateElapsed mono">{secs.toFixed(1)}s elapsed</p>
      )}
      <p className="note cons__stateNote">
        Nine stages over {progress?.rows ? progress.rows.toLocaleString() : 'the whole'}{' '}
        catalogue, with zero model calls. Nothing here is cached from a previous session,
        and nothing is mocked — the console reads whatever the pipeline actually produced.
      </p>
      <ul className="cons__stages">
        {Object.entries(STAGE_LABELS).map(([k, v]) => (
          <li key={k}>{v}</li>
        ))}
      </ul>
    </div>
  )
}

/** Distinguish "the server is not running" from a genuine API error. */
function diagnose(message) {
  const m = String(message || '')
  if (/^0\b|Failed to fetch|NetworkError|Load failed/i.test(m)) {
    return {
      title: 'The compiler is not running.',
      why:
        'The browser could not reach the API at all. The Python server has to be up: ' +
        'the console reads a live run and has no offline fixtures, on purpose.',
      showCommand: true,
    }
  }
  if (/^404/.test(m)) {
    return {
      title: 'The compiler is not running.',
      why:
        'The request for /api reached a server, but not this one — a 404 here almost ' +
        'always means the Vite dev server answered because nothing was listening on ' +
        'port 8000 to proxy to.',
      showCommand: true,
    }
  }
  return {
    title: 'The compile failed.',
    why: 'The server is up, but the pipeline raised an error. The message is below.',
    showCommand: false,
  }
}

function Offline({ message, onRetry }) {
  const d = diagnose(message)
  return (
    <div className="cons__state">
      <span className="cons__stateIcon">
        <Icon name="warning" size={20} />
      </span>
      <p className="cons__stateText">{d.title}</p>
      <p className="note cons__stateNote">{d.why}</p>

      {d.showCommand && (
        <div className="cons__fix">
          <p className="meta">Start it, then retry</p>
          <code className="cons__code">python -m uniforge.cli serve</code>
          <p className="note">
            That serves the API and this console together on{' '}
            <span className="mono">http://127.0.0.1:8000</span>. If you are on the Vite
            dev server at port 5173, run the command above in a second terminal — Vite
            proxies <span className="mono">/api</span> to it.
          </p>
        </div>
      )}

      <p className="cons__stateErr mono">{message}</p>

      <div className="cons__stateActions">
        {onRetry && (
          <button type="button" className="btn btn--primary" onClick={onRetry}>
            Retry
          </button>
        )}
        <a className="btn btn--ghost" href="/">
          Back to the site
        </a>
      </div>
    </div>
  )
}

function Stat({ value, label, sub, tone = '' }) {
  return (
    <div className={`cstat${tone ? ' cstat--' + tone : ''}`}>
      <span className="cstat__value mono">{value}</span>
      <span className="cstat__label">{label}</span>
      {sub && <span className="cstat__sub mono">{sub}</span>}
    </div>
  )
}

function Panel({ title, meta, children, actions }) {
  return (
    <section className="cpanel">
      <header className="cpanel__head">
        <span className="meta">{title}</span>
        <div className="cpanel__headRight">
          {meta && <span className="cpanel__meta mono">{meta}</span>}
          {actions}
        </div>
      </header>
      <div className="cpanel__body">{children}</div>
    </section>
  )
}

/* ── Overview ────────────────────────────────────────────────────────────── */
function Overview({ metrics: m, health, onReload }) {
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const fileRef = useRef(null)

  const onUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    setMsg(null)
    try {
      const r = await api.upload(file)
      setMsg(
        `Compiled ${num(r.rows)} rows from ${r.file} in ${r.compile_seconds}s — ` +
          `${r.self_checks.passed}/${r.self_checks.total} self-checks passing.`
      )
      onReload()
    } catch (err) {
      setMsg(`Upload failed: ${err.message}`)
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const restore = async () => {
    setBusy(true)
    try {
      const r = await api.resetInput()
      setMsg(`Restored ${r.input} (${num(r.rows)} rows).`)
      onReload()
    } catch (err) {
      setMsg(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="cons__page">
      <div className="cons__pageHead">
        <div>
          <h1 className="cons__title">Run overview</h1>
          <p className="note">
            {m.input.source_file} · {num(m.input.row_count)} rows ·{' '}
            {m.meta.compile_seconds}s · {num(m.meta.rows_per_second)} rows/s ·{' '}
            {m.discovery.model_calls} model calls
          </p>
        </div>
        <div className="cons__pageActions">
          <input
            ref={fileRef}
            type="file"
            id="upload"
            accept=".xlsx,.xls,.csv"
            className="cons__file"
            onChange={onUpload}
            disabled={busy}
          />
          <label htmlFor="upload" className="btn btn--ghost">
            {busy ? 'Working…' : 'Compile a catalogue'}
          </label>
          <a className="btn btn--ghost" href={api.downloadUrl('xlsx')}>
            XLSX
          </a>
          <a className="btn btn--primary" href={api.downloadUrl('csv')}>
            Download CSV
          </a>
        </div>
      </div>

      {msg && (
        <p className="cons__flash">
          {msg}{' '}
          <button type="button" className="btn btn--quiet" onClick={restore}>
            restore the bundled catalogue
          </button>
        </p>
      )}

      <div className="cgrid cgrid--4">
        <Stat
          value={num(m.output.populated_cells_out)}
          label="Populated cells out"
          sub={`from ${num(m.output.populated_cells_in)} · ×${m.output.populated_cell_multiple}`}
          tone="accent"
        />
        <Stat
          value={pct(m.compliance.character_limit_compliance_pct, 2)}
          label="Character-limit compliance"
          sub={`${num(m.compliance.character_limit_checks)} checks`}
        />
        <Stat
          value={pct(m.compliance.approved_unit_compliance_pct, 2)}
          label="Approved-unit compliance"
          sub={`${num(m.compliance.approved_unit_checks)} checks`}
        />
        <Stat
          value={num(m.integrity.hallucinations)}
          label="Hallucinations"
          sub={`${num(m.integrity.numbers_traced_to_a_source)} numbers traced`}
          tone="accent"
        />
      </div>

      <div className="cons__two">
        <Panel
          title="What it learned from the catalogue"
          meta={`${m.discovery.model_calls} model calls`}
        >
          <dl className="klist">
            <KV k="Families" v={num(m.discovery.families)} />
            <KV k="Variant axes discovered" v={num(m.discovery.variant_axes_discovered)} />
            <KV k="Attribute labels induced" v={num(m.discovery.attribute_labels_induced)} />
            <KV
              k="Awaiting one human name"
              v={num(m.discovery.labels_awaiting_a_human_name)}
            />
            <KV
              k="Categorical attributes induced"
              v={num(m.discovery.categorical_attributes_induced)}
            />
            <KV
              k="Propagations blocked by the axis rule"
              v={num(m.discovery.propagations_blocked_by_the_axis_rule)}
              accent
            />
          </dl>
        </Panel>

        <Panel title="Refusing to guess" meta="abstentions">
          <dl className="klist">
            <KV
              k="Delivery cells left empty"
              v={num(m.abstention.delivery_cells_left_empty_for_want_of_a_source)}
            />
            <KV
              k="Mobile descriptions left short"
              v={num(m.abstention.mobile_descriptions_left_short)}
            />
            <KV
              k="Abbreviations left unexpanded"
              v={num(m.abstention.abbreviations_left_unexpanded)}
            />
            <KV k="Claims without a locator" v={num(m.integrity.claims_without_a_locator)} accent />
            <KV
              k="Document overruled inference"
              v={num(m.integrity.document_overruled_inference)}
              accent
            />
          </dl>
          <p className="note cpanel__note">{m.abstention.principle}</p>
        </Panel>
      </div>

      <Panel
        title="Vocabulary provenance"
        meta={m.vocabulary.any_supplied ? 'client files present' : 'derived only'}
      >
        <table className="ctable">
          <thead>
            <tr>
              <th>Table</th>
              <th>Provenance</th>
              <th className="ctable__num">Rows</th>
              <th>Note</th>
            </tr>
          </thead>
          <tbody>
            {m.vocabulary.tables.map((t) => (
              <tr key={t.name}>
                <td>{t.name}</td>
                <td>
                  <span className={`prov prov--${t.provenance}`}>{t.provenance}</span>
                </td>
                <td className="ctable__num mono">{num(t.rows)}</td>
                <td className="ctable__note">{t.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="note cpanel__note">{m.compliance.note}</p>
      </Panel>

      <Panel
        title="Self checks"
        meta={`${m.self_checks.passed}/${m.self_checks.total} passing`}
      >
        <ul className="checks">
          {m.self_checks.checks.map((c) => (
            <li key={c.check} className={c.pass ? 'is-pass' : 'is-fail'}>
              <Icon name={c.pass ? 'check' : 'warning'} size={12} />
              <span className="checks__what">{c.check}</span>
              <span className="checks__detail mono">{c.detail}</span>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  )
}

function KV({ k, v, accent }) {
  return (
    <div className="klist__row">
      <dt>{k}</dt>
      <dd className={`mono${accent ? ' accent' : ''}`}>{v}</dd>
    </div>
  )
}

/* ── Records ─────────────────────────────────────────────────────────────── */
function Records() {
  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [sel, setSel] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .records({ q, status, page, size: 20 })
      .then((d) => !cancelled && setData(d))
      .catch((e) => !cancelled && setErr(e.message))
    return () => {
      cancelled = true
    }
  }, [q, status, page])

  if (err) return <Offline message={err} />
  if (!data) return <Loading label="Loading records…" />

  return (
    <div className="cons__page">
      <div className="cons__pageHead">
        <div>
          <h1 className="cons__title">Records</h1>
          <p className="note">
            {num(data.total)} matching · {num(data.status_counts['auto-publish'])}{' '}
            auto-publish · {num(data.status_counts['review required'])} to review
          </p>
        </div>
        <div className="cons__pageActions">
          <label className="cons__search">
            <Icon name="search" size={14} />
            <input
              type="search"
              placeholder="Part number, brand, classpath…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value)
                setPage(1)
              }}
              aria-label="Search records"
            />
          </label>
          <select
            className="cons__select"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value)
              setPage(1)
            }}
            aria-label="Filter by status"
          >
            <option value="">All statuses</option>
            <option value="auto-publish">Auto-publish</option>
            <option value="review required">Review required</option>
          </select>
        </div>
      </div>

      <div className="ctablewrap">
        <table className="ctable ctable--rows">
          <thead>
            <tr>
              <th>Part number</th>
              <th>Raw description</th>
              <th>Manufacturer</th>
              <th className="ctable__num">Attrs</th>
              <th className="ctable__num">Conf.</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((r) => (
              <tr
                key={r.row_id}
                onClick={() => setSel(r.row_id)}
                className={sel === r.row_id ? 'is-sel' : ''}
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && setSel(r.row_id)}
              >
                <td className="mono">
                  {r.part_number}
                  {r.sourced && <span className="dot dot--sourced" title="Has a source" />}
                  {r.contradiction && (
                    <span className="dot dot--contra" title="Contradiction" />
                  )}
                </td>
                <td className="ctable__desc">{r.raw_description}</td>
                <td>{r.manufacturer || <span className="dim">unresolved</span>}</td>
                <td className="ctable__num mono">{r.attributes}</td>
                <td className="ctable__num mono">{r.confidence.toFixed(2)}</td>
                <td>
                  <span
                    className={`badge badge--${
                      r.status === 'auto-publish' ? 'verified' : 'review'
                    }`}
                  >
                    {r.status === 'auto-publish' ? 'Publish' : 'Review'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="cons__pager">
        <button
          type="button"
          className="btn btn--ghost"
          disabled={page <= 1}
          onClick={() => setPage((p) => Math.max(1, p - 1))}
        >
          Previous
        </button>
        <span className="mono">
          Page {data.page} / {data.pages}
        </span>
        <button
          type="button"
          className="btn btn--ghost"
          disabled={page >= data.pages}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>

      {sel != null && <RecordDrawer id={sel} onClose={() => setSel(null)} />}
    </div>
  )
}

/* ── Record drawer, with the evidence trail ──────────────────────────────── */
function RecordDrawer({ id, onClose }) {
  const [rec, setRec] = useState(null)
  const [err, setErr] = useState(null)
  const [proof, setProof] = useState(null)

  useEffect(() => {
    setRec(null)
    api.record(id).then(setRec).catch((e) => setErr(e.message))
  }, [id])

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const openProof = async (ref) => {
    setProof({ loading: true, ref })
    try {
      setProof({ ...(await api.locator(ref)), ref })
    } catch (e) {
      setProof({ error: e.message, ref })
    }
  }

  return (
    <div className="drawer" role="dialog" aria-modal="true" aria-label="Record detail">
      <button type="button" className="drawer__scrim" onClick={onClose} aria-label="Close" />
      <div className="drawer__panel">
        <header className="drawer__head">
          <div>
            <span className="meta">Record</span>
            <h2 className="drawer__title mono">{rec?.part_number ?? `#${id}`}</h2>
          </div>
          <button type="button" className="drawer__close" onClick={onClose} aria-label="Close">
            <Icon name="close" size={16} />
          </button>
        </header>

        {err && <Offline message={err} />}
        {!rec && !err && <Loading label="Loading record…" />}

        {rec && (
          <div className="drawer__body">
            <Panel title="As supplied" meta={`${rec.input.populated_cells} of 6 cells`}>
              <dl className="klist">
                {Object.entries(rec.input)
                  .filter(([k]) => k !== 'populated_cells')
                  .map(([k, v]) => (
                    <div className="klist__row" key={k}>
                      <dt className="mono">{k}</dt>
                      <dd className={String(v).startsWith('--') ? 'amber' : ''}>
                        {v || <span className="dim">empty</span>}
                      </dd>
                    </div>
                  ))}
              </dl>
            </Panel>

            <Panel
              title="Resolved"
              meta={`${rec.resolution.method} · ${rec.validation.confidence.toFixed(3)}`}
            >
              <dl className="klist">
                <KV k="Manufacturer" v={rec.manufacturer || '—'} />
                <KV k="Brand" v={rec.brand || '—'} />
                <KV k="Classpath" v={rec.classpath || '—'} />
                <KV k="Family" v={rec.family_id || 'singleton'} />
              </dl>
              {rec.resolution.unmasked_from && (
                <p className="note cpanel__note amber">
                  Invoiced by “{rec.resolution.unmasked_from}”, which is not a
                  manufacturer. Unmasked from the description.
                </p>
              )}
              {rec.contradiction && (
                <p className="note cpanel__note amber">{rec.contradiction.explanation}</p>
              )}
            </Panel>

            <Panel title="Descriptions" meta="limit / length">
              {Object.entries(rec.descriptions).map(([k, d]) => (
                <div className="desc" key={k}>
                  <div className="desc__head">
                    <span className="desc__name mono">{k}</span>
                    <span
                      className={`desc__len mono${
                        d.below_floor ? ' is-short' : ''
                      }`}
                    >
                      {d.length}/{d.limit}
                      {d.below_floor ? ' · below floor' : ''}
                    </span>
                  </div>
                  <p className="desc__value">
                    {d.value || (
                      <span className="dim">
                        {k === 'MARKETING_DESC'
                          ? 'empty — not sourced, never generated'
                          : 'empty'}
                      </span>
                    )}
                  </p>
                </div>
              ))}
            </Panel>

            <Panel
              title="Attributes and their evidence"
              meta={`${rec.attributes.length} · ${rec.attributes_in_sequence} in the leaf sequence`}
            >
              <ul className="attrs">
                {rec.attributes.map((a) => (
                  <li className="attr" key={a.label}>
                    <div className="attr__top">
                      <span className="attr__label">{a.label}</span>
                      <span className="attr__value mono">
                        {a.value} {a.uom}
                      </span>
                      <span className={`kind kind--${a.kind}`}>{a.kind}</span>
                    </div>
                    <p className="attr__rule">{a.rule}</p>
                    {a.locator && (
                      <button
                        type="button"
                        className="attr__loc mono"
                        onClick={() => openProof(a.locator)}
                      >
                        <Icon name="search" size={11} />
                        {a.locator}
                      </button>
                    )}
                  </li>
                ))}
              </ul>
              {rec.unexpanded_abbreviations.length > 0 && (
                <p className="note cpanel__note">
                  Left unexpanded for want of a source:{' '}
                  <span className="mono">
                    {rec.unexpanded_abbreviations.join(', ')}
                  </span>
                </p>
              )}
            </Panel>

            {rec.features.length > 0 && (
              <Panel title="Sourced features" meta={`${rec.features.length}`}>
                <ul className="bullets">
                  {rec.features.map((f) => (
                    <li key={f}>{f}</li>
                  ))}
                </ul>
              </Panel>
            )}

            <Panel
              title="Abstentions"
              meta={`${rec.evidence.abstentions.length}`}
            >
              <ul className="abst">
                {rec.evidence.abstentions.map((a, i) => (
                  <li key={i}>
                    <span className="abst__field mono">{a.field}</span>
                    <span className="abst__reason">{a.reason}</span>
                    {a.detail && <span className="abst__detail">{a.detail}</span>}
                  </li>
                ))}
              </ul>
            </Panel>
          </div>
        )}
      </div>

      {proof && (
        <ProofPopover proof={proof} onClose={() => setProof(null)} />
      )}
    </div>
  )
}

function ProofPopover({ proof, onClose }) {
  return (
    <div className="proof" role="dialog" aria-label="Evidence">
      <header className="proof__head">
        <span className="meta">
          {proof.kind === 'doc' ? proof.domain : `Supplied · ${proof.field ?? ''}`}
        </span>
        <button type="button" onClick={onClose} aria-label="Close evidence">
          <Icon name="close" size={14} />
        </button>
      </header>
      {proof.loading && <p className="note">Resolving…</p>}
      {proof.error && <p className="note amber">{proof.error}</p>}
      {proof.quote != null && (
        <>
          <p className="proof__body mono">
            <span className="dim">…{proof.context_before?.slice(-180)}</span>
            <mark>{proof.quote}</mark>
            <span className="dim">{proof.context_after?.slice(0, 180)}…</span>
          </p>
          <footer className="proof__foot">
            <span className="mono">{proof.ref}</span>
            {proof.kind === 'doc' && proof.reconstructed && (
              <span className="badge badge--review">Reconstructed fixture</span>
            )}
          </footer>
        </>
      )}
    </div>
  )
}

/* ── Discovery ───────────────────────────────────────────────────────────── */
function Discovery() {
  const [d, setD] = useState(null)
  const [err, setErr] = useState(null)
  const [fam, setFam] = useState(null)

  useEffect(() => {
    api.discovery().then(setD).catch((e) => setErr(e.message))
  }, [])

  if (err) return <Offline message={err} />
  if (!d) return <Loading label="Loading discovery…" />

  const open = async (id) => {
    setFam({ loading: true })
    try {
      setFam(await api.family(id))
    } catch (e) {
      setFam({ error: e.message })
    }
  }

  return (
    <div className="cons__page">
      <div className="cons__pageHead">
        <div>
          <h1 className="cons__title">Discovery</h1>
          <p className="note">
            {num(d.families.family_count)} families ·{' '}
            {num(d.families.axis_count)} variant axes ·{' '}
            {num(d.induction.attribute_count)} induced attributes ·{' '}
            {d.induction.model_calls} model calls
          </p>
        </div>
      </div>

      <div className="cons__two">
        <Panel title="Largest families" meta="click to inspect">
          <table className="ctable">
            <thead>
              <tr>
                <th>Family</th>
                <th className="ctable__num">Members</th>
                <th className="ctable__num">Axes</th>
                <th>Skeleton</th>
              </tr>
            </thead>
            <tbody>
              {d.families.families.slice(0, 14).map((f) => (
                <tr key={f.family_id} onClick={() => open(f.family_id)} tabIndex={0}>
                  <td className="mono">{f.family_id}</td>
                  <td className="ctable__num mono">{f.size}</td>
                  <td className="ctable__num mono">{f.axes.length}</td>
                  <td className="ctable__note mono">{f.skeleton}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        <Panel
          title="Induced attributes"
          meta={`${d.induction.labels_awaiting_a_name} awaiting a name`}
        >
          <ul className="induced">
            {d.induction.attributes.slice(0, 18).map((a) => (
              <li key={a.attr_id} className={a.needs_name ? 'is-unnamed' : ''}>
                <div className="induced__top">
                  <span className="induced__label">
                    {a.label ?? <em>unnamed</em>}
                  </span>
                  <span className={`kind kind--${a.needs_name ? 'inferred' : 'derived'}`}>
                    {a.label_source}
                  </span>
                  <span className="induced__support mono">{a.affected_rows} rows</span>
                </div>
                <p className="induced__vals mono">{a.values.slice(0, 8).join(' · ')}</p>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel
        title="Propagations blocked by the axis rule"
        meta={`${num(d.propagation.propagations_blocked_by_the_axis_rule)} refused`}
      >
        <p className="note cpanel__note">{d.propagation.rule}</p>
        <table className="ctable">
          <thead>
            <tr>
              <th>Manufacturer / leaf</th>
              <th>Attribute</th>
              <th>Values that differ</th>
            </tr>
          </thead>
          <tbody>
            {(d.propagation.blocked_examples || []).slice(0, 12).map((b, i) => (
              <tr key={i}>
                <td>
                  {b.manufacturer} <span className="dim">/ {b.leaf}</span>
                </td>
                <td>{b.label}</td>
                <td className="ctable__note mono">{(b.values || []).join(' · ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Panel>

      {fam && <FamilyDrawer fam={fam} onClose={() => setFam(null)} />}
    </div>
  )
}

function FamilyDrawer({ fam, onClose }) {
  if (fam.loading) return null
  const axisSlots = new Set((fam.axes || []).map((a) => a.slot))
  return (
    <div className="drawer" role="dialog" aria-modal="true" aria-label="Family">
      <button type="button" className="drawer__scrim" onClick={onClose} aria-label="Close" />
      <div className="drawer__panel">
        <header className="drawer__head">
          <div>
            <span className="meta">Family</span>
            <h2 className="drawer__title mono">{fam.family_id}</h2>
          </div>
          <button type="button" className="drawer__close" onClick={onClose} aria-label="Close">
            <Icon name="close" size={16} />
          </button>
        </header>
        <div className="drawer__body">
          {fam.error && <Offline message={fam.error} />}
          {!fam.error && (
            <>
              <Panel title="Members" meta={`${fam.members.length}`}>
                <div className="famrows">
                  {fam.members.map((mem) => (
                    <div className="famrow" key={mem.row_id}>
                      <span className="famrow__pn mono">{mem.part_number}</span>
                      <span className="famrow__toks">
                        {mem.tokens.map((t, i) => (
                          <span
                            key={i}
                            className={
                              axisSlots.has(i) ? 'tok--vary' : 'tok--hold'
                            }
                          >
                            {t.text}
                          </span>
                        ))}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="note cpanel__note">
                  Highlighted positions vary between siblings, so they are attributes —
                  and they are never propagated.
                </p>
              </Panel>

              <Panel title="Variant axes" meta={`${fam.axes.length}`}>
                <ul className="induced">
                  {fam.axes.map((a) => (
                    <li key={a.slot} className={a.label ? '' : 'is-unnamed'}>
                      <div className="induced__top">
                        <span className="induced__label">
                          {a.label ?? <em>unnamed axis</em>}
                        </span>
                        <span className="induced__support mono">slot {a.slot}</span>
                      </div>
                      <p className="induced__vals mono">{a.values.join(' · ')}</p>
                    </li>
                  ))}
                </ul>
              </Panel>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Sourcing gate ───────────────────────────────────────────────────────── */
function Sourcing() {
  const [s, setS] = useState(null)
  const [err, setErr] = useState(null)
  const [url, setUrl] = useState('https://www.homedepot.com/p/49-94-0013')
  const [mfr, setMfr] = useState('Milwaukee Tool')
  const [verdict, setVerdict] = useState(null)

  useEffect(() => {
    api.sourcing().then(setS).catch((e) => setErr(e.message))
  }, [])

  if (err) return <Offline message={err} />
  if (!s) return <Loading label="Loading sourcing gate…" />

  const test = async (e) => {
    e.preventDefault()
    try {
      setVerdict(await api.gateTest(url, mfr))
    } catch (ex) {
      setVerdict({ verdict: 'error', reason: ex.message })
    }
  }

  return (
    <div className="cons__page">
      <div className="cons__pageHead">
        <div>
          <h1 className="cons__title">Sourcing gate</h1>
          <p className="note">
            {s.candidates_considered} candidates · {s.admitted} admitted ·{' '}
            {s.rejected_count} rejected before any request · {s.blocked_count} blocked by
            the site
          </p>
        </div>
      </div>

      {s.reconstructed && (
        <div className="cons__flash cons__flash--warn">
          <Icon name="warning" size={13} />
          <span>
            <strong>These are reconstructed fixtures, not live captures.</strong> The
            structure matches a real manufacturer page — a spec block, a feature list, a
            marketing paragraph, document links — but the wording is generated, so treat
            the sourced values as a demonstration of the mechanism rather than as facts
            about these products. Replace them with genuine caches using{' '}
            <span className="mono">uniforge source --fetch --discover</span>; the index
            format is identical and the flag clears itself.
          </span>
        </div>
      )}

      <Panel title="Test the gate" meta="nothing is requested">
        <form className="gateform" onSubmit={test}>
          <input
            className="cons__input"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            aria-label="Candidate URL"
            placeholder="https://…"
          />
          <input
            className="cons__input cons__input--short"
            value={mfr}
            onChange={(e) => setMfr(e.target.value)}
            aria-label="Resolved manufacturer"
            placeholder="Manufacturer"
          />
          <button type="submit" className="btn btn--primary">
            Classify
          </button>
        </form>
        {verdict && (
          <div className={`gateverdict gateverdict--${verdict.verdict}`}>
            <StatusBadge tone={verdict.verdict === 'admitted' ? 'verified' : 'review'}>
              {verdict.verdict}
            </StatusBadge>
            <span className="mono gateverdict__dom">{verdict.domain}</span>
            <span className="gateverdict__why">{verdict.reason}</span>
          </div>
        )}
        <p className="note cpanel__note">
          Nothing is requested. The verdict is reached from the domain alone, which is the
          point — an excluded source is never contacted.
        </p>
      </Panel>

      <div className="cons__two">
        <Panel title="Rejected before any request" meta={`${s.rejected_count}`}>
          <ul className="gatelist">
            {s.rejected_before_request.map((r, i) => (
              <li key={i}>
                <span className="gatelist__dom mono">{r.domain}</span>
                <span className="gatelist__why">{r.reason}</span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel title="Admitted, then refused by the site" meta={`${s.blocked_count}`}>
          <ul className="gatelist">
            {s.blocked_by_site.map((r, i) => (
              <li key={i}>
                <span className="gatelist__dom mono">{r.domain}</span>
                <span className="gatelist__why amber">{r.reason}</span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <Panel title="Cached documents" meta={`${s.documents_cached}`}>
        <div className="ctablewrap">
          <table className="ctable">
            <thead>
              <tr>
                <th>Part number</th>
                <th>Domain</th>
                <th className="ctable__num">Chars</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {s.documents.slice(0, 30).map((doc) => (
                <tr key={doc.doc_id}>
                  <td className="mono">{doc.part_number}</td>
                  <td>{doc.domain}</td>
                  <td className="ctable__num mono">{num(doc.chars)}</td>
                  <td className="ctable__note mono">{doc.url}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}

/* ── Review queue ────────────────────────────────────────────────────────── */
function ReviewQueue({ onChanged }) {
  const [rq, setRq] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(null)
  const [result, setResult] = useState(null)

  const reload = useCallback(() => {
    api.review().then(setRq).catch((e) => setErr(e.message))
  }, [])

  useEffect(reload, [reload])

  if (err) return <Offline message={err} />
  if (!rq) return <Loading label="Loading review queue…" />

  const KIND_MAP = {
    'attribute label awaiting a name': 'attribute_name',
    'item type outside the derived taxonomy': 'item_type',
    'manufacturer unresolved': 'manufacturer',
    'source contradiction': 'contradiction',
  }

  const decide = async (action, value) => {
    const kind = KIND_MAP[action.kind]
    if (!kind || !value) return
    setBusy(action.action_id)
    setResult(null)
    try {
      let key = action.action_id
      if (kind === 'attribute_name') {
        key = (action.evidence[0] || '').split(' · ')[0]
      } else if (kind === 'item_type') {
        key = action.prompt.replace(/^Map item type "/, '').replace(/" to a classpath$/, '')
      } else if (kind === 'manufacturer') {
        key = action.prompt.replace(/^Map "/, '').replace(/" to an approved manufacturer$/, '')
      } else if (kind === 'contradiction') {
        key = String(action.records[0])
        value = value.startsWith('Manufacturer is') ? 'brand_owner' : 'supplied'
      }
      const r = await api.decide({ kind, key, value })
      setResult(r)
      reload()
      onChanged?.()
    } catch (e) {
      setResult({ error: e.message })
    } finally {
      setBusy(null)
    }
  }

  const reset = async () => {
    setBusy('reset')
    try {
      await api.resetReview()
      setResult(null)
      reload()
      onChanged?.()
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="cons__page">
      <div className="cons__pageHead">
        <div>
          <h1 className="cons__title">Review queue</h1>
          <p className="note">
            {num(rq.review_records)} records, {num(rq.action_count)} decisions —{' '}
            {rq.records_per_action} records cleared per decision.{' '}
            {num(rq.auto_publish_records)} already auto-publish ({rq.auto_publish_pct}%).
          </p>
        </div>
        <div className="cons__pageActions">
          {rq.decisions.decisions > 0 && (
            <button
              type="button"
              className="btn btn--ghost"
              onClick={reset}
              disabled={busy === 'reset'}
            >
              Reset {rq.decisions.decisions} decision
              {rq.decisions.decisions === 1 ? '' : 's'}
            </button>
          )}
        </div>
      </div>

      {result && !result.error && (
        <p className="cons__flash">
          Applied. Auto-publish moved from {num(result.auto_publish_before)} to{' '}
          {num(result.auto_publish_after)} —{' '}
          <strong>{num(result.records_unblocked)} records unblocked</strong> by one
          decision. Actions remaining: {result.actions_after}.
        </p>
      )}
      {result?.error && <p className="cons__flash cons__flash--warn">{result.error}</p>}

      <div className="cgrid cgrid--4">
        {rq.blockers
          .filter((b) => b.records > 0)
          .map((b) => (
            <Stat
              key={b.blocker}
              value={num(b.records)}
              label={b.blocker}
              sub={`${b.actions} action${b.actions === 1 ? '' : 's'} · ${b.one_action_clears} each`}
            />
          ))}
      </div>

      <div className="actions">
        {rq.actions.slice(0, 24).map((a) => (
          <ActionCard
            key={a.action_id}
            action={a}
            busy={busy === a.action_id}
            onDecide={decide}
          />
        ))}
      </div>
    </div>
  )
}

function ActionCard({ action, busy, onDecide }) {
  const [value, setValue] = useState('')
  const decidable = Boolean(action.options?.length)

  return (
    <article className="action">
      <header className="action__head">
        <span className={`kind kind--${
          action.kind === 'source contradiction' ? 'inferred' : 'derived'
        }`}>
          {action.kind}
        </span>
        <span className="action__lev mono">
          unblocks {action.records_unblocked}
        </span>
      </header>
      <h3 className="action__prompt">{action.prompt}</h3>
      <p className="action__detail">{action.detail}</p>
      {action.evidence?.length > 0 && (
        <ul className="action__ev">
          {action.evidence.slice(0, 3).map((e, i) => (
            <li key={i} className="mono">
              {e}
            </li>
          ))}
        </ul>
      )}
      {decidable ? (
        <div className="action__foot">
          <select
            className="cons__select"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            aria-label="Decision"
          >
            <option value="">Choose…</option>
            {action.options.map((o) => (
              <option key={o} value={o}>
                {o}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="btn btn--primary"
            disabled={!value || busy}
            onClick={() => onDecide(action, value)}
          >
            {busy ? 'Applying…' : 'Apply once'}
          </button>
        </div>
      ) : (
        <p className="note action__note">
          Needs a mapping target that is not in the derived taxonomy yet.
        </p>
      )}
    </article>
  )
}

/* ── Search lab ──────────────────────────────────────────────────────────── */
const EXAMPLES = [
  'thin cut-off wheel 7/8 arbor',
  'abrasive disc p120',
  'composite deck board brownstone',
  'gfci outlet 20 amp',
  'electric hot water tank 50 gal',
]

function SearchLab() {
  const [q, setQ] = useState(EXAMPLES[0])
  const [res, setRes] = useState(null)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)

  const run = useCallback(async (query) => {
    setBusy(true)
    setErr(null)
    try {
      setRes(await api.search(query))
    } catch (e) {
      setErr(e.message)
    } finally {
      setBusy(false)
    }
  }, [])

  useEffect(() => {
    run(EXAMPLES[0])
  }, [run])

  return (
    <div className="cons__page">
      <div className="cons__pageHead">
        <div>
          <h1 className="cons__title">Search readiness</h1>
          <p className="note">
            The same query, the same scorer, run against the raw catalogue and the
            compiled one. Part numbers are stripped because a unique key inflates any
            baseline.
          </p>
        </div>
      </div>

      <form
        className="searchlab__form"
        onSubmit={(e) => {
          e.preventDefault()
          run(q)
        }}
      >
        <label className="cons__search cons__search--wide">
          <Icon name="search" size={15} />
          <input
            type="search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Type the way a counter clerk types…"
            aria-label="Search query"
          />
        </label>
        <button type="submit" className="btn btn--primary" disabled={busy}>
          {busy ? 'Searching…' : 'Run'}
        </button>
      </form>

      <div className="searchlab__examples">
        {EXAMPLES.map((e) => (
          <button
            key={e}
            type="button"
            className="pill searchlab__ex"
            onClick={() => {
              setQ(e)
              run(e)
            }}
          >
            {e}
          </button>
        ))}
      </div>

      {err && <Offline message={err} />}

      {res && (
        <div className="cons__two searchlab__results">
          <Panel title="Raw catalogue" meta={`${res.before.length} hits`}>
            <ResultList items={res.before} empty="No results — the supplier never wrote these words." />
          </Panel>
          <Panel title="Compiled catalogue" meta={`${res.after.length} hits`}>
            <ResultList items={res.after} accent />
          </Panel>
        </div>
      )}
    </div>
  )
}

function ResultList({ items, accent, empty = 'No results.' }) {
  if (!items.length) return <p className="note">{empty}</p>
  return (
    <ol className="hits">
      {items.map((h, i) => (
        <li key={h.row_id} className="hit">
          <span className="hit__rank mono">{i + 1}</span>
          <div className="hit__main">
            <span className={`hit__title${accent ? ' accent' : ''}`}>
              {h.title || h.raw_description}
            </span>
            <span className="hit__meta mono">
              {h.part_number}
              {h.classpath ? ` · ${h.classpath.split('>').pop()}` : ''}
            </span>
          </div>
          <span className="hit__score mono">{h.score.toFixed(2)}</span>
        </li>
      ))}
    </ol>
  )
}
