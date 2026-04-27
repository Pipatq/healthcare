import { useEffect, useMemo, useState } from 'react'
import httpClient from '../lib/httpClient'

const initialForm = {
  patientHn: '',
  status: 'active',
  intent: 'order',
  atcCode: '',
  medicationDisplay: '',
  dosageText: '',
}

const STATUS_OPTIONS = ['active', 'completed', 'cancelled', 'on-hold', 'stopped']
const INTENT_OPTIONS = ['order', 'plan', 'proposal', 'directive']

const STATUS_STYLES = {
  active: 'bg-green-100 text-green-700',
  completed: 'bg-slate-100 text-slate-600',
  cancelled: 'bg-rose-100 text-rose-700',
  'on-hold': 'bg-yellow-100 text-yellow-700',
  stopped: 'bg-orange-100 text-orange-700',
}

// HIS A is the data CONSUMER — medication requests are owned/published by HIS B.
// Per interop requirements: HIS A can view but cannot mutate HIS B data.
// Flip to false to re-enable Create/Edit/Delete for admin/demo use.
const READ_ONLY = false

export default function MedicationRequests() {
  const [medRequests, setMedRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadMedRequests() }, [])

  const sorted = useMemo(
    () => [...medRequests].sort((a, b) => Number(a.id || 0) - Number(b.id || 0)),
    [medRequests],
  )

  function parseMedRequest(mr) {
    const coding = mr.medication?.concept?.coding?.[0] ?? {}
    const dosage = mr.dosageInstruction?.[0]?.text ?? ''
    return {
      patientHn: mr.subject?.reference?.split('/').pop() ?? '',
      status: mr.status ?? 'active',
      intent: mr.intent ?? 'order',
      atcCode: coding.code ?? '',
      medicationDisplay: coding.display ?? '',
      dosageText: dosage,
    }
  }

  async function loadMedRequests() {
    setLoading(true)
    setError(null)
    try {
      const res = await httpClient.get('/api/v1/fhir/MedicationRequest')
      setMedRequests(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Error loading medication requests.')
    } finally {
      setLoading(false)
    }
  }

  function buildPayload() {
    return {
      resourceType: 'MedicationRequest',
      status: form.status,
      intent: form.intent,
      medication: {
        concept: {
          coding: [{ system: 'http://www.whocc.no/atc', code: form.atcCode, display: form.medicationDisplay }],
        },
      },
      subject: { reference: `Patient/${form.patientHn}` },
      dosageInstruction: form.dosageText ? [{ text: form.dosageText }] : [],
      authoredOn: new Date().toISOString(),
    }
  }

  function openCreate() {
    setForm(initialForm)
    setSelectedId(null)
    setIsEditing(false)
    setModalOpen(true)
  }

  function openEdit(mr) {
    setForm(parseMedRequest(mr))
    setSelectedId(mr.id)
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
        await httpClient.put(`/api/v1/fhir/MedicationRequest/${encodeURIComponent(selectedId)}`, payload)
      } else {
        await httpClient.post('/api/v1/fhir/MedicationRequest', payload)
      }
      setModalOpen(false)
      await loadMedRequests()
    } catch (err) {
      const msg = err.response?.data?.detail ?? err.response?.data ?? err.message ?? 'Unable to save.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(mr) {
    if (!window.confirm(`Delete MedicationRequest #${mr.id}?`)) return
    setError(null)
    try {
      await httpClient.delete(`/api/v1/fhir/MedicationRequest/${encodeURIComponent(mr.id)}`)
      await loadMedRequests()
    } catch (err) {
      setError(err.response?.data?.detail ?? err.message ?? 'Unable to delete.')
    }
  }

  if (loading) return <p className="text-gray-500 text-sm">Loading medication requests…</p>

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Medication Requests</h2>
          <p className="mt-2 text-sm text-slate-500">บันทึกและจัดการรายการยาที่แพทย์สั่ง</p>
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
            + New medication
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
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">ATC Code</th>
              <th className="px-4 py-3">Medication</th>
              <th className="px-4 py-3">Dosage</th>
              <th className="px-4 py-3">Authored</th>
              {!READ_ONLY && <th className="px-4 py-3">Actions</th>}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {sorted.map((mr) => {
              const coding = mr.medication?.concept?.coding?.[0] ?? {}
              const patient = mr.subject?.reference ?? '—'
              const authored = mr.authoredOn
                ? new Date(mr.authoredOn).toLocaleString('th-TH')
                : '—'
              const mrStatus = mr.status ?? '—'
              const dosage = mr.dosageInstruction?.[0]?.text ?? '—'

              return (
                <tr key={mr.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-slate-500">{mr.id}</td>
                  <td className="px-4 py-3 font-medium text-slate-700">{patient}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${STATUS_STYLES[mrStatus] ?? 'bg-slate-100 text-slate-600'}`}>
                      {mrStatus}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-700 text-xs">{coding.code ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-900 font-medium">{coding.display ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600 text-xs max-w-[200px] truncate">{dosage}</td>
                  <td className="px-4 py-3 text-slate-600 text-xs">{authored}</td>
                  {!READ_ONLY && (
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => openEdit(mr)}
                          className="rounded-2xl bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDelete(mr)}
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
                  No medication requests found.
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
                  {isEditing ? 'Edit medication' : 'New medication'}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {isEditing ? 'แก้ไขรายการยา' : 'สั่งยาใหม่'}
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
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  ATC Code
                  <input
                    required
                    value={form.atcCode}
                    onChange={(e) => setForm((p) => ({ ...p, atcCode: e.target.value }))}
                    placeholder="A10BA02"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Medication name
                  <input
                    value={form.medicationDisplay}
                    onChange={(e) => setForm((p) => ({ ...p, medicationDisplay: e.target.value }))}
                    placeholder="Metformin"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  Intent
                  <select
                    value={form.intent}
                    onChange={(e) => setForm((p) => ({ ...p, intent: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  >
                    {INTENT_OPTIONS.map((i) => (
                      <option key={i} value={i}>{i}</option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Dosage instructions
                  <input
                    value={form.dosageText}
                    onChange={(e) => setForm((p) => ({ ...p, dosageText: e.target.value }))}
                    placeholder="500mg twice daily with meals"
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
                  {saving ? 'Saving…' : isEditing ? 'Save changes' : 'Create medication'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
