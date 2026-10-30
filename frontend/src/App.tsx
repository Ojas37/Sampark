import { useMemo, useState } from 'react'
import { Link, Navigate, NavLink, Route, Routes, useNavigate, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity, AlertTriangle, ArrowDownRight, ArrowUpRight, BadgeCheck, Bell, BookOpen, CalendarDays,
  Check, ChevronDown, ChevronRight, Clock3, FileCheck2, FileText, Fingerprint,
  LayoutDashboard, LogOut, RefreshCw, Search, Settings2, ShieldCheck, Sparkles,
  Workflow, X,
} from 'lucide-react'
import { api, login as loginRequest, type Application, type Candidate, type DocumentSummary, type User } from './api/client'

const menu = [
  { title: 'Workspace', items: [
    { label: 'Dashboard', path: '/', icon: LayoutDashboard },
    { label: 'Action inbox', path: '/inbox', icon: Activity },
    { label: 'Applications', path: '/cases', icon: FileText },
    { label: 'EVC planner', path: '/planner', icon: CalendarDays },
    { label: 'Compliance', path: '/compliance', icon: FileCheck2 },
    { label: 'Simulator', path: '/simulator', icon: Activity },
    { label: 'Outbox', path: '/outbox', icon: Bell },
  ] },
  { title: 'Governance', items: [
    { label: 'Workflow studio', path: '/studio', icon: Workflow },
    { label: 'Audit trail', path: '/audit', icon: Fingerprint },
    { label: 'Rules & traceability', path: '/rules', icon: BookOpen },
  ] },
]

function useCurrentUser() {
  return useMemo(() => {
    const raw = localStorage.getItem('flowwise_user')
    return raw ? JSON.parse(raw) as User : null
  }, [])
}

function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('system_admin@demo.test')
  const [password, setPassword] = useState('demo1234')
  const [error, setError] = useState('')
  const { data: accounts = [] } = useQuery({ queryKey: ['accounts'], queryFn: () => api<Array<{email: string; role: string; password: string}>>('/api/v1/demo/accounts') })
  const mutation = useMutation({
    mutationFn: () => loginRequest(email, password),
    onSuccess: (result) => {
      localStorage.setItem('flowwise_token', result.access_token)
      localStorage.setItem('flowwise_user', JSON.stringify(result.user))
      navigate('/')
    },
    onError: (reason) => setError(reason instanceof Error ? reason.message : 'Unable to sign in'),
  })

  return <main className="login-page">
    <section className="login-art">
      <div className="brand brand-light"><span className="brand-mark"><Workflow size={21} /></span><span>SAMPARK</span></div>
      <div className="login-message">
        <span className="eyebrow">AICTE APPROVAL WORKFLOW</span>
        <h1>Clarity at every<br /><em>decision point.</em></h1>
        <p>One auditable workspace for approvals, compliance and expert visit coordination.</p>
        <div className="login-stat"><div className="stat-icon"><ShieldCheck size={18} /></div><div><strong>Human-led decisions</strong><span>AI and scoring are advisory. Officers remain in control.</span></div></div>
        <div className="art-orbit orbit-one" /><div className="art-orbit orbit-two" />
      </div>
      <span className="login-foot">SMART INDIA HACKATHON · SIH26262</span>
    </section>
    <section className="login-panel">
      <div className="login-form-wrap">
        <span className="eyebrow">DEMO ENVIRONMENT</span>
        <h2>Welcome back</h2>
        <p className="muted">Sign in with one of the synthetic demo accounts.</p>
        <form onSubmit={(event) => { event.preventDefault(); setError(''); mutation.mutate() }}>
          <label htmlFor="email">Demo account</label>
          <select id="email" value={email} onChange={(event) => setEmail(event.target.value)}>
            {accounts.map((account) => <option value={account.email} key={account.email}>{account.role.replaceAll('_', ' ')} · {account.email}</option>)}
          </select>
          <label htmlFor="password">Password</label>
          <input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          {error && <div className="error-box"><AlertTriangle size={16} />{error}</div>}
          <button className="button button-primary button-wide" disabled={mutation.isPending}>{mutation.isPending ? 'Signing in…' : 'Sign in'}<ChevronRight size={17} /></button>
        </form>
        <div className="demo-credential"><span><BadgeCheck size={15} /> Demo password</span><code>demo1234</code></div>
        <div className="login-note"><ShieldCheck size={16} /><span>All data is synthetic. Integrations are simulated.</span></div>
      </div>
      <footer>SAMPARK Prototype <span>·</span> v3.0 specification</footer>
    </section>
  </main>
}

function AppShell() {
  const user = useCurrentUser()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [toast, setToast] = useState('')
  const isAdmin = user?.role === 'SYSTEM_ADMIN'
  const userRole = user?.role ?? ''
  const visibleMenu = menu.map((group) => ({
    ...group,
    items: group.items.filter((item) => {
      if (item.path === '/planner') return ['EVC_COORDINATOR', 'SYSTEM_ADMIN', 'REGIONAL_OFFICER', 'SENIOR_MANAGEMENT'].includes(userRole)
      if (item.path === '/simulator') return ['SYSTEM_ADMIN', 'SENIOR_MANAGEMENT'].includes(userRole)
      if (item.path === '/studio') return ['SYSTEM_ADMIN', 'SECOND_APPROVER'].includes(userRole)
      if (item.path === '/audit') return ['SYSTEM_ADMIN', 'AUDITOR'].includes(userRole)
      if (item.path === '/rules') return ['SYSTEM_ADMIN', 'AUDITOR', 'SENIOR_MANAGEMENT'].includes(userRole)
      return true
    }),
  })).filter((group) => group.items.length > 0)
  const clock = useQuery({ queryKey: ['clock'], queryFn: () => api<{now: string; offset_seconds: number}>('/api/v1/demo/clock'), enabled: isAdmin, refetchInterval: 30000 })
  const logout = () => {
    localStorage.removeItem('flowwise_token')
    localStorage.removeItem('flowwise_user')
    navigate('/login')
  }
  const demoAction = async (action: 'reset' | 'advance' | 'tamper') => {
    try {
      if (action === 'advance') await api('/api/v1/demo/clock/advance', { method: 'POST', body: JSON.stringify({ working_hours: 10 }) })
      if (action === 'reset') await api('/api/v1/demo/reset', { method: 'POST', body: '{}' })
      if (action === 'tamper') await api('/api/v1/demo/tamper', { method: 'POST', body: '{}' })
      setToast(action === 'advance' ? 'Demo clock advanced by 10 working hours' : action === 'reset' ? 'Synthetic demo data reset' : 'Demo audit event altered')
      await queryClient.invalidateQueries()
      window.setTimeout(() => setToast(''), 3500)
    } catch (reason) {
      setToast(reason instanceof Error ? reason.message : 'Demo action failed')
    }
  }
  if (!user) return <Navigate to="/login" replace />
  const initials = user.name.split(' ').map((part) => part[0]).slice(0, 2).join('').toUpperCase()
  return <div className="app-shell">
    <aside className="sidebar">
      <Link to="/" className="brand"><span className="brand-mark"><Workflow size={20} /></span><span>SAMPARK</span></Link>
      <div className="workspace-switch"><div className="workspace-icon">A</div><div><strong>AICTE Workspace</strong><span>Prototype environment</span></div><ChevronDown size={15} /></div>
      <nav className="side-nav">
        {visibleMenu.map((group) => <section key={group.title}><span className="nav-heading">{group.title}</span>{group.items.map(({ label, path, icon: Icon }) =>
          <NavLink key={path} to={path} end={path === '/'} className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}><Icon size={17} /><span>{label}</span>{label === 'Action inbox' && <span className="nav-count">8</span>}</NavLink>,
        )}</section>)}
      </nav>
      <div className="sidebar-bottom">
        <div className="sidebar-help"><div className="help-mark"><Sparkles size={16} /></div><strong>Prototype workspace</strong><span>Built on synthetic data for SIH 2026.</span><Link to="/rules">View traceability <ChevronRight size={13} /></Link></div>
        <button className="profile-button" onClick={logout}><span className="avatar">{initials}</span><span className="profile-copy"><strong>{user.name}</strong><small>{user.role.replaceAll('_', ' ')}</small></span><LogOut size={16} /></button>
      </div>
    </aside>
    <main className="main-shell">
      <header className="topbar"><div className="breadcrumbs"><span>SAMPARK</span><ChevronRight size={14} /><strong>Operations workspace</strong></div><div className="topbar-actions"><div className="topbar-search"><Search size={16} /><input placeholder="Search cases, institutions…" aria-label="Search" /></div><button className="icon-button" aria-label="Notifications"><Bell size={18} /><i /></button><span className="avatar avatar-small">{initials}</span></div></header>
      <div className="synthetic-banner"><span className="banner-dot" /><strong>Synthetic data.</strong> Integrations simulated. No live AICTE systems connected.</div>
      {isAdmin && <div className="demo-bar"><div><span className="demo-indicator" /> DEMO CONTROLS <span className="demo-time">{clock.data ? new Date(clock.data.now).toLocaleString() : 'Clock loading…'}</span></div><div className="demo-actions"><button onClick={() => demoAction('advance')}><Clock3 size={14} /> +10 hours</button><button onClick={() => demoAction('reset')}><RefreshCw size={14} /> Reset</button><button onClick={() => demoAction('tamper')}><AlertTriangle size={14} /> Tamper test</button></div></div>}
      {toast && <div className="toast"><Check size={16} />{toast}<button onClick={() => setToast('')} aria-label="Dismiss"><X size={15} /></button></div>}
      <div className="page-content"><Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/inbox" element={<InboxPage />} />
        <Route path="/cases" element={<CasesPage />} />
        <Route path="/planner" element={<PlannerPage />} />
        <Route path="/compliance" element={<CompliancePage />} />
        <Route path="/simulator" element={<SimulatorPage />} />
        <Route path="/outbox" element={<OutboxPage />} />
        <Route path="/studio" element={<StudioPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/rules" element={<RulesPage />} />
        <Route path="*" element={<DashboardPage />} />
      </Routes></div>
      <footer className="app-footer"><span>AICTE SAMPARK · SIH 2026 prototype</span><span>All workflow values are configurable demo assumptions.</span></footer>
    </main>
  </div>
}

