import { useEffect, useMemo, useState } from 'react'
import httpClient from '../lib/httpClient'

const initialForm = {
  patientHn: '',
  status: 'in-progress',
  classCode: 'AMB',
  periodStart: '',
  periodEnd: '',
  reason: '',
}

const CLASS_OPTIONS = [
  { code: 'AMB', label: 'AMB — Outpatient' },
  { code: 'IMP', label: 'IMP — Inpatient' },
  { code: 'EMER', label: 'EMER — Emergency' },
]

const STATUS_OPTIONS = ['planned', 'in-progress', 'finished', 'cancelled']

const STATUS_STYLES = {
  'in-progress': 'bg-blue-100 text-blue-700',
  finished: 'bg-green-100 text-green-700',
  planned: 'bg-yellow-100 text-yellow-700',
  cancelled: 'bg-rose-100 text-rose-700',
}

const CLASS_STYLES = {
  IMP: 'bg-purple-100 text-purple-700',
  AMB: 'bg-sky-100 text-sky-700',
  EMER: 'bg-red-100 text-red-700',
}

// HIS A is the data CONSUMER — encounters are owned/published by HIS B.
// Per interop requirements: HIS A can view but cannot mutate HIS B data.
// Flip to false to re-enable Create/Edit/Delete for admin/demo use.
const READ_ONLY = true

