import { useEffect, useState } from 'react'

// Placeholder page: proves React, Tailwind and the Django API are all connected.
// Replace it with real screens as tickets are built.
export default function App() {
  const [backend, setBackend] = useState('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((response) => (response.ok ? response.json() : Promise.reject(response)))
      .then((data) => setBackend(data.status === 'ok' ? 'connected' : 'error'))
      .catch(() => setBackend('error'))
  }, [])

  return (
    <main className="flex min-h-dvh items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-xl border border-line bg-white p-6 text-center shadow-sm">
        <h1 className="text-xl font-semibold text-brand">Marinus Painting</h1>
        <p className="mt-2 text-sm text-gray-500">Project manager: development build</p>
        <p className="mt-6 text-sm">
          Backend: {backend === 'checking' && <span className="text-gray-500">checking…</span>}
          {backend === 'connected' && <span className="font-medium text-brand">connected</span>}
          {backend === 'error' && (
            <span className="font-medium text-danger">not reachable (is Django running?)</span>
          )}
        </p>
      </div>
    </main>
  )
}