function PageHeading({ eyebrow, title, description, action }: {eyebrow: string; title: string; description: string; action?: React.ReactNode}) {
  return <div className="page-heading"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</div>
}

function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ['dashboard'], queryFn: () => api<{total: number; active: number; evc_ready: number; open_deficiencies: number; overdue_undertakings: number; by_stage: Record<string, number>}>('/api/v1/dashboard/summary') })
  const { data: applications = [] } = useQuery({ queryKey: ['applications'], queryFn: () => api<Application[]>('/api/v1/applications') })
  const stageRows = Object.entries(data?.by_stage ?? {}).map(([stage, count]) => ({ stage: stage.replaceAll('_', ' '), count }))
  const latest = applications.slice(0, 5)
  return <><PageHeading eyebrow="OVERVIEW · FR-08" title="Good morning" description="A clear view of your approval workload and what needs attention." action={<button className="button button-secondary" onClick={() => window.location.reload()}><RefreshCw size={15} /> Refresh data</button>} />
    {isLoading ? <Loading /> : <><div className="metrics-grid">
      <Metric label="Total applications" value={data?.total ?? 0} note="Across visible scope" icon={FileText} tone="navy" />
      <Metric label="Active cases" value={data?.active ?? 0} note="In progress" icon={Activity} tone="teal" trend="8.2%" />
      <Metric label="EVC queue" value={data?.evc_ready ?? 0} note="Awaiting visit planning" icon={CalendarDays} tone="violet" />
      <Metric label="Open deficiencies" value={data?.open_deficiencies ?? 0} note={`${data?.overdue_undertakings ?? 0} overdue undertakings`} icon={AlertTriangle} tone="amber" />
    </div>
    <div className="dashboard-grid">
      <section className="panel stage-panel"><div className="panel-heading"><div><h2>Applications by stage</h2><p>Current distribution in your authorised scope</p></div><span className="live-tag"><i /> Live</span></div>
        {stageRows.length ? <div className="stage-bars">{stageRows.map((row, index) => <div className="stage-bar-row" key={row.stage}><span>{row.stage}</span><div className="bar-track"><i style={{ width: `${Math.max(4, row.count / Math.max(data?.total ?? 1, 1) * 100)}%`, background: ['#0e7c7b', '#4b78b8', '#9c81d2', '#d2a44c'][index % 4] }} /></div><strong>{row.count}</strong></div>)}</div> : <EmptyState title="No stage data" detail="Seed demo data to populate the dashboard." />}
        <div className="panel-footnote"><span><i className="legend-dot teal" /> In progress</span><span>Source: synthetic seed dataset</span></div>
      </section>
      <section className="panel attention-panel"><div className="panel-heading"><div><h2>Needs attention</h2><p>Priority items from your workspace</p></div><Link to="/inbox" className="text-link">View inbox <ChevronRight size={14} /></Link></div>
        <AttentionItem color="amber" title="SLA approaching threshold" description="FW-2026-0002 · Scrutiny" tag="10h remaining" />
        <AttentionItem color="coral" title="Institution response overdue" description="FW-2026-0003 · Demo Institute 03" tag="6 days" />
        <AttentionItem color="blue" title="EVC visit not scheduled" description="30 cases are ready for a plan" tag="EVC queue" />
        <Link to="/cases" className="attention-link">Review all open cases <ArrowUpRight size={14} /></Link>
      </section>
    </div>
    <section className="panel table-panel"><div className="panel-heading"><div><h2>Recently updated cases</h2><p>Latest activity across the visible case list</p></div><Link to="/cases" className="text-link">All applications <ChevronRight size={14} /></Link></div><ApplicationsTable applications={latest} /></section>
    <div className="info-strip"><div className="info-icon"><Sparkles size={17} /></div><div><strong>Designed to support decisions, not make them.</strong><span>Priority scores, workflow rules and AI suggestions are advisory. Authorised officers make every approval decision.</span></div><Link to="/rules">See rule tags <ChevronRight size={14} /></Link></div></>}
  </>
}

function Metric({ label, value, note, icon: Icon, tone, trend }: {label: string; value: number; note: string; icon: typeof FileText; tone: string; trend?: string}) {
  return <div className={`metric-card tone-${tone}`}><div className="metric-top"><span>{label}</span><i><Icon size={17} /></i></div><div className="metric-value">{value.toLocaleString()}</div><div className="metric-note">{trend && <b><ArrowUpRight size={13} /> {trend}</b>}{note}</div></div>
}

function AttentionItem({ color, title, description, tag }: {color: string; title: string; description: string; tag: string}) {
  return <div className="attention-item"><span className={`attention-mark ${color}`} /><div><strong>{title}</strong><span>{description}</span></div><small>{tag}</small></div>
}

function ApplicationsTable({ applications }: {applications: Application[]}) {
  if (!applications.length) return <EmptyState title="No applications found" detail="No cases are available in your current scope." />
  return <div className="table-scroll"><table><thead><tr><th>Reference</th><th>Institution</th><th>Stage</th><th>Owner</th><th>Priority</th><th>Status</th><th /></tr></thead><tbody>
    {applications.map((item) => <tr key={item.id}><td><Link className="case-ref" to={`/cases?case=${item.id}`}>{item.reference_no}<small>{item.application_type.replaceAll('_', ' ')}</small></Link></td><td>{item.institution}<small className="cell-sub">{item.region_code} Region</small></td><td><span className={`stage-pill stage-${item.stage.toLowerCase()}`}>{item.stage.replaceAll('_', ' ')}</span></td><td>{item.owner_role ? item.owner_role.replaceAll('_', ' ') : '—'}</td><td><Priority value={item.priority} /></td><td><span className={`status-dot ${item.status.toLowerCase()}`} />{item.status.replaceAll('_', ' ')}</td><td><Link to={`/cases?case=${item.id}`} className="row-arrow" aria-label={`Open ${item.reference_no}`}><ChevronRight size={16} /></Link></td></tr>)}
  </tbody></table></div>
}

function Priority({ value }: {value: number}) {
  return <span className="priority">{Array.from({ length: 5 }, (_, i) => <i className={i < value ? 'on' : ''} key={i} />)}<small>P{value}</small></span>
}

function CasesPage() {
  const [query, setQuery] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const selectedId = Number(searchParams.get('case')) || null
  const { data: applications = [], isLoading } = useQuery({ queryKey: ['applications'], queryFn: () => api<Application[]>('/api/v1/applications') })
  const filtered = applications.filter((item) => `${item.reference_no} ${item.institution} ${item.stage}`.toLowerCase().includes(query.toLowerCase()))
  const selected = applications.find((item) => item.id === selectedId)
  return <><PageHeading eyebrow="CASE MANAGEMENT · FR-01" title="Applications" description="Review case status, ownership and next actions across your authorised scope." action={<span className="record-count">{applications.length} records</span>} />
    <section className="panel case-list-panel"><div className="list-toolbar"><div className="list-search"><Search size={16} /><input aria-label="Filter applications" placeholder="Search by case or institution" value={query} onChange={(e) => setQuery(e.target.value)} /></div><button className="button button-secondary" onClick={() => window.location.reload()}><RefreshCw size={15} /> Refresh</button></div>
      {isLoading ? <Loading /> : <ApplicationsTable applications={filtered} />}
    </section>
    {selected && <CaseDetails application={selected} onClose={() => setSearchParams({})} />}
    {!selected && <p className="table-hint">Select a case reference to inspect its timeline and workflow actions.</p>}
  </>
}

