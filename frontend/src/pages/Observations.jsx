import { useState, useEffect } from 'react'
import httpClient from '../lib/httpClient'

export default function Observations() {
  const [observations, setObservations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    httpClient
      .get('/api/v1/fhir/Observation')
      .then((res) => {
        const data = res.data
        setObservations(Array.isArray(data) ? data : [])
      })
      .catch((err) => {
        const msg =
          err.response?.data?.detail ?? err.message ?? 'Unexpected error occurred.'
        setError(msg)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="text-gray-500 text-sm">Loading observations…</p>

  if (error)
    return (
      <div className="rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
        <strong>Error:</strong> {String(error)}
      </div>
    )

  if (observations.length === 0)
    return <p className="text-gray-500 text-sm">No observations found.</p>

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Observations</h2>
      <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm">
        <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
          <thead className="bg-gray-50 text-left text-xs font-semibold uppercase text-gray-500 tracking-wider">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Patient</th>
              <th className="px-4 py-3">Test (LOINC)</th>
              <th className="px-4 py-3">Value</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Issued</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {observations.map((obs) => {
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
                <tr key={obs.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-gray-400 text-xs">{obs.id ?? '—'}</td>
                  <td className="px-4 py-3 text-gray-700">{patientRef}</td>
                  <td className="px-4 py-3">
                    <span className="font-medium text-gray-800">{coding.display ?? '—'}</span>
                    {coding.code && (
                      <span className="ml-2 text-xs text-gray-400 font-mono">[{coding.code}]</span>
                    )}
                  </td>
                  <td className="px-4 py-3 font-semibold text-blue-700">{displayValue}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      obs.status === 'final'
                        ? 'bg-green-100 text-green-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {obs.status ?? '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{issued}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
