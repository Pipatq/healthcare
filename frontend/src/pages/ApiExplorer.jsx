import { useMemo, useState } from 'react'
import httpClient from '../lib/httpClient'

const sampleEndpoints = [
  { label: 'All Patients', path: 'Patient', method: 'GET' },
  { label: 'Single Patient HN-0001', path: 'Patient/HN-0001', method: 'GET' },
  { label: 'Observations for HN-0001', path: 'Observation?patient=HN-0001', method: 'GET' },
  { label: 'All ServiceRequests', path: 'ServiceRequest', method: 'GET' },
  { label: 'Create Patient', path: 'Patient', method: 'POST' },
  { label: 'Update Patient', path: 'Patient/HN-0001', method: 'PUT' },
  { label: 'Delete Patient', path: 'Patient/HN-0001', method: 'DELETE' },
]

const methods = ['GET', 'POST', 'PUT', 'DELETE']

function normalizeUrl(path) {
  const trimmed = path.trim()
  if (!trimmed) return ''
  return trimmed.startsWith('/api/v1/fhir/')
    ? trimmed
    : `/api/v1/fhir/${trimmed.replace(/^\/+/, '')}`
}

export default function ApiExplorer() {
  const [method, setMethod] = useState('GET')
  const [path, setPath] = useState('Patient')
  const [body, setBody] = useState('')
  const [response, setResponse] = useState(null)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const endpointUrl = useMemo(() => normalizeUrl(path), [path])

  async function handleSubmit(event) {
    event.preventDefault()
    setError(null)
    setResponse(null)
    setStatus(null)
    setLoading(true)

    try {
      const requestConfig = {
        method,
        url: endpointUrl,
      }

      if (['POST', 'PUT'].includes(method)) {
        requestConfig.data = body ? JSON.parse(body) : {}
      }

      const res = await httpClient(requestConfig)
      setResponse(res.data)
      setStatus(res.status)
    } catch (err) {
      const msg =
        err.response?.data?.detail ??
        err.response?.data ??
        err.message ??
        'Unexpected error occurred.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg, null, 2))
      setStatus(err.response?.status ?? null)
    } finally {
      setLoading(false)
    }
  }

  function handleSampleClick(sample) {
    setMethod(sample.method)
    setPath(sample.path)
    if (sample.method === 'POST' || sample.method === 'PUT') {
      setBody(`{
  "resourceType": "Patient",
  "id": "HN-0001",
  "name": [{ "family": "Doe", "given": ["John"] }],
  "gender": "male"
}`)
    } else {
      setBody('')
    }
  }

  return (
    <div className="space-y-6">
      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-slate-900">API Explorer</h2>
            <p className="mt-1 text-sm text-slate-500">
              เรียกใช้ API ตามรายละเอียดใน Readme พร้อมดูผลลัพธ์แบบเรียลไทม์
            </p>
          </div>
          <div className="rounded-2xl bg-slate-100 px-4 py-3 text-sm text-slate-700">
            Base path: <span className="font-semibold">/api/v1/fhir/</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="sm:col-span-2">
              <label className="block text-sm font-medium text-slate-700 mb-2">Path</label>
              <input
                type="text"
                value={path}
                onChange={(e) => setPath(e.target.value)}
                placeholder="Patient or Patient/HN-0001 or Observation?patient=HN-0001"
                className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
              />
              <p className="mt-2 text-xs text-slate-500">
                เส้นทาง API ที่จะเรียกใช้ โดยระบบจะต่อกับ <code>/api/v1/fhir/</code>
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Method</label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200"
              >
                {methods.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {['POST', 'PUT'].includes(method) && (
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">JSON Body</label>
              <textarea
                rows="10"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder='{
  "resourceType": "Patient",
  "id": "HN-0001",
  "name": [{ "family": "Doe", "given": ["John"] }],
  "gender": "male"
}'
                className="w-full rounded-2xl border border-slate-300 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none focus:ring-2 focus:ring-slate-200 font-mono"
              />
            </div>
          )}

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <p className="text-sm text-slate-500">Endpoint</p>
              <p className="text-sm font-medium text-slate-900">{endpointUrl}</p>
            </div>
            <button
              type="submit"
              disabled={loading || !path.trim()}
              className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'Executing…' : 'Execute Request'}
            </button>
          </div>
        </form>
      </div>

      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-lg font-semibold text-slate-900">ตัวอย่าง API</h3>
          <p className="mt-2 text-sm text-slate-500">
            เลือกตัวอย่าง เพื่อกรอกข้อมูลให้อัตโนมัติ แล้วกด Execute Request.
          </p>
          <div className="mt-4 space-y-3">
            {sampleEndpoints.map((sample) => (
              <button
                key={sample.label}
                type="button"
                onClick={() => handleSampleClick(sample)}
                className="w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:border-slate-300 hover:bg-slate-100"
              >
                <div className="flex items-center justify-between gap-3">
                  <span>{sample.label}</span>
                  <span className="rounded-full bg-slate-900 px-3 py-1 text-[11px] font-semibold text-white">
                    {sample.method}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-500">{sample.path}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-slate-900">ผลลัพธ์การเรียก API</h3>
                <p className="mt-1 text-sm text-slate-500">สถานะและตัวอย่างผลลัพธ์จาก backend</p>
              </div>
              {status != null && (
                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                  HTTP {status}
                </span>
              )}
            </div>

            {error ? (
              <pre className="rounded-2xl bg-rose-50 p-4 text-sm text-rose-900 overflow-x-auto">{error}</pre>
            ) : response ? (
              <pre className="rounded-2xl bg-slate-950 p-4 text-sm text-slate-100 overflow-x-auto">{JSON.stringify(response, null, 2)}</pre>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-200 p-8 text-center text-sm text-slate-500">
                เรียก API เพื่อดู data response ที่นี่
              </div>
            )}
          </div>

          <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-slate-900">ข้อมูลช่วยเหลือ</h3>
            <ul className="mt-4 space-y-3 text-sm text-slate-600">
              <li>• โดยปกติใช้ path ตาม Readme เช่น <code className="rounded bg-slate-100 px-1 py-0.5">Patient</code>, <code className="rounded bg-slate-100 px-1 py-0.5">Observation?patient=HN-0001</code></li>
              <li>• เมื่อต้องการเรียก Gateway/FHIR proxy ให้ใช้ HTTP method ที่ถูกต้อง</li>
              <li>• POST / PUT ต้องส่ง JSON body ที่ถูกต้องตามทรัพยากร FHIR</li>
              <li>• ถ้าเป็น 401 ระบบจะพาไปหน้า login ใหม่อัตโนมัติ</li>
            </ul>
          </div>
        </section>
      </div>
    </div>
  )
}