function CaseDetails({ application, onClose }: {application: Application; onClose: () => void}) {
  const queryClient = useQueryClient()
  const [reason, setReason] = useState('')
  const [notice, setNotice] = useState('')
  const { data: timeline = [] } = useQuery({ queryKey: ['timeline', application.id], queryFn: () => api<Array<{id: number; action: string; reason: string | null; occurred_at: string}>>(`/api/v1/applications/${application.id}/timeline`) })
  const { data: sla } = useQuery({ queryKey: ['sla', application.id], queryFn: () => api<{totals_seconds: Record<string, number>; segments: Array<{holder: string; stage: string; started_at: string; ended_at: string | null}>}>(`/api/v1/applications/${application.id}/sla`) })
  const { data: observations = [] } = useQuery({ queryKey: ['observations', application.id], queryFn: () => api<Array<{id: number; category: string; remarks: string; status: string; response: string | null}>>(`/api/v1/applications/${application.id}/observations`) })
  const mutate = useMutation({
    mutationFn: async ({ event, text }: {event: string; text: string}) => api(`/api/v1/applications/${application.id}/transitions`, {
      method: 'POST',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({ event, reason: text || null, expected_version: application.version }),
    }),
    onSuccess: async () => { setNotice('Workflow event recorded and added to the audit chain.'); setReason(''); await queryClient.invalidateQueries() },
    onError: (error) => setNotice(error instanceof Error ? error.message : 'Action could not be completed'),
  })
  const addDeficiency = useMutation({
    mutationFn: () => api(`/api/v1/applications/${application.id}/observations`, {
      method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({ category: 'DOCUMENTATION', remarks: reason }),
    }),
    onSuccess: async () => { setNotice('Deficiency issued. SLA ownership switched to the institution.'); setReason(''); await queryClient.invalidateQueries() },
    onError: (error) => setNotice(error instanceof Error ? error.message : 'Unable to issue deficiency'),
  })
  const total = Object.values(sla?.totals_seconds ?? {}).reduce((sum, value) => sum + value, 0)
  const canScrutinize = ['SCRUTINY_OFFICER', 'SYSTEM_ADMIN'].includes(useCurrentUser()?.role ?? '')
  const isApplicant = useCurrentUser()?.role === 'INSTITUTION_APPLICANT'
  const canCoordinate = ['EVC_COORDINATOR', 'SYSTEM_ADMIN'].includes(useCurrentUser()?.role ?? '')
  const openObservation = observations.find((item) => item.status === 'OPEN')
  return <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}><section className="case-drawer">
    <div className="drawer-heading"><div><span className="eyebrow">CASE DETAIL · {application.region_code}</span><h2>{application.reference_no}</h2><p>{application.institution} · {application.application_type.replaceAll('_', ' ')}</p></div><button className="icon-button" aria-label="Close case" onClick={onClose}><X size={18} /></button></div>
    <div className="drawer-body">
      <div className="case-summary-grid"><div><small>Current stage</small><strong>{application.stage}</strong></div><div><small>Case status</small><strong>{application.status.replaceAll('_', ' ')}</strong></div><div><small>Owner queue</small><strong>{application.owner_role.replaceAll('_', ' ') || 'Completed'}</strong></div><div><small>Workflow</small><strong>{application.template} <em>v{application.template_version}</em></strong></div></div>
      <section className="drawer-section"><div className="section-title"><h3>Clock-aware SLA</h3><span>{Math.floor(total / 3600)}h total business time</span></div><div className="sla-bar">{(sla?.segments ?? []).map((segment, index) => <div className={`sla-segment ${segment.holder.toLowerCase()}`} style={{ flex: Math.max(0.1, segment.ended_at ? 1 : 1.4) }} key={`${segment.started_at}-${index}`} title={`${segment.holder} · ${segment.stage}`} />)}</div><div className="sla-legend">{Object.entries(sla?.totals_seconds ?? {}).map(([holder, seconds]) => <span key={holder}><i className={`legend-dot ${holder.toLowerCase()}`} />{holder.replaceAll('_', ' ')} · {Math.floor(seconds / 3600)}h</span>)}</div></section>
      <section className="drawer-section"><div className="section-title"><h3>Deficiency observations</h3><span>{observations.length} records</span></div>{observations.length ? observations.map((item) => <div className="observation" key={item.id}><div><strong>{item.category}</strong><span className={`status-chip ${item.status.toLowerCase()}`}>{item.status}</span></div><p>{item.remarks}</p>{item.response && <small>Institution response: {item.response}</small>}</div>) : <p className="muted small">No observations recorded.</p>}</section>
      <section className="drawer-section"><div className="section-title"><h3>Timeline</h3><span>{timeline.length} events</span></div>{timeline.map((item) => <div className="timeline-row" key={item.id}><i /><div><strong>{item.action.replaceAll('_', ' ')}</strong>{item.reason && <span>{item.reason}</span>}<small>{new Date(item.occurred_at).toLocaleString()}</small></div></div>)}</section>
      <section className="drawer-section action-section"><h3>Available actions</h3>
        {application.stage === 'SCRUTINY' && canScrutinize && <div className="action-card"><label htmlFor="deficiency-reason">Issue a deficiency or complete scrutiny</label><textarea id="deficiency-reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Add a reason for the deficiency / return" /><div className="action-buttons"><button className="button button-secondary" disabled={!reason.trim() || addDeficiency.isPending} onClick={() => addDeficiency.mutate()}>Issue deficiency</button><button className="button button-primary" disabled={mutate.isPending || application.open_deficiencies > 0} onClick={() => mutate.mutate({ event: 'COMPLETE_SCRUTINY', text: '' })}>Complete scrutiny</button></div></div>}
        {application.stage === 'SCRUTINY' && isApplicant && openObservation && <div className="action-card"><label htmlFor="response-reason">Respond to the open deficiency</label><textarea id="response-reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Describe the synthetic evidence submitted" /><button className="button button-primary" disabled={!reason.trim() || mutate.isPending} onClick={() => mutate.mutate({ event: 'SUBMIT_RESPONSE', text: reason })}>Submit response</button></div>}
        {application.stage === 'EVC' && canCoordinate && <div className="action-buttons"><button className="button button-secondary" onClick={() => mutate.mutate({ event: 'CONFIRM_VISIT', text: '' })}>Confirm visit</button><button className="button button-secondary" onClick={() => mutate.mutate({ event: 'RECORD_EVC_REPORT', text: '' })}>Record EVC report</button><button className="button button-primary" onClick={() => mutate.mutate({ event: 'COMPLETE_EVC', text: '' })}>Complete EVC</button></div>}
        {(canScrutinize || canCoordinate) && <LetterGenerator applicationId={application.id} letterType={application.stage === 'EVC' ? 'evc_schedule' : 'deficiency_notice'} />}
        {notice && <div className={`inline-notice ${notice.toLowerCase().includes('could not') || notice.toLowerCase().includes('cannot') || notice.toLowerCase().includes('required') ? 'notice-error' : ''}`}>{notice}</div>}
        {!canScrutinize && !isApplicant && !canCoordinate && <p className="muted small">This role has read-only access to workflow actions.</p>}
      </section>
    </div>
  </section></div>
}

type LetterRecord = { id: number; reference_no: string; letter_type: string; verify_token: string; sha256: string; status: string; issued_at: string; verify_url: string; download_url: string }

function LetterGenerator({ applicationId, letterType }: {applicationId: number; letterType: string}) {
  const queryClient = useQueryClient()
  const [letter, setLetter] = useState<LetterRecord | null>(null)
  const [error, setError] = useState('')
  const generate = useMutation({
    mutationFn: () => api<LetterRecord>('/api/v1/letters', { method: 'POST', body: JSON.stringify({ application_id: applicationId, letter_type: letterType }) }),
    onSuccess: async (result) => { setLetter(result); setError(''); await queryClient.invalidateQueries({ queryKey: ['letters'] }) },
    onError: (reason) => setError(reason instanceof Error ? reason.message : 'Could not generate letter'),
  })
  const download = async () => {
    if (!letter) return
    const token = localStorage.getItem('flowwise_token')
    const response = await fetch(letter.download_url, { headers: { Authorization: `Bearer ${token}` } })
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url; anchor.download = `${letter.reference_no}.pdf`; anchor.click()
    URL.revokeObjectURL(url)
  }
  return <div className="action-card letter-card"><label>Generate a verifiable {letterType.replaceAll('_', ' ')}</label>
    <button className="button button-secondary" disabled={generate.isPending} onClick={() => generate.mutate()}><Fingerprint size={15} />{generate.isPending ? 'Rendering PDF…' : 'Generate letter + QR'}</button>
    {error && <div className="inline-notice notice-error">{error}</div>}
    {letter && <div className="letter-result"><div><strong>{letter.reference_no}</strong><small>SHA-256 {letter.sha256.slice(0, 20)}…</small></div><div className="letter-result-actions"><button className="button button-primary" onClick={download}><FileText size={14} /> Download PDF</button><a className="button button-ghost" href={`/verify/${letter.verify_token}`} target="_blank" rel="noreferrer"><ShieldCheck size={14} /> Open verify page</a></div></div>}
  </div>
}

