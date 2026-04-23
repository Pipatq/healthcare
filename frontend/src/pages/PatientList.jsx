import { useEffect, useMemo, useState } from 'react'
import httpClient from '../lib/httpClient'

const initialForm = {
  hn: '',
  firstName: '',
  lastName: '',
  gender: 'male',
  birthDate: '',
  phone: '',
  address: '',
}

const genders = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
  { value: 'unknown', label: 'Unknown' },
]

export default function PatientList() {
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadPatients()
  }, [])

  const sortedPatients = useMemo(
    () => [...patients].sort((a, b) => (a.id || '').localeCompare(b.id || '')),
    [patients],
  )

  function buildPayload() {
    const payload = {
      resourceType: 'Patient',
      id: form.hn,
      identifier: [{ system: 'urn:his-b:hn', value: form.hn }],
      name: [{ family: form.lastName, given: [form.firstName] }],
      gender: form.gender,
      birthDate: form.birthDate || undefined,
      telecom: form.phone ? [{ system: 'phone', value: form.phone }] : undefined,
      address: form.address ? [{ text: form.address }] : undefined,
    }
    if (!payload.birthDate) delete payload.birthDate
    if (!payload.telecom?.[0]?.value) delete payload.telecom
    if (!payload.address?.[0]?.text) delete payload.address
    return payload
  }

  function parsePatient(patient) {
    const name = patient.name?.[0] || {}
    return {
      hn: patient.id ?? '',
      firstName: (name.given?.[0] ?? '').toString(),
      lastName: name.family ?? '',
      gender: patient.gender ?? 'male',
      birthDate: patient.birthDate ?? '',
      phone: patient.telecom?.[0]?.value ?? '',
      address: patient.address?.[0]?.text ?? '',
    }
  }

  async function loadPatients() {
    setLoading(true)
    setError(null)
    try {
      const res = await httpClient.get('/api/v1/fhir/Patient')
      const data = res.data
      setPatients(Array.isArray(data) ? data : [])
    } catch (err) {
      const msg =
        err.response?.data?.detail ?? err.message ?? 'Unexpected error occurred.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  function resetForm() {
    setForm(initialForm)
    setIsEditing(false)
  }

  function openCreate() {
    resetForm()
    setModalOpen(true)
  }

  function openEdit(patient) {
    setForm(parsePatient(patient))
    setIsEditing(true)
    setModalOpen(true)
  }

  async function handleSave(e) {
    e.preventDefault()
    setError(null)
    setSaving(true)
    try {
      const payload = buildPayload()
      if (isEditing) {
        await httpClient.put(`/api/v1/fhir/Patient/${encodeURIComponent(form.hn)}`, payload)
      } else {
        await httpClient.post('/api/v1/fhir/Patient', payload)
      }
      setModalOpen(false)
      await loadPatients()
    } catch (err) {
      const msg =
        err.response?.data?.detail ??
        err.response?.data ??
        err.message ??
        'Unable to save patient.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(patient) {
    if (!window.confirm(`Delete patient ${patient.id}?`)) {
      return
    }
    setError(null)
    try {
      await httpClient.delete(`/api/v1/fhir/Patient/${encodeURIComponent(patient.id)}`)
      await loadPatients()
    } catch (err) {
      const msg =
        err.response?.data?.detail ?? err.message ?? 'Unable to delete patient.'
      setError(msg)
    }
  }

  if (loading) {
    return <p className="text-gray-500 text-sm">Loading patients…</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-slate-900">Patients</h2>
          <p className="mt-2 text-sm text-slate-500">ดู, สร้าง, แก้ไข และลบข้อมูลผู้ป่วยได้จากหน้านี้</p>
        </div>
        <button
          type="button"
          onClick={openCreate}
          className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800"
        >
          + New patient
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
              <th className="px-4 py-3">HN</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Gender</th>
              <th className="px-4 py-3">Birth date</th>
              <th className="px-4 py-3">Phone</th>
              <th className="px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {sortedPatients.map((patient) => {
              const name = patient.name?.[0]
              const displayName = name?.text ?? [name?.family, ...(name?.given ?? [])].filter(Boolean).join(' ') ?? '—'
              return (
                <tr key={patient.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-slate-500">{patient.id ?? '—'}</td>
                  <td className="px-4 py-3 font-medium text-slate-900">{displayName}</td>
                  <td className="px-4 py-3 capitalize text-slate-600">{patient.gender ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{patient.birthDate ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{patient.telecom?.[0]?.value ?? '—'}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => openEdit(patient)}
                        className="rounded-2xl bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-200"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(patient)}
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
                  {isEditing ? 'Edit patient' : 'New patient'}
                </h3>
                <p className="mt-1 text-sm text-slate-500">
                  {isEditing ? 'แก้ไขข้อมูลผู้ป่วย' : 'เพิ่มผู้ป่วยใหม่ลงในระบบ'}
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
              <div className="grid gap-4 lg:grid-cols-3">
                <label className="space-y-2 text-sm text-slate-700">
                  HN
                  <input
                    required
                    disabled={isEditing}
                    value={form.hn}
                    onChange={(e) => setForm((prev) => ({ ...prev, hn: e.target.value }))}
                    placeholder="HN-0001"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  First name
                  <input
                    required
                    value={form.firstName}
                    onChange={(e) => setForm((prev) => ({ ...prev, firstName: e.target.value }))}
                    placeholder="John"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Last name
                  <input
                    required
                    value={form.lastName}
                    onChange={(e) => setForm((prev) => ({ ...prev, lastName: e.target.value }))}
                    placeholder="Doe"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
              </div>

              <div className="grid gap-4 lg:grid-cols-3">
                <label className="space-y-2 text-sm text-slate-700">
                  Gender
                  <select
                    value={form.gender}
                    onChange={(e) => setForm((prev) => ({ ...prev, gender: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  >
                    {genders.map((item) => (
                      <option key={item.value} value={item.value}>{item.label}</option>
                    ))}
                  </select>
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Birth date
                  <input
                    type="date"
                    value={form.birthDate}
                    onChange={(e) => setForm((prev) => ({ ...prev, birthDate: e.target.value }))}
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
                <label className="space-y-2 text-sm text-slate-700">
                  Phone
                  <input
                    type="tel"
                    value={form.phone}
                    onChange={(e) => setForm((prev) => ({ ...prev, phone: e.target.value }))}
                    placeholder="089-000-0000"
                    className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
                  />
                </label>
              </div>

              <label className="space-y-2 text-sm text-slate-700">
                Address
                <textarea
                  rows="3"
                  value={form.address}
                  onChange={(e) => setForm((prev) => ({ ...prev, address: e.target.value }))}
                  placeholder="123 Main St, Bangkok"
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
                  {saving ? 'Saving…' : isEditing ? 'Update patient' : 'Create patient'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
