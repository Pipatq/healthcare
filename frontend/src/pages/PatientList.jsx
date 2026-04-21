import { useState, useEffect } from 'react'
import httpClient from '../lib/httpClient'

export default function PatientList() {
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    httpClient
      .get('/api/v1/fhir/Patient')
      .then((res) => {
        const data = res.data
        setPatients(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        const msg =
          err.response?.data?.detail ??
          err.message ??
          'Unexpected error occurred.'
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <p className="text-gray-500 text-sm">Loading patients…</p>
  }

  if (error) {
    return (
      <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
        <strong>Error:</strong> {String(error)}
      </div>
    )
  }

  if (patients.length === 0) {
    return <p className="text-gray-500 text-sm">No patients found.</p>
  }

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Patients</h2>
      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
          <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500 tracking-wider">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Gender</th>
              <th className="px-4 py-3">Birth Date</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {patients.map((p) => {
              const name = p.name?.[0]
              const displayName = name?.text
                ?? [name?.family, ...(name?.given ?? [])].filter(Boolean).join(', ')
                ?? '—'

              return (
                <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-400 text-xs">{p.id ?? '—'}</td>
                  <td className="px-4 py-3 font-medium text-gray-800">{displayName}</td>
                  <td className="px-4 py-3 capitalize text-gray-600">{p.gender ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{p.birthDate ?? '—'}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