function InboxPage() {
  const { data = [], isLoading } = useQuery({ queryKey: ['inbox'], queryFn: () => api<Array<{application: Application; score: number; factors: Record<string, number>}>>('/api/v1/inbox') })
  return <><PageHeading eyebrow="EXPLAINABLE PRIORITY · FR-15" title="Action inbox" description="A deterministic view of the next actions, with the factors behind each score." />
    <section className="panel"><div className="panel-heading"><div><h2>Ranked work items</h2><p>Priority weights are demo placeholders and can be tuned by an administrator.</p></div><span className="count-chip">{data.length} items</span></div>{isLoading ? <Loading /> : data.length ? <div className="inbox-list">{data.slice(0, 30).map((item) => <Link className="inbox-row" to={`/cases?case=${item.application.id}`} key={item.application.id}><div className="score-ring">{Math.round(item.score * 100)}</div><div className="inbox-main"><strong>{item.application.reference_no} <span className={`stage-pill stage-${item.application.stage.toLowerCase()}`}>{item.application.stage}</span></strong><span>{item.application.institution} · {item.application.owner_role.replaceAll('_', ' ')}</span><div className="factor-list">{Object.entries(item.factors).map(([name, value]) => <span key={name}>{name.replaceAll('_', ' ')} <b>{value.toFixed(2)}</b></span>)}</div></div><ChevronRight size={18} /></Link>)}</div> : <EmptyState title="Inbox is clear" detail="No pending actions exist in your visible scope." />}</section>
  </>
}

type PlanMetrics = {scheduled_count: number; priority_weighted_ageing: number; total_travel_km: number; workload_spread: number}
type PlannerPlan = {
  plan_id: number
  solver_status: string
  assignments: Array<{case: string; scheduled: boolean; visit_date?: string; panel?: string[]; visit_mode?: string; panel_size?: number; reason: string; excluded_experts?: Array<{expert: string; reason: string}>}>
  scheduled_count: number
  baseline: PlanMetrics
  metrics: PlanMetrics
  notice: string
}

function PlannerPage() {
  const [plan, setPlan] = useState<PlannerPlan | null>(null)
  const [error, setError] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const user = useCurrentUser()
  const { data: queue = [] } = useQuery({ queryKey: ['evc-queue'], queryFn: () => api<Application[]>('/api/v1/evc/queue') })
  const run = useMutation({ mutationFn: () => api<PlannerPlan>('/api/v1/evc/plans', { method: 'POST', body: '{}' }), onSuccess: (result) => { setPlan(result); setConfirmed(false); setError('') }, onError: (reason) => setError(reason instanceof Error ? reason.message : 'Planner could not run') })
  const confirm = useMutation({
    mutationFn: () => api<{confirmed_count: number}>(`/api/v1/evc/plans/${plan?.plan_id}/confirm`, { method: 'POST', body: '{}' }),
    onSuccess: (result) => { setConfirmed(true); setError(`${result.confirmed_count} visits confirmed. Simulated notifications are in the outbox.`) },
    onError: (reason) => setError(reason instanceof Error ? reason.message : 'Plan confirmation failed'),
  })
  const canConfirm = ['EVC_COORDINATOR', 'SYSTEM_ADMIN'].includes(user?.role ?? '')
  return <><PageHeading eyebrow="EXPERT VISIT COMMITTEE · FR-04 / FR-13" title="EVC planner" description="Review EVC-ready applications and create a synthetic, conflict-aware planning proposal." action={<div className="heading-actions">{plan && canConfirm && <button className="button button-secondary" disabled={confirmed || confirm.isPending || plan.scheduled_count === 0} onClick={() => confirm.mutate()}><Check size={15} />{confirmed ? 'Plan confirmed' : 'Confirm plan'}</button>}<button className="button button-primary" disabled={run.isPending} onClick={() => run.mutate()}><Sparkles size={15} />{run.isPending ? 'Planning…' : 'Run planner'}</button></div>} />
    <div className="planner-notice"><CalendarDays size={17} /><span><strong>Planning window · next 10 days</strong><small>Demo placeholder. The proposal is advisory; a coordinator must confirm all assignments.</small></span><span className="placeholder-tag">PLACEHOLDER</span></div>
    {error && <div className="error-box">{error}</div>}
    <div className="planner-grid"><section className="panel"><div className="panel-heading"><div><h2>Ready for planning</h2><p>{queue.length} cases · sorted by priority and age</p></div><span className="count-chip">{queue.length} cases</span></div><ApplicationsTable applications={queue.slice(0, 12)} /></section>
      <section className="panel plan-summary"><div className="panel-heading"><div><h2>Proposal comparison</h2><p>Same synthetic instance · {plan?.solver_status ?? 'awaiting solve'}</p></div></div>{plan ? <><div className="compare-metrics"><div><small>SAMPARK proposal</small><strong>{plan.metrics.scheduled_count}</strong><span>cases scheduled</span></div><div><small>Greedy baseline</small><strong>{plan.baseline.scheduled_count}</strong><span>cases scheduled</span></div></div><div className="plan-metric-list">{([['Priority-weighted age', 'priority_weighted_ageing', 'case-days'], ['Physical travel', 'total_travel_km', 'km'], ['Workload spread', 'workload_spread', 'visits']] as const).map(([label, key, unit]) => <div key={key}><span>{label}</span><strong>{plan.metrics[key].toLocaleString()} {unit}</strong><small>Baseline {plan.baseline[key].toLocaleString()}</small></div>)}</div><p className="muted small">{plan.notice}</p></> : <div className="empty-chart empty-chart-tall"><CalendarDays size={26} /><strong>No plan run yet</strong><span>Run the planner to review a deterministic, conflict-aware proposal.</span></div>}</section>
    </div>
    {error && <div className={error.includes('confirmed') ? 'inline-notice' : 'error-box'}>{error}</div>}
    {plan && <section className="panel table-panel"><div className="panel-heading"><div><h2>Proposed assignments</h2><p>Every assignment includes a reason; no case is automatically approved.</p></div><span className={`status-chip ${confirmed ? 'published' : 'proposed'}`}>{confirmed ? 'CONFIRMED' : 'PROPOSED'}</span></div><div className="table-scroll"><table><thead><tr><th>Application</th><th>Visit date</th><th>Mode</th><th>Panel</th><th>Validation reason</th></tr></thead><tbody>{plan.assignments.map((item) => <tr key={item.case}><td className="case-ref">{item.case}</td><td>{item.visit_date ?? 'Not scheduled'}</td><td>{item.visit_mode ?? '—'}</td><td>{item.panel?.join(', ') ?? '—'}</td><td>{item.reason}{item.excluded_experts?.length ? <details className="excluded-details"><summary>Excluded experts ({item.excluded_experts.length})</summary>{item.excluded_experts.map((expert) => <span key={expert.expert}>{expert.expert}: {expert.reason}</span>)}</details> : null}</td></tr>)}</tbody></table></div></section>}
  </>
}

function CompliancePage() {
  const user = useCurrentUser()
  const canReview = ['COMPLIANCE_OFFICER', 'SYSTEM_ADMIN'].includes(user?.role ?? '')
  const { data = [] } = useQuery({ queryKey: ['undertakings'], queryFn: () => api<Array<{id: number; title: string; institution: string; due_at: string; status: string; source: string}>>('/api/v1/undertakings') })
  return <><PageHeading eyebrow="OBLIGATION INTELLIGENCE · FR-10" title="Obligation intelligence" description="AI reads approval letters, lease deeds and EVC reports and proposes obligations with a cited source page and verbatim quote. Officers confirm every item." />
    <ObligationWorkspace canReview={canReview} />
    <section className="panel table-panel"><div className="panel-heading"><div><h2>Compliance register</h2><p>Only officer-confirmed candidates enter this register, each with provenance.</p></div><span className="count-chip">{data.length} records</span></div>
      <div className="table-scroll"><table><thead><tr><th>Commitment</th><th>Institution</th><th>Due date</th><th>Status</th><th>Provenance</th></tr></thead><tbody>{data.map((row) => <tr key={row.id}><td className="case-ref">{row.title}</td><td>{row.institution}</td><td>{new Date(row.due_at).toLocaleDateString()}</td><td><span className={`status-chip ${row.status.toLowerCase()}`}>{row.status.replaceAll('_', ' ')}</span></td><td><span className="source-tag">{row.source}</span></td></tr>)}</tbody></table></div>
    </section>
  </>
}