export default function Encounters() {
  const [encounters, setEncounters] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadEncounters() }, [])

  const sorted = useMemo(
    () => [...encounters].sort((a, b) => Number(a.id || 0) - Number(b.id || 0)),
    [encounters],
  )

  function parseEncounter(enc) {
    const classCode = enc.class?.[0]?.coding?.[0]?.code ?? 'AMB'
    const periodStart = (enc.actualPeriod?.start ?? enc.period?.start ?? '').slice(0, 16)
    const periodEnd = (enc.actualPeriod?.end ?? enc.period?.end ?? '').slice(0, 16)
    const reason = enc.reason?.[0]?.value?.[0]?.concept?.text ?? ''
    return {
      patientHn: enc.subject?.reference?.split('/').pop() ?? '',
      status: enc.status ?? 'in-progress',
      classCode,
      periodStart,
      periodEnd,
      reason,
    }
  }

  async function loadEncounters() {
    setLoading(true)
    setError(null)
    try {
      const res = await httpClient.get('/api/v1/fhir/Encounter')
      setEncounters(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Error loading encounters.')
    } finally {
      setLoading(false)
    }
  }

  // datetime-local returns "YYYY-MM-DDTHH:MM" — FHIR DateTime needs seconds + timezone offset
  function toFhirDt(val) {
    if (!val) return ''
    const withSeconds = val.length === 16 ? `${val}:00` : val
    // append Thailand offset if no timezone present
    return withSeconds.includes('+') || withSeconds.includes('Z') ? withSeconds : `${withSeconds}+07:00`
  }

  function buildPayload() {
    const classDisplay = CLASS_OPTIONS.find((c) => c.code === form.classCode)?.label.split(' — ')[1] ?? form.classCode
    const payload = {
      resourceType: 'Encounter',
      status: form.status,
      // FHIR R5: class is a list of CodeableConcept
      class: [
        { coding: [{ system: 'http://terminology.hl7.org/CodeSystem/v3-ActCode', code: form.classCode, display: classDisplay }] },
      ],
      subject: { reference: `Patient/${form.patientHn}` },
      // FHIR R5: actualPeriod replaces period
      // datetime-local gives "YYYY-MM-DDTHH:MM" — append ":00" so FHIR DateTime regex matches
      actualPeriod: { start: toFhirDt(form.periodStart) || new Date().toISOString() },
    }
    if (form.periodEnd) payload.actualPeriod.end = toFhirDt(form.periodEnd)
    // FHIR R5: reason uses value[].concept structure
    if (form.reason) payload.reason = [{ value: [{ concept: { text: form.reason } }] }]
    return payload
  }

  function openCreate() {
    setForm(initialForm)
    setSelectedId(null)
    setIsEditing(false)
    setModalOpen(true)
  }

  function openEdit(enc) {
    setForm(parseEncounter(enc))
    setSelectedId(enc.id)
    setIsEditing(true)
    setModalOpen(true)
  }

  async function handleSave(e) {
    e.preventDefault()
    setError(null)
    setSaving(true)
    try {
      const payload = buildPayload()
      if (isEditing && selectedId != null) {
        await httpClient.put(`/api/v1/fhir/Encounter/${encodeURIComponent(selectedId)}`, payload)
      } else {
        await httpClient.post('/api/v1/fhir/Encounter', payload)
      }
      setModalOpen(false)
      await loadEncounters()
    } catch (err) {
      const msg = err.response?.data?.detail ?? err.response?.data ?? err.message ?? 'Unable to save.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(enc) {
    if (!window.confirm(`Delete Encounter #${enc.id}?`)) return
    setError(null)
    try {
      await httpClient.delete(`/api/v1/fhir/Encounter/${encodeURIComponent(enc.id)}`)
      await loadEncounters()
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Unable to delete.')
    }
  }

  if (loading) return <p className="text-gray-500 text-sm">Loading encounters…</p>

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Encounters</h2>
          <p className="mt-2 text-sm text-slate-500">บันทึกการเข้ารับบริการ (OPD / IPD / ER)</p>
          {READ_ONLY && (
            <p className="mt-1 inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700 ring-1 ring-amber-200">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              Read-only · Published by HIS B
            </p>
          )}
        </div>
        {!READ_ONLY && (
          <button
            type="button"
            onClick={openCreate}
            className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            + New encounter
          </button>
        )}
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {String(error)}
        </div>
      )}

      <div className="overflow-x-auto rounded-3xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead className="bg-slate-50 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Patient</th>
              <th className="px-4 py-3">Class</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Period Start</th>
              <th className="px-4 py-3">Period End</th>
              <th className="px-4 py-3">Reason</th>
              {!READ_ONLY && <th className="px-4 py-3">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {sorted.map((enc) => {
              const classCode = enc.class?.[0]?.coding?.[0]?.code ?? '—'
              const patient = enc.subject?.reference ?? '—'
              const start = (enc.actualPeriod?.start ?? enc.period?.start)
                ? new Date(enc.actualPeriod?.start ?? enc.period?.start).toLocaleString('th-TH') : '—'
              const end = (enc.actualPeriod?.end ?? enc.period?.end)
                ? new Date(enc.actualPeriod?.end ?? enc.period?.end).toLocaleString('th-TH') : '—'
              const reason = enc.reason?.[0]?.value?.[0]?.concept?.text ?? '—'
              const encStatus = enc.status ?? '—'

              return (
                <tr key={enc.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-slate-500">{enc.id}</td>
                  <td className="px-4 py-3 font-medium text-slate-700">{patient}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${CLASS_STYLES[classCode] ?? 'bg-slate-100 text-slate-600'}`}>
                      {classCode}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${STATUS_STYLES[encStatus] ?? 'bg-slate-100 text-slate-600'}`}>
                      {encStatus}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 text-xs">{start}</td>
                  <td className="px-4 py-3 text-slate-600 text-xs">{end}</td>
                  <td className="px-4 py-3 text-slate-600 text-xs max-w-[180px] truncate">{reason}</td>
                  {!READ_ONLY && (
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(enc)}
                          className="rounded-2xl bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(enc)}
                          className="rounded-2xl bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-100"
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  )}
                </tr>
              )
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={READ_ONLY ? 7 : 8} className="px-4 py-8 text-center text-slate-400 text-sm">
                  No encounters found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {!READ_ONLY && modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 py-8">
          <div className="w-full max-w-2xl overflow-hidden rounded-[32px] bg-white shadow-2xl ring-1 ring-slate-200">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
              <div>
                <h3 className="text-xl font-semibold text-slate-900">
                  {isEditing ? 'Edit encounter' : 'New encounter'}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {isEditing ? 'แก้ไขข้อมูลการเข้ารับบริการ' : 'บันทึกการเข้ารับบริการใหม่'}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="rounded-full bg-slate-100 p-2 text-slate-600 transition hover:bg-slate-200"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSave} className="space-y-5 px-6 py-6">
              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  Patient HN
                  <input
                    required
                    value={form.patientHn}
                    onChange={(e) => setForm((p) => ({ ...p, patientHn: e.target.value }))}
                    placeholder="HN-0001"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Class
                  <select
                    value={form.classCode}
                    onChange={(e) => setForm((p) => ({ ...p, classCode: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  >
                    {CLASS_OPTIONS.map((c) => (
                      <option key={c.code} value={c.code}>{c.label}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  Status
                  <select
                    value={form.status}
                    onChange={(e) => setForm((p) => ({ ...p, status: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  >
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Reason (optional)
                  <input
                    value={form.reason}
                    onChange={(e) => setForm((p) => ({ ...p, reason: e.target.value }))}
                    placeholder="e.g. Follow-up diabetes"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  Period Start
                  <input
                    type="datetime-local"
                    value={form.periodStart}
                    onChange={(e) => setForm((p) => ({ ...p, periodStart: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Period End (optional)
                  <input
                    type="datetime-local"
                    value={form.periodEnd}
                    onChange={(e) => setForm((p) => ({ ...p, periodEnd: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
              </div>

              {error && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {String(error)}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="rounded-2xl border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="rounded-2xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
                >
                  {saving ? 'Saving…' : isEditing ? 'Save changes' : 'Create encounter'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
