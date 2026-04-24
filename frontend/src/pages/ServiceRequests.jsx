import { useEffect, useMemo, useState } from 'react'
import httpClient from '../lib/httpClient'

const initialForm = {
  patientHn: '',
  orderCode: '',
  displayName: '',
  priority: 'routine',
  status: 'active',
}

const priorities = ['routine', 'urgent', 'asap', 'stat']
const statuses = ['draft', 'active', 'completed', 'on-hold', 'cancelled']

const PRIORITY_STYLES = {
  urgent: 'bg-red-100 text-red-700',
  stat: 'bg-red-100 text-red-700',
  asap: 'bg-orange-100 text-orange-700',
  routine: 'bg-blue-100 text-blue-700',
}

const STATUS_STYLES = {
  active: 'bg-green-100 text-green-700',
  completed: 'bg-slate-100 text-slate-600',
  cancelled: 'bg-rose-100 text-rose-700',
  'on-hold': 'bg-yellow-100 text-yellow-700',
  draft: 'bg-slate-100 text-slate-600',
}

export default function ServiceRequests() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadRequests()
  }, [])

  const sortedRequests = useMemo(
    () => [...requests].sort((a, b) => Number(a.id || 0) - Number(b.id || 0)),
    [requests],
  )

  function parseRequest(sr) {
    return {
      patientHn: sr.subject?.reference?.split('/').pop() ?? '',
      orderCode: sr.code?.coding?.[0]?.code ?? '',
      displayName: sr.code?.coding?.[0]?.display ?? '',
      priority: sr.priority ?? 'routine',
      status: sr.status ?? 'active',
    }
  }

  async function loadRequests() {
    setLoading(true)
    setError(null)
    try {
      const res = await httpClient.get('/api/v1/fhir/ServiceRequest')
      const data = res.data
      setRequests(Array.isArray(data) ? data : [])
    } catch (err) {
      const msg =
        err.response?.data?.detail ?? err.message ?? 'Unexpected error occurred.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  function buildPayload() {
    return {
      resourceType: 'ServiceRequest',
      status: form.status,
      intent: 'order',
      priority: form.priority,
      code: {
        coding: [
          {
            system: 'urn:his-b:order-codes',
            code: form.orderCode,
            display: form.displayName,
          },
        ],
      },
      subject: { reference: `Patient/${form.patientHn}` },
    }
  }

  function openCreate() {
    setForm(initialForm)
    setSelectedId(null)
    setIsEditing(false)
    setModalOpen(true)
  }

  function openEdit(sr) {
    setForm(parseRequest(sr))
    setSelectedId(sr.id)
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
        await httpClient.put(`/api/v1/fhir/ServiceRequest/${encodeURIComponent(selectedId)}`, payload)
      } else {
        await httpClient.post('/api/v1/fhir/ServiceRequest', payload)
      }
      setModalOpen(false)
      await loadRequests()
    } catch (err) {
      const msg =
        err.response?.data?.detail ??
        err.response?.data ??
        err.message ??
        'Unable to save service request.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(sr) {
    if (!window.confirm(`Delete service request ${sr.id}?`)) {
      return
    }
    setError(null)
    try {
      await httpClient.delete(`/api/v1/fhir/ServiceRequest/${encodeURIComponent(sr.id)}`)
      await loadRequests()
    } catch (err) {
      const msg =
        err.response?.data?.detail ?? err.message ?? 'Unable to delete service request.'
      setError(msg)
    }
  }

  if (loading) return <p className="text-gray-500 text-sm">Loading service requests…</p>

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Service Requests</h2>
          <p className="mt-2 text-sm text-slate-500">สร้าง แก้ไข และลบคำสั่งแพทย์ได้จากตารางนี้</p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          + New order
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
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Authored</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {sortedRequests.map((sr) => {
              const coding = sr.code?.coding?.[0] ?? {}
              const patient = sr.subject?.reference ?? '—'
              const authored = sr.authoredOn
                ? new Date(sr.authoredOn).toLocaleString('th-TH')
                : '—'
              const priority = sr.priority ?? 'routine'
              const srStatus = sr.status ?? '—'

              return (
                <tr key={sr.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-slate-500">{sr.id ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-700">{patient}</td>
                  <td className="px-4 py-3">
                    <div className="font-medium text-slate-900">{coding.display ?? '—'}</div>
                    {coding.code && <div className="text-xs text-slate-500">[{coding.code}]</div>}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${PRIORITY_STYLES[priority] ?? 'bg-slate-100 text-slate-600'}`}>
                      {priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-full px-2.5 py-1 text-[11px] font-semibold ${STATUS_STYLES[srStatus] ?? 'bg-slate-100 text-slate-600'}`}>
                      {srStatus}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 text-xs">{authored}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => openEdit(sr)}
                        className="rounded-2xl bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(sr)}
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
                  {isEditing ? 'Edit order' : 'New order'}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {isEditing ? 'ปรับปรุงคำสั่งแพทย์' : 'สร้างคำสั่งแพทย์ใหม่'}
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
                  Priority
                  <select
                    value={form.priority}
                    onChange={(e) => setForm((prev) => ({ ...prev, priority: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  >
                    {priorities.map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <label className="space-y-2 text-sm text-slate-700">
                  Order code
                  <input
                    required
                    value={form.orderCode}
                    onChange={(e) => setForm((prev) => ({ ...prev, orderCode: e.target.value }))}
                    placeholder="CBC-001"
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

              <label className="space-y-2 text-sm text-slate-700">
                Display name
                <input
                  required
                  value={form.displayName}
                  onChange={(e) => setForm((prev) => ({ ...prev, displayName: e.target.value }))}
                  placeholder="Complete Blood Count"
                  className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                />
              </label>

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
                  {saving ? 'Saving…' : isEditing ? 'Update order' : 'Create order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