function ObligationWorkspace({ canReview }: {canReview: boolean}) {
  const queryClient = useQueryClient()
  const [activeDoc, setActiveDoc] = useState<number | null>(null)
  const [notice, setNotice] = useState('')
  const [showUpload, setShowUpload] = useState(false)
  const { data: documents = [], isLoading } = useQuery({ queryKey: ['documents'], queryFn: () => api<DocumentSummary[]>('/api/v1/documents') })
  const { data: candidates = [] } = useQuery({
    queryKey: ['candidates', activeDoc],
    queryFn: () => api<Candidate[]>(`/api/v1/documents/${activeDoc}/candidates`),
    enabled: activeDoc !== null,
  })
  const extract = useMutation({
    mutationFn: (docId: number) => api<{run: {candidates_total: number; candidates_discarded: number; latency_ms: number}}>(`/api/v1/documents/${docId}/extract`, { method: 'POST', body: '{}' }),
    onSuccess: async (result, docId) => { setActiveDoc(docId); setNotice(`Extracted ${result.run.candidates_total} grounded candidate(s) in ${result.run.latency_ms}ms · ${result.run.candidates_discarded} discarded for failing the quote check.`); await queryClient.invalidateQueries({ queryKey: ['candidates', docId] }); await queryClient.invalidateQueries({ queryKey: ['documents'] }) },
    onError: (reason) => setNotice(reason instanceof Error ? reason.message : 'Extraction failed'),
  })
  const decide = useMutation({
    mutationFn: ({ id, action, edit }: {id: number; action: 'accept' | 'reject'; edit?: {description?: string; due_date?: string}}) => api(`/api/v1/candidates/${id}/${action}`, { method: 'POST', body: JSON.stringify(edit ?? {}) }),
    onSuccess: async (_result, variables) => { setNotice(variables.action === 'accept' ? 'Obligation confirmed and added to the register with provenance.' : 'Candidate rejected. It never enters the register.'); await queryClient.invalidateQueries({ queryKey: ['candidates', activeDoc] }); await queryClient.invalidateQueries({ queryKey: ['documents'] }); await queryClient.invalidateQueries({ queryKey: ['undertakings'] }) },
    onError: (reason) => setNotice(reason instanceof Error ? reason.message : 'Could not record decision'),
  })
  const pending = candidates.filter((item) => item.status === 'PENDING')
  const reviewed = candidates.filter((item) => item.status !== 'PENDING')
  const grounded = candidates.length

  return <div className="obligation-workspace">
    <div className="obligation-layout">
      <section className="panel document-panel">
        <div className="panel-heading"><div><h2>Documents</h2><p>Synthetic letters with a text layer</p></div>{canReview && <button className="button button-secondary" onClick={() => setShowUpload(true)}><FileText size={15} /> Upload</button>}</div>
        {isLoading ? <Loading /> : documents.map((doc) => <button key={doc.id} className={`document-row ${doc.id === activeDoc ? 'selected' : ''}`} onClick={() => setActiveDoc(doc.id)}>
          <span className="document-icon"><FileText size={17} /></span>
          <span className="document-main"><strong>{doc.filename}</strong><small>{doc.doc_type.replaceAll('_', ' ')} · {doc.doc_date ?? 'no date'} · {doc.pages}p</small></span>
          <span className="document-meta">{doc.accepted_candidates > 0 && <span className="status-chip compliant">{doc.accepted_candidates} confirmed</span>}{doc.pending_candidates > 0 && <span className="status-chip proposed">{doc.pending_candidates} to review</span>}<ChevronRight size={15} /></span>
        </button>)}
      </section>

      <section className="panel review-panel">
        <div className="panel-heading"><div><h2>Candidate review</h2><p>{activeDoc ? `${grounded} grounded candidate(s)` : 'Select a document to begin'}</p></div>{activeDoc && canReview && <button className="button button-primary" disabled={extract.isPending} onClick={() => extract.mutate(activeDoc)}><Sparkles size={15} />{extract.isPending ? 'Reading…' : 'Run extraction'}</button>}</div>
        {notice && <div className="inline-notice">{notice}</div>}
        {!activeDoc && <div className="empty-chart empty-chart-tall"><Sparkles size={26} /><strong>No document selected</strong><span>Pick a document, then run extraction to see source-cited obligation candidates.</span></div>}
        {activeDoc && candidates.length === 0 && <div className="empty-chart empty-chart-tall"><Sparkles size={26} /><strong>No candidates yet</strong><span>Run extraction to propose obligations. Each candidate must quote verbatim text from the page.</span></div>}
        {pending.map((item) => <CandidateCard key={item.id} item={item} canReview={canReview} onDecide={(action, edit) => decide.mutate({ id: item.id, action, edit })} busy={decide.isPending} />)}
        {reviewed.length > 0 && <div className="reviewed-group"><span className="nav-heading">Reviewed · {reviewed.length}</span>{reviewed.map((item) => <div key={item.id} className={`candidate-reviewed ${item.status.toLowerCase()}`}><span className={`status-chip ${item.status === 'ACCEPTED' ? 'compliant' : 'coral'}`}>{item.status}</span><strong>{item.description}</strong>{item.edited && <span className="source-tag">edited</span>}<small>p.{item.source_page}</small></div>)}</div>}
      </section>
    </div>
    {showUpload && <UploadModal onClose={() => setShowUpload(false)} onUploaded={async () => { setShowUpload(false); await queryClient.invalidateQueries({ queryKey: ['documents'] }) }} />}
  </div>
}

function CandidateCard({ item, canReview, onDecide, busy }: {item: Candidate; canReview: boolean; onDecide: (action: 'accept' | 'reject', edit?: {description?: string; due_date?: string}) => void; busy: boolean}) {
  const [editing, setEditing] = useState(false)
  const [description, setDescription] = useState(item.description)
  const [dueDate, setDueDate] = useState(item.due_date ?? '')
  const confidencePct = Math.round(item.confidence * 100)
  return <article className="candidate-card">
    <div className="candidate-top">
      <div><span className={`candidate-kind ${item.kind}`}>{item.kind === 'validity' ? 'VALIDITY FIELD' : item.category.replaceAll('_', ' ')}</span><span className="candidate-party">{item.responsible_party.replaceAll('_', ' ')}</span></div>
      <div className="confidence-badge" title="Extractor confidence"><i style={{ width: `${confidencePct}%` }} /><b>{confidencePct}%</b></div>
    </div>
    {editing ? <textarea className="candidate-edit" value={description} onChange={(e) => setDescription(e.target.value)} /> : <h3 className="candidate-desc">{item.description}</h3>}
    <div className="candidate-meta">
      {item.due_date && <span><CalendarDays size={13} /> Due {new Date(item.due_date).toLocaleDateString()}</span>}
      {item.due_expression && <span className="source-tag">{item.due_expression}</span>}
      {item.field_value && <span><BadgeCheck size={13} /> {item.field_name?.replaceAll('_', ' ')}: {item.field_value}</span>}
    </div>
    {editing && <label className="candidate-due-edit">Due date <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} /></label>}
    <blockquote className="candidate-quote"><span className="quote-label"><BookOpen size={13} /> Source · page {item.source_page}</span>"{item.source_quote}"</blockquote>
    {canReview && <div className="candidate-actions">
      {editing ? <>
        <button className="button button-primary" disabled={busy} onClick={() => onDecide('accept', { description, due_date: dueDate || undefined })}><Check size={15} /> Confirm edited</button>
        <button className="button button-ghost" onClick={() => setEditing(false)}>Cancel</button>
      </> : <>
        <button className="button button-primary" disabled={busy} onClick={() => onDecide('accept')}><Check size={15} /> Accept</button>
        <button className="button button-secondary" disabled={busy} onClick={() => setEditing(true)}>Edit</button>
        <button className="button button-ghost" disabled={busy} onClick={() => onDecide('reject')}><X size={15} /> Reject</button>
      </>}
    </div>}
    {!canReview && <p className="muted small">Read-only. Only a compliance officer can confirm candidates.</p>}
  </article>
}

