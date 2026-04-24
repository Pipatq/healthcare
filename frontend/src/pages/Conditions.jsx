import { useEffect, useMemo, useState } from 'react'
import httpClient from '../lib/httpClient'

const initialForm = {
  patientHn: '',
  clinicalStatus: 'active',
  icd10Code: '',
  icd10Display: '',
  onsetDate: '',
  note: '',
}

const CLINICAL_STATUS_OPTIONS = ['active', 'inactive', 'resolved']

const CLINICAL_STATUS_STYLES = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-slate-100 text-slate-600',
  resolved: 'bg-blue-100 text-blue-700',
}

// HIS A is the data CONSUMER — conditions are owned/published by HIS B.
// Per interop requirements: HIS A can view but cannot mutate HIS B data.
// Flip to false to re-enable Create/Edit/Delete for admin/demo use.
const READ_ONLY = true

export default function Conditions() {
  const [conditions, setConditions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadConditions() }, [])

  const sorted = useMemo(
    () => [...conditions].sort((a, b) => Number(a.id || 0) - Number(b.id || 0)),
    [conditions],
  )

  function parseCondition(cond) {
    return {
      patientHn: cond.subject?.reference?.split('/').pop() ?? '',
      clinicalStatus: cond.clinicalStatus?.coding?.[0]?.code ?? 'active',
      icd10Code: cond.code?.coding?.[0]?.code ?? '',
      icd10Display: cond.code?.coding?.[0]?.display ?? '',
      onsetDate: cond.onsetDateTime ? cond.onsetDateTime.slice(0, 10) : '',
      note: cond.note?.[0]?.text ?? '',
    }
  }

  async function loadConditions() {
    setLoading(true)
    setError(null)
    try {
      const res = await httpClient.get('/api/v1/fhir/Condition')
      setConditions(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Error loading conditions.')
    } finally {
      setLoading(false)
    }
  }

  function buildPayload() {
    const payload = {
      resourceType: 'Condition',
      clinicalStatus: {
        coding: [{ system: 'http://terminology.hl7.org/CodeSystem/condition-clinical', code: form.clinicalStatus }],
      },
      code: {
        coding: [{ system: 'http://hl7.org/fhir/sid/icd-10', code: form.icd10Code, display: form.icd10Display }],
      },
      subject: { reference: `Patient/${form.patientHn}` },
    }
    if (form.onsetDate) payload.onsetDateTime = form.onsetDate
    if (form.note) payload.note = [{ text: form.note }]
    return payload
  }

  function openCreate() {
    setForm(initialForm)
    setSelectedId(null)
    setIsEditing(false)
    setModalOpen(true)
  }

  function openEdit(cond) {
    setForm(parseCondition(cond))
    setSelectedId(cond.id)
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
        await httpClient.put(`/api/v1/fhir/Condition/${encodeURIComponent(selectedId)}`, payload)
      } else {
        await httpClient.post('/api/v1/fhir/Condition', payload)
      }
      setModalOpen(false)
      await loadConditions()
    } catch (err) {
      const msg = err.response?.data?.detail ?? err.response?.data ?? err.message ?? 'Unable to save.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(cond) {
    if (!window.confirm(`Delete Condition #${cond.id}?`)) return
    setError(null)
    try {
      await httpClient.delete(`/api/v1/fhir/Condition/${encodeURIComponent(cond.id)}`)
      await loadConditions()
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Unable to delete.')
    }
  }

  if (loading) return <p className="text-gray-500 text-sm">Loading conditions…</p>

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Conditions</h2>
          <p className="mt-2 text-sm text-slate-500">บันทึกการวินิจฉัยโรค ICD-10</p>
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
            + New condition
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
              <th className="px-4 py-3">Clinical Status</th>
              <th className="px-4 py-3">ICD-10</th>
              <th className="px-4 py-3">Diagnosis</th>
              <th className="px-4 py-3">Onset</th>
              <th className="px-4 py-3">Note</th>
              {!READ_ONLY && <th className="px-4 py-3">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {sorted.map((cond) => {
              const clinicalStatus = cond.clinicalStatus?.coding?.[0]?.code ?? '—'
              const icd10Code = cond.code?.coding?.[0]?.code ?? '—'
              const icd10Display = cond.code?.coding?.[0]?.display ?? '—'
              const patient = cond.subject?.reference ?? '—'
              const onset = cond.onsetDateTime
                ? new Date(cond.onsetDateTime).toLocaleDateString('th-TH')
                : '—'
              const note = cond.note?.[0]?.text ?? '—'

              return (
                <tr key={cond.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-slate-500">{cond.id}</td>
                  <td className="px-4 py-3 font-medium text-slate-700">{patient}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${CLINICAL_STATUS_STYLES[clinicalStatus] ?? 'bg-slate-100 text-slate-600'}`}>
                      {clinicalStatus}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-700 text-xs">{icd10Code}</td>
                  <td className="px-4 py-3 text-slate-900 max-w-[200px] truncate">{icd10Display}</td>
                  <td className="px-4 py-3 text-slate-600 text-xs">{onset}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs max-w-[160px] truncate">{note}</td>
                  {!READ_ONLY && (
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(cond)}
                          className="rounded-2xl bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(cond)}
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
                  No conditions found.
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
                  {isEditing ? 'Edit condition' : 'New condition'}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {isEditing ? 'แก้ไขการวินิจฉัยโรค' : 'บันทึกการวินิจฉัยโรคใหม่'}
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
                  Clinical Status
                  <select
                    value={form.clinicalStatus}
                    onChange={(e) => setForm((p) => ({ ...p, clinicalStatus: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  >
                    {CLINICAL_STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  ICD-10 Code
                  <input
                    required
                    value={form.icd10Code}
                    onChange={(e) => setForm((p) => ({ ...p, icd10Code: e.target.value }))}
                    placeholder="E11"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Diagnosis (display)
                  <input
                    value={form.icd10Display}
                    onChange={(e) => setForm((p) => ({ ...p, icd10Display: e.target.value }))}
                    placeholder="Type 2 diabetes mellitus"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  Onset Date (optional)
                  <input
                    type="date"
                    value={form.onsetDate}
                    onChange={(e) => setForm((p) => ({ ...p, onsetDate: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Note (optional)
                  <input
                    value={form.note}
                    onChange={(e) => setForm((p) => ({ ...p, note: e.target.value }))}
                    placeholder="e.g. Controlled with medication"
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
                  {saving ? 'Saving…' : isEditing ? 'Save changes' : 'Create condition'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
