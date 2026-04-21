import { useState, useEffect } from 'react'
import httpClient from '../lib/httpClient'

const PRIORITY_STYLES = {
  urgent: 'bg-red-100 text-red-700',
  stat: 'bg-red-100 text-red-700',
  asap: 'bg-orange-100 text-orange-700',
  routine: 'bg-blue-100 text-blue-700',
}

const STATUS_STYLES = {
  active: 'bg-green-100 text-green-700',
  completed: 'bg-gray-100 text-gray-600',
  cancelled: 'bg-red-100 text-red-400',
  'on-hold': 'bg-yellow-100 text-yellow-700',
}

export default function ServiceRequests() {
  const [requests, setRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    httpClient
      .get('/api/v1/fhir/ServiceRequest')
      .then((res) => {
        const data = res.data
        setRequests(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        const msg =
          err.response?.data?.detail ?? err.message ?? 'Unexpected error occurred.'
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-gray-500 text-sm">Loading service requests…</p>

  if (error)
    return (
      <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
        <strong>Error:</strong> {String(error)}
      </div>
    )

  if (requests.length === 0)
    return <p className="text-gray-500 text-sm">No service requests found.</p>

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Service Requests</h2>
      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
          <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500 tracking-wider">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Patient</th>
              <th className="px-4 py-3">Order</th>
              <th className="px-4 py-3">Priority</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Authored</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {requests.map((sr) => {
              const coding = sr.code?.coding?.[0] ?? {}
              const patient = sr.subject?.reference ?? '—'
              const authored = sr.authoredOn
                ? new Date(sr.authoredOn).toLocaleString('th-TH')
                : '—'
              const priority = sr.priority ?? 'routine'
              const srStatus = sr.status ?? '—'

              return (
                <tr key={sr.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-400 text-xs">{sr.id ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{patient}</td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-gray-800">{coding.display ?? '—'}</span>
                    {coding.code && (
                      <span className="ml-2 text-xs text-gray-400 font-mono">[{coding.code}]</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      PRIORITY_STYLES[priority] ?? 'bg-gray-100 text-gray-600'
                    }`}>
                      {priority}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      STATUS_STYLES[srStatus] ?? 'bg-gray-100 text-gray-600'
                    }`}>
                      {srStatus}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{authored}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