function UploadModal({ onClose, onUploaded }: {onClose: () => void; onUploaded: () => void}) {
  const [filename, setFilename] = useState('uploaded_letter.txt')
  const [docType, setDocType] = useState('approval_letter')
  const [docDate, setDocDate] = useState('2026-10-15')
  const [text, setText] = useState('SYNTHETIC APPROVAL LETTER.\nDate of issue: 2026-10-15.\nThe institution shall submit the registered lease deed for the permanent campus within 90 days of issue.\nThe institution shall submit a valid fire safety certificate within 60 days of issue.\nThe approved lease is valid up to 2035-12-31.')
  const [error, setError] = useState('')
  const upload = useMutation({
    mutationFn: () => api<DocumentSummary>('/api/v1/documents', { method: 'POST', body: JSON.stringify({ filename, doc_type: docType, doc_date: docDate || null, text }) }),
    onSuccess: onUploaded,
    onError: (reason) => setError(reason instanceof Error ? reason.message : 'Upload failed'),
  })
  return <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}><section className="case-drawer upload-drawer">
    <div className="drawer-heading"><div><span className="eyebrow">OBLIGATION INTELLIGENCE</span><h2>Add a document</h2><p>Paste synthetic document text. No file leaves this prototype; extraction is deterministic and offline.</p></div><button className="icon-button" aria-label="Close" onClick={onClose}><X size={18} /></button></div>
    <div className="drawer-body">
      <label>File name<input value={filename} onChange={(e) => setFilename(e.target.value)} /></label>
      <div className="upload-row">
        <label>Document type<select value={docType} onChange={(e) => setDocType(e.target.value)}><option value="approval_letter">Approval letter</option><option value="lease_deed">Lease deed</option><option value="evc_report">EVC report</option><option value="deficiency_letter">Deficiency letter</option></select></label>
        <label>Document date<input type="date" value={docDate} onChange={(e) => setDocDate(e.target.value)} /></label>
      </div>
      <label>Document text (use a form feed to separate pages)<textarea className="upload-text" value={text} onChange={(e) => setText(e.target.value)} rows={10} /></label>
      {error && <div className="error-box"><AlertTriangle size={16} />{error}</div>}
      <div className="action-buttons"><button className="button button-primary" disabled={upload.isPending || text.length < 10} onClick={() => upload.mutate()}><FileText size={15} />{upload.isPending ? 'Uploading…' : 'Add document'}</button><button className="button button-ghost" onClick={onClose}>Cancel</button></div>
      <p className="muted small">Content is synthetic demo data. The extractor never sends text to an external provider in this build.</p>
    </div>
  </section></div>
}

function OutboxPage() {
  const { data = [], isLoading } = useQuery({ queryKey: ['outbox'], queryFn: () => api<Array<{id: number; entity_id: string; channel: string; subject: string; body: string; status: string; created_at: string}>>('/api/v1/notifications') })
  return <><PageHeading eyebrow="SIMULATED DELIVERY · FR-07" title="Notification outbox" description="Review in-app notices and simulated delivery events. No email or SMS leaves this prototype." />
    <div className="simulation-warning"><Bell size={17} /><div><strong>Simulated outbox only.</strong><span>Messages are stored locally for the demo; external channels are not configured.</span></div></div>
    <section className="panel"><div className="panel-heading"><div><h2>Recent notifications</h2><p>System-generated demo messages</p></div><span className="count-chip">{data.length} messages</span></div>{isLoading ? <Loading /> : data.length ? <div className="outbox-list">{data.map((item) => <article className="outbox-item" key={item.id}><div className="outbox-icon"><Bell size={16} /></div><div><div className="outbox-item-top"><strong>{item.subject}</strong><span className="source-tag">{item.channel.replaceAll('_', ' ')}</span></div><p>{item.body}</p><small>{item.entity_id} · {new Date(item.created_at).toLocaleString()}</small></div><span className="status-chip proposed">{item.status}</span></article>)}</div> : <EmptyState title="Outbox is empty" detail="Confirm a synthetic EVC plan to generate a demo notification." />}</section>
  </>
}

type SimulationResult = {
  data_source: string
  notice: string
  assumptions: {
    replications: number
    working_days: number
    seed: number
    additional_scrutiny_officers: Record<string, number>
  }
  baseline: Record<string, Record<string, {p50_hours: number; p90_hours: number; mean_backlog: number}>>
  scenario: Record<string, Record<string, {p50_hours: number; p90_hours: number; mean_backlog: number}>>
}

function SimulatorPage() {
  const [extraOfficers, setExtraOfficers] = useState(2)
  const [result, setResult] = useState<SimulationResult | null>(null)
  const [error, setError] = useState('')
  const mutation = useMutation({
    mutationFn: () => api<SimulationResult>('/api/v1/simulations', {
      method: 'POST',
      body: JSON.stringify({ additional_scrutiny_officers: { NR: extraOfficers }, replications: 30, working_days: 120, seed: 42 }),
    }),
    onSuccess: (value) => { setResult(value); setError('') },
    onError: (reason) => setError(reason instanceof Error ? reason.message : 'Simulation could not run'),
  })
  const before = result?.baseline.NR.SCRUTINY
  const after = result?.scenario.NR.SCRUTINY
  return <><PageHeading eyebrow="CAPACITY WHAT-IF · FR-12" title="Capacity simulator" description="Compare queue outcomes under stated synthetic staffing and service-time assumptions." action={<button className="button button-primary" disabled={mutation.isPending} onClick={() => mutation.mutate()}><Activity size={15} />{mutation.isPending ? 'Running 30 replications…' : 'Run simulation'}</button>} />
    <div className="simulation-warning"><AlertTriangle size={17} /><div><strong>Simulation under stated assumptions, not a forecast.</strong><span>Service times and arrivals are synthetic; use this only to compare scenarios.</span></div></div>
    <section className="panel scenario-controls"><div><span className="eyebrow">SCENARIO INPUT</span><h2>Increase scrutiny capacity in NR</h2><p>Baseline staffing is 2 scrutiny officers in NR and 3 in each other region.</p></div><label>Additional officers <input type="number" min={0} max={20} value={extraOfficers} onChange={(event) => setExtraOfficers(Number(event.target.value))} /></label></section>
    {error && <div className="error-box">{error}</div>}
    {result ? <><div className="metrics-grid simulator-metrics"><SimulationMetric title="NR scrutiny · p90 time in system" baseline={before?.p90_hours ?? 0} scenario={after?.p90_hours ?? 0} suffix="business hours" /><SimulationMetric title="NR scrutiny · mean backlog" baseline={before?.mean_backlog ?? 0} scenario={after?.mean_backlog ?? 0} suffix="cases" /><SimulationMetric title="NR EVC · p90 time in system" baseline={result.baseline.NR.EVC.p90_hours} scenario={result.scenario.NR.EVC.p90_hours} suffix="business hours" /><SimulationMetric title="NR EVC · mean backlog" baseline={result.baseline.NR.EVC.mean_backlog} scenario={result.scenario.NR.EVC.mean_backlog} suffix="cases" /></div>
      <section className="panel simulation-table"><div className="panel-heading"><div><h2>Region and stage outcomes</h2><p>Baseline versus adjusted scrutiny staffing · {result.assumptions.replications} replications</p></div><span className="source-tag">{result.data_source}</span></div><div className="table-scroll"><table><thead><tr><th>Region</th><th>Stage</th><th>Baseline p90</th><th>Scenario p90</th><th>Baseline backlog</th><th>Scenario backlog</th></tr></thead><tbody>{Object.entries(result.baseline).flatMap(([region, stages]) => Object.entries(stages).map(([stage, baseline]) => { const changed = result.scenario[region][stage]; return <tr key={`${region}-${stage}`}><td>{region}</td><td>{stage}</td><td>{baseline.p90_hours.toFixed(1)}h</td><td>{changed.p90_hours.toFixed(1)}h</td><td>{baseline.mean_backlog}</td><td>{changed.mean_backlog}</td></tr> }))}</tbody></table></div></section>
      <p className="simulation-assumptions">Source: {result.data_source} · {result.assumptions.working_days} working days · fixed seed {result.assumptions.seed} · Poisson arrivals at 1.2 cases/region/day · lognormal service times.</p>
    </> : <section className="panel simulator-empty"><Activity size={26} /><strong>Run a scenario to see the comparison</strong><span>Results include backlog and time-in-system percentiles across regions and stages.</span></section>}
  </>
}

function SimulationMetric({ title, baseline, scenario, suffix }: {title: string; baseline: number; scenario: number; suffix: string}) {
  const change = baseline ? Math.round((scenario - baseline) / baseline * 100) : 0
  const improved = change < 0
  return <div className="metric-card simulation-metric"><div className="metric-top"><span>{title}</span><i>{improved ? <ArrowDownRight size={17} /> : <ArrowUpRight size={17} />}</i></div><div className="simulation-value">{scenario.toFixed(1)}<small> {suffix}</small></div><div className="metric-note">Baseline {baseline.toFixed(1)} · <b className={improved ? 'improved' : ''}>{change > 0 ? '+' : ''}{change}%</b></div></div>
}

type Stage = { code: string; role?: string; sla_hours?: number; type: string }
type Transition = { from: string; to: string; event: string; when?: unknown; requires_reason?: boolean }
type Graph = { start: string; stages: Stage[]; transitions: Transition[] }
type WorkflowDef = { id: number; template_code: string; version: number; status: string; graph: Graph; proposed_by: string | null; approved_by: string | null; reject_reason: string | null }
type ValidationResult = { valid: boolean; errors: string[]; warnings: string[]; checks: Array<{label: string; ok: boolean}> }
type DryRunResult = { ok: boolean; path: string[]; message: string }

const ROLE_OPTIONS = ['SCRUTINY_OFFICER', 'EVC_COORDINATOR', 'SAC_SHC_MEMBER', 'REGIONAL_OFFICER', 'COMPLIANCE_OFFICER', 'SYSTEM_ADMIN']

