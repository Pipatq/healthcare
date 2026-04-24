import { useEffect, useMemo, useState } from 'react'
import httpClient from '../lib/httpClient'

const initialForm = {
  patientHn: '',
  loincCode: '',
  displayName: '',
  status: 'final',
  value: '',
  unit: '',
  issued: '',
}

const statuses = [
  'registered',
  'preliminary',
  'final',
  'amended',
  'corrected',
]

export default function Observations() {
  const [observations, setObservations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadObservations()
  }, [])

  const sortedObservations = useMemo(
    () => [...observations].sort((a, b) => Number(a.id || 0) - Number(b.id || 0)),
    [observations],
  )

  function parseObservation(obs) {
    return {
      patientHn: obs.subject?.reference?.split('/').pop() ?? '',
      loincCode: obs.code?.coding?.[0]?.code ?? '',
      displayName: obs.code?.coding?.[0]?.display ?? '',
      status: obs.status ?? 'final',
      value: obs.valueQuantity?.value?.toString() ?? obs.valueString ?? '',
      unit: obs.valueQuantity?.unit ?? '',
      issued: obs.issued?.slice(0, 16) ?? '',
    }
  }

  async function loadObservations() {
    setLoading(true)
    setError(null)
    try {
      const res = await httpClient.get('/api/v1/fhir/Observation')
      const data = res.data
      setObservations(Array.isArray(data) ? data : [])
    } catch (err) {
      const msg =
        err.response?.data?.detail ?? err.message ?? 'Unexpected error occurred.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  function buildPayload() {
    const payload = {
      resourceType: 'Observation',
      status: form.status,
      code: {
        coding: [
          {
            system: 'http://loinc.org',
            code: form.loincCode,
            display: form.displayName,
          },
        ],
      },
      subject: { reference: `Patient/${form.patientHn}` },
      issued: form.issued || new Date().toISOString(),
    }

    if (form.unit) {
      payload.valueQuantity = {
        value: Number(form.value),
        unit: form.unit,
        system: 'http://unitsofmeasure.org',
        code: form.unit,
      }
    } else {
      payload.valueString = form.value
    }

    return payload
  }

  function openCreate() {
    setForm(initialForm)
    setSelectedId(null)
    setIsEditing(false)
    setModalOpen(true)
  }

  function openEdit(obs) {
    setForm(parseObservation(obs))
    setSelectedId(obs.id)
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
        await httpClient.put(`/api/v1/fhir/Observation/${encodeURIComponent(selectedId)}`, payload)
      } else {
        await httpClient.post('/api/v1/fhir/Observation', payload)
      }
      setModalOpen(false)
      await loadObservations()
    } catch (err) {
      const msg =
        err.response?.data?.detail ??
        err.response?.data ??
        err.message ??
        'Unable to save observation.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(obs) {
    if (!window.confirm(`Delete observation ${obs.id}?`)) {
      return
    }
    setError(null)
    try {
      await httpClient.delete(`/api/v1/fhir/Observation/${encodeURIComponent(obs.id)}`)
      await loadObservations()
    } catch (err) {
      const msg =
        err.response?.data?.detail ?? err.message ?? 'Unable to delete observation.'
      setError(msg)
    }
  }

  if (loading) return <p className="text-gray-500 text-sm">Loading observations…</p>

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Observations</h2>
          <p className="mt-2 text-sm text-slate-500">จัดการผลแลบแบบครบทั้งสร้าง แก้ไข และลบได้ที่นี่</p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          + New observation
        </button>
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
              <th className="px-4 py-3">Code</th>
              <th className="px-4 py-3">Value</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Issued</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {sortedObservations.map((obs) => {
              const coding = obs.code?.coding?.[0] ?? {}
              const valueQty = obs.valueQuantity
              const valueStr = obs.valueString
              const displayValue = valueQty
                ? `${valueQty.value} ${valueQty.unit}`
                : valueStr ?? '—'
              const patientRef = obs.subject?.reference ?? '—'
              const issued = obs.issued
                ? new Date(obs.issued).toLocaleString('th-TH')
                : '—'

              return (
                <tr key={obs.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-slate-500">{obs.id ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-700">{patientRef}</td>
                  <td className="px-4 py-3 text-slate-900">
                    <div className="font-medium">{coding.display ?? '—'}</div>
                    {coding.code && <div className="text-xs text-slate-500">[{coding.code}]</div>}
                  </td>
                  <td className="px-4 py-3 text-blue-700">{displayValue}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-semibold text-emerald-700">
                      {obs.status ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 text-xs">{issued}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => openEdit(obs)}
                        className="rounded-2xl bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(obs)}
                        className="rounded-2xl bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 transition hover:bg-rose-100"
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 px-4 py-8">
          <div className="w-full max-w-2xl overflow-hidden rounded-[32px] bg-white shadow-2xl ring-1 ring-slate-200">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-5">
              <div>
                <h3 className="text-xl font-semibold text-slate-900">
                  {isEditing ? 'Edit observation' : 'New observation'}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {isEditing ? 'ปรับปรุงผลแลบ' : 'บันทึกผลแลบใหม่'}
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
                    onChange={(e) => setForm((prev) => ({ ...prev, patientHn: e.target.value }))}
                    placeholder="HN-0001"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Status
                  <select
                    value={form.status}
                    onChange={(e) => setForm((prev) => ({ ...prev, status: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  >
                    {statuses.map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  LOINC code
                  <input
                    required
                    value={form.loincCode}
                    onChange={(e) => setForm((prev) => ({ ...prev, loincCode: e.target.value }))}
                    placeholder="718-7"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Display name
                  <input
                    required
                    value={form.displayName}
                    onChange={(e) => setForm((prev) => ({ ...prev, displayName: e.target.value }))}
                    placeholder="Hemoglobin"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                <label className="space-y-2 text-sm text-slate-700">
                  Value
                  <input
                    required
                    value={form.value}
                    onChange={(e) => setForm((prev) => ({ ...prev, value: e.target.value }))}
                    placeholder="13.5"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Unit
                  <input
                    value={form.unit}
                    onChange={(e) => setForm((prev) => ({ ...prev, unit: e.target.value }))}
                    placeholder="g/dL"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Issued at
                  <input
                    type="datetime-local"
                    value={form.issued}
                    onChange={(e) => setForm((prev) => ({ ...prev, issued: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:justify-end">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="inline-flex items-center justify-center rounded-2xl border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
                >
                  {saving ? 'Saving…' : isEditing ? 'Update observation' : 'Create observation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