function StudioPage() {
  const user = useCurrentUser()
  const queryClient = useQueryClient()
  const isAdmin = user?.role === 'SYSTEM_ADMIN'
  const isApprover = user?.role === 'SECOND_APPROVER'
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [draft, setDraft] = useState<Graph | null>(null)
  const [templateCode, setTemplateCode] = useState('SCRUTINY_EVC')
  const [validation, setValidation] = useState<ValidationResult | null>(null)
  const [dryRun, setDryRun] = useState<DryRunResult | null>(null)
  const [notice, setNotice] = useState('')
  const { data: definitions = [] } = useQuery({ queryKey: ['definitions'], queryFn: () => api<WorkflowDef[]>('/api/v1/workflow-definitions') })
  const selected = definitions.find((d) => d.id === selectedId) ?? definitions[0]
  const activeGraph = draft ?? selected?.graph

  const validate = useMutation({
    mutationFn: (graph: Graph) => api<{validation: ValidationResult; dry_run: DryRunResult}>('/api/v1/workflow-definitions/validate', { method: 'POST', body: JSON.stringify({ graph }) }),
    onSuccess: (result) => { setValidation(result.validation); setDryRun(result.dry_run); setNotice('') },
  })
  const submitDraft = useMutation({
    mutationFn: async (graph: Graph) => {
      const created = await api<WorkflowDef>('/api/v1/workflow-definitions', { method: 'POST', body: JSON.stringify({ template_code: templateCode, graph }) })
      return api<WorkflowDef>(`/api/v1/workflow-definitions/${created.id}/submit`, { method: 'POST', body: '{}' })
    },
    onSuccess: async (result) => { setNotice(`Version ${result.version} submitted for approval. A second approver must publish it.`); setDraft(null); await queryClient.invalidateQueries({ queryKey: ['definitions'] }); setSelectedId(result.id) },
    onError: (reason) => setNotice(reason instanceof Error ? reason.message : 'Submit failed'),
  })
  const decide = useMutation({
    mutationFn: ({ id, action }: {id: number; action: 'publish' | 'reject'}) => api(`/api/v1/workflow-definitions/${id}/${action}`, { method: 'POST', body: action === 'reject' ? JSON.stringify({ reason: 'Returned for revision in demo' }) : '{}' }),
    onSuccess: async (_r, variables) => { setNotice(variables.action === 'publish' ? 'Published. New cases follow this version; in-flight cases keep their pinned version.' : 'Rejected and returned to the proposer.'); await queryClient.invalidateQueries({ queryKey: ['definitions'] }) },
    onError: (reason) => setNotice(reason instanceof Error ? reason.message : 'Action failed'),
  })

  const startEdit = () => {
    if (!selected) return
    setDraft(JSON.parse(JSON.stringify(selected.graph)))
    setTemplateCode(selected.template_code)
    setValidation(null); setDryRun(null); setNotice('')
  }
  const updateStageSla = (code: string, sla: number) => draft && setDraft({ ...draft, stages: draft.stages.map((s) => s.code === code ? { ...s, sla_hours: sla } : s) })
  const updateStageRole = (code: string, role: string) => draft && setDraft({ ...draft, stages: draft.stages.map((s) => s.code === code ? { ...s, role } : s) })

  return <><PageHeading eyebrow="VERSIONED WORKFLOWS · FR-14" title="Workflow studio" description="Build a stage combination, validate it, dry-run it on a synthetic case, and publish with a second approver. Cases pin their template version." action={selected && <span className={`status-chip ${selected.status === 'PUBLISHED' ? 'published' : 'proposed'}`}>{selected.status.replaceAll('_', ' ')}</span>} />
    {notice && <div className="inline-notice">{notice}</div>}
    <div className="studio-layout">
      <section className="panel template-list"><div className="panel-heading"><div><h2>Definitions</h2><p>Versioned workflow graphs</p></div><Workflow size={18} /></div>
        {definitions.map((def) => <button key={def.id} onClick={() => { setSelectedId(def.id); setDraft(null); setValidation(null); setDryRun(null) }} className={`template-option ${def.id === (selected?.id) ? 'selected' : ''}`}>
          <span className="template-icon"><Workflow size={17} /></span>
          <span><strong>{def.template_code.replaceAll('_', ' ')}</strong><small>v{def.version} · {def.graph.stages.length} stages · <span className={`status-chip ${def.status === 'PUBLISHED' ? 'published' : def.status === 'REJECTED' ? 'coral' : 'proposed'}`}>{def.status.replaceAll('_', ' ')}</span></small></span>
          <ChevronRight size={16} />
        </button>)}
      </section>

      <section className="panel studio-canvas">
        <div className="panel-heading"><div><h2>{(draft ? templateCode : selected?.template_code ?? '').replaceAll('_', ' ')}</h2><p>{draft ? 'Draft · edit SLA targets and roles, then validate' : `${selected?.status.replaceAll('_', ' ')} · proposed by ${selected?.proposed_by ?? '—'}${selected?.approved_by ? `, approved by ${selected.approved_by}` : ''}`}</p></div>{draft && <span className="placeholder-tag">EDITING DRAFT</span>}</div>

        <div className="workflow-flow"><div className="flow-start"><i /> START: {activeGraph?.start}</div>{activeGraph?.stages.map((stage, index) => <div className={`flow-stage ${stage.type === 'terminal' ? 'terminal' : ''}`} key={stage.code}>
          <span className="flow-step">{index + 1}</span><strong>{stage.code}</strong>
          {stage.type === 'terminal' ? <small>Terminal stage</small> : draft ? <div className="stage-edit"><label>Role<select value={stage.role} onChange={(e) => updateStageRole(stage.code, e.target.value)}>{ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r.replaceAll('_', ' ')}</option>)}</select></label><label>SLA (h)<input type="number" min={1} value={stage.sla_hours ?? 0} onChange={(e) => updateStageSla(stage.code, Number(e.target.value))} /></label></div> : <small>{stage.role?.replaceAll('_', ' ')} · {stage.sla_hours}h</small>}
          {index < activeGraph.stages.length - 1 && <span className="flow-arrow"><i /></span>}
        </div>)}</div>

        <div className="studio-actions">
          {!draft && isAdmin && selected && <button className="button button-secondary" onClick={startEdit}><Settings2 size={15} /> New version from this</button>}
          {draft && <><button className="button button-secondary" onClick={() => activeGraph && validate.mutate(activeGraph)}><Check size={15} /> Validate & dry-run</button>
          <button className="button button-primary" disabled={!validation?.valid || submitDraft.isPending} onClick={() => activeGraph && submitDraft.mutate(activeGraph)}><ShieldCheck size={15} /> Submit for approval</button>
          <button className="button button-ghost" onClick={() => { setDraft(null); setValidation(null); setDryRun(null) }}>Cancel</button></>}
          {!draft && selected?.status === 'SUBMITTED_FOR_APPROVAL' && (isApprover || isAdmin) && <><button className="button button-primary" disabled={decide.isPending} onClick={() => decide.mutate({ id: selected.id, action: 'publish' })}><ShieldCheck size={15} /> Approve & publish</button><button className="button button-ghost" disabled={decide.isPending} onClick={() => decide.mutate({ id: selected.id, action: 'reject' })}><X size={15} /> Reject</button></>}
        </div>

        {validation && <div className="validation-panel">
          <div className={`validation-result ${validation.valid ? 'valid' : 'invalid'}`}>{validation.valid ? <Check size={16} /> : <AlertTriangle size={16} />}<span><strong>{validation.valid ? 'Graph is valid' : `${validation.errors.length} error(s)`}</strong>{dryRun && <span> · Dry-run: {dryRun.message}</span>}</span></div>
          <div className="validation-checks">{validation.checks.map((check) => <span key={check.label} className={check.ok ? 'check-ok' : 'check-fail'}>{check.ok ? <Check size={13} /> : <X size={13} />}{check.label}</span>)}</div>
          {validation.errors.map((error) => <p className="validation-error" key={error}><AlertTriangle size={13} /> {error}</p>)}
          {dryRun && dryRun.path.length > 0 && <p className="dryrun-path">Path walked: {dryRun.path.join(' → ')}</p>}
        </div>}
        {selected?.reject_reason && !draft && <p className="validation-error"><AlertTriangle size={13} /> Rejected: {selected.reject_reason}</p>}
        <p className="studio-footnote">Validation enforces reachability, terminal states, role coverage and the predicate whitelist. Publication is maker-checker: the approver must differ from the proposer.</p>
      </section>
    </div>
  </>
}

function AuditPage() {
  const queryClient = useQueryClient()
  const [verification, setVerification] = useState<{valid: boolean; first_bad_index: number | null; checked: number} | null>(null)
  const [error, setError] = useState('')
  const { data: events = [], isLoading } = useQuery({ queryKey: ['audit'], queryFn: () => api<Array<{id: number; action: string; entity_type: string; entity_id: string; occurred_at: string; reason: string | null; hash: string}>>('/api/v1/audit/events') })
  const verify = async () => {
    try { setVerification(await api('/api/v1/audit/verify')); setError('') } catch (reason) { setError(reason instanceof Error ? reason.message : 'Verification failed') }
  }
  return <><PageHeading eyebrow="TRUST LAYER · FR-17" title="Audit trail" description="Review append-only case activity and verify the SHA-256 hash chain." action={<button className="button button-primary" onClick={verify}><ShieldCheck size={15} /> Verify chain</button>} />
    {verification && <div className={`verification-result ${verification.valid ? 'valid' : 'invalid'}`}><ShieldCheck size={19} /><div><strong>{verification.valid ? 'Audit chain verified' : `Tampering detected at event ${verification.first_bad_index}`}</strong><span>{verification.checked} event(s) checked. {verification.valid ? 'All hashes link to the genesis record.' : 'The stored event no longer matches its chained hash.'}</span></div></div>}
    {error && <div className="error-box">{error}</div>}
    <LettersPanel />
    <section className="panel table-panel"><div className="panel-heading"><div><h2>Recent events</h2><p>Hash-chained material changes · latest 200</p></div><button className="icon-button" onClick={() => queryClient.invalidateQueries({ queryKey: ['audit'] })} aria-label="Refresh audit"><RefreshCw size={16} /></button></div>{isLoading ? <Loading /> : <div className="table-scroll"><table><thead><tr><th>Event</th><th>Entity</th><th>Reason</th><th>Timestamp</th><th>Fingerprint</th></tr></thead><tbody>{events.map((event) => <tr key={event.id}><td><strong>{event.action.replaceAll('_', ' ')}</strong><small className="cell-sub">#{event.id}</small></td><td>{event.entity_type} · {event.entity_id}</td><td>{event.reason ?? '—'}</td><td>{new Date(event.occurred_at).toLocaleString()}</td><td><code className="hash">{event.hash.slice(0, 16)}…</code></td></tr>)}</tbody></table></div>}</section>
    <div className="info-strip"><div className="info-icon"><AlertTriangle size={17} /></div><div><strong>Demo tamper control is destructive by design.</strong><span>Use the labelled demo-bar control to alter one audit row and demonstrate chain verification. Reset restores the synthetic chain.</span></div></div>
  </>
}

function LettersPanel() {
  const { data = [] } = useQuery({ queryKey: ['letters'], queryFn: () => api<LetterRecord[]>('/api/v1/letters') })
  if (!data.length) return <section className="panel"><div className="panel-heading"><div><h2>Generated letters</h2><p>QR-verifiable PDFs with a SHA-256 fingerprint</p></div><Fingerprint size={18} /></div><EmptyState title="No letters yet" detail="Open a case and generate a deficiency notice or EVC schedule to see verifiable letters here." /></section>
  return <section className="panel table-panel"><div className="panel-heading"><div><h2>Generated letters</h2><p>QR-verifiable PDFs with a SHA-256 fingerprint</p></div><span className="count-chip">{data.length} letters</span></div>
    <div className="table-scroll"><table><thead><tr><th>Reference</th><th>Type</th><th>Status</th><th>Issued</th><th>Fingerprint</th><th>Verify</th></tr></thead><tbody>{data.map((letter) => <tr key={letter.id}><td className="case-ref">{letter.reference_no}</td><td>{letter.letter_type.replaceAll('_', ' ')}</td><td><span className={`status-chip ${letter.status === 'valid' ? 'compliant' : 'coral'}`}>{letter.status}</span></td><td>{new Date(letter.issued_at).toLocaleString()}</td><td><code className="hash">{letter.sha256.slice(0, 16)}…</code></td><td><a className="text-link" href={`/verify/${letter.verify_token}`} target="_blank" rel="noreferrer">Open <ChevronRight size={13} /></a></td></tr>)}</tbody></table></div>
  </section>
}

function RulesPage() {
  const { data = [], isLoading } = useQuery({ queryKey: ['rules'], queryFn: () => api<Array<{key: string; value: unknown; tag: string; version: number}>>('/api/v1/admin/rules') })
  return <><PageHeading eyebrow="ADMINISTRATION · PRD SECTION 6" title="Rules & traceability" description="Demo rule values are configurable assumptions, not official AICTE timelines." />
    <section className="panel table-panel"><div className="panel-heading"><div><h2>Configured demo rules</h2><p>Every value has an explicit provenance tag.</p></div><Settings2 size={18} /></div>{isLoading ? <Loading /> : <div className="table-scroll"><table><thead><tr><th>Rule</th><th>Configured value</th><th>Source tag</th><th>Version</th></tr></thead><tbody>{data.map((rule) => <tr key={rule.key}><td className="case-ref">{rule.key.replaceAll('_', ' ')}</td><td><code className="rule-value">{JSON.stringify(rule.value)}</code></td><td><span className={`source-tag ${rule.tag}`}>{rule.tag.replaceAll('_', ' ')}</span></td><td>{rule.version}</td></tr>)}</tbody></table></div>}</section>
    <div className="traceability-grid"><TraceItem tag="sourced_verify" title="Visit mode" description="Physical, online or hybrid visits are represented as sourced values pending handbook verification." /><TraceItem tag="placeholder" title="Workflow mappings & SLAs" description="Template mappings and demo stage targets are configurable assumptions; verify them with authorised stakeholders." /><TraceItem tag="sourced_verify" title="Appeal and review windows" description="Publicly sourced values remain unverified against the current Approval Process Handbook." /></div>
  </>
}

function TraceItem({ tag, title, description }: {tag: string; title: string; description: string}) {
  return <section className="panel trace-item"><span className={`source-tag ${tag}`}>{tag.replaceAll('_', ' ')}</span><h3>{title}</h3><p>{description}</p></section>
}

function Loading() {
  return <div className="loading-state"><span className="spinner" />Loading workspace data…</div>
}

function EmptyState({ title, detail }: {title: string; detail: string}) {
  return <div className="empty-state"><div><FileText size={20} /></div><strong>{title}</strong><span>{detail}</span></div>
}

function LoginRoute() {
  return localStorage.getItem('flowwise_token') ? <Navigate to="/" replace /> : <LoginPage />
}

export default function App() {
  return <Routes><Route path="/login" element={<LoginRoute />} /><Route path="/verify/:token" element={<VerifyPage />} /><Route path="/*" element={<AppShell />} /></Routes>
}

type VerifyResult = { found: boolean; letter_type?: string; reference_no?: string; issued_at?: string; status?: string; stored_sha256?: string; match?: boolean }

function VerifyPage() {
  const token = window.location.pathname.split('/verify/')[1] ?? ''
  const { data, isLoading, isError } = useQuery({
    queryKey: ['verify', token],
    queryFn: () => api<VerifyResult>(`/api/v1/verify/${token}`),
    retry: false,
  })
  const [match, setMatch] = useState<boolean | null>(null)
  const checkMatch = async () => {
    try { const result = await api<VerifyResult>(`/api/v1/verify/${token}/match`, { method: 'POST', body: '{}' }); setMatch(result.match ?? null) } catch { setMatch(false) }
  }
  return <main className="verify-page">
    <div className="verify-card">
      <div className="verify-brand"><span className="brand-mark"><Workflow size={20} /></span> SAMPARK · Document verification</div>
      {isLoading && <Loading />}
      {isError && <div className="verify-status invalid"><AlertTriangle size={30} /><h2>Not found</h2><p>No letter matches this verification code. It may be invalid or withdrawn.</p></div>}
      {data?.found && <>
        <div className={`verify-status ${data.status === 'valid' ? 'valid' : 'warn'}`}>{data.status === 'valid' ? <ShieldCheck size={30} /> : <AlertTriangle size={30} />}<h2>{data.status === 'valid' ? 'Valid document' : data.status}</h2><p>This verification code resolves to a genuine SAMPARK-issued letter.</p></div>
        <dl className="verify-facts">
          <div><dt>Document type</dt><dd>{data.letter_type?.replaceAll('_', ' ')}</dd></div>
          <div><dt>Reference</dt><dd>{data.reference_no}</dd></div>
          <div><dt>Issued</dt><dd>{data.issued_at ? new Date(data.issued_at).toLocaleString() : '—'}</dd></div>
          <div><dt>Status</dt><dd><span className={`status-chip ${data.status === 'valid' ? 'compliant' : 'coral'}`}>{data.status}</span></dd></div>
          <div><dt>Fingerprint</dt><dd><code className="hash">{data.stored_sha256?.slice(0, 24)}…</code></dd></div>
        </dl>
        <button className="button button-secondary" onClick={checkMatch}><Fingerprint size={15} /> Check stored file integrity</button>
        {match !== null && <div className={`inline-notice ${match ? '' : 'notice-error'}`}>{match ? 'The stored file matches its recorded SHA-256 fingerprint.' : 'The stored file does not match its fingerprint.'}</div>}
      </>}
      <p className="verify-foot">No personal or sensitive content is exposed on this page. Synthetic demo data for SIH 2026.</p>
    </div>
  </main>
}
