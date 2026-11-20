import { useState } from 'react'

export default function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleFileChange(event) {
    setFile(event.target.files[0] ?? null)
    setPreview(null)
    setError('')
  }

  async function handlePreview() {
    setLoading(true)
    setPreview(null)
    setError('')

    try {
      const tokenResponse = await fetch('/api/preview/')
      if (!tokenResponse.ok) {
        throw new Error(`Could not reach the preview endpoint (${tokenResponse.status}).`)
      }
      const { csrfToken } = await tokenResponse.json()

      const form = new FormData()
      form.append('file', file)

      const response = await fetch('/api/preview/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrfToken },
        body: form,
      })

      if (!response.ok) {
        const details = await response.json().catch(() => ({}))
        throw new Error(details.error || `Preview failed (${response.status}).`)
      }

      const data = await response.json()
      setPreview(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <h1>Supplier catalogue</h1>

      <label>
        Choose an Excel file{' '}
        <input
          type="file"
          accept=".xlsx"
          disabled={loading}
          onChange={handleFileChange}
        />
      </label>

      <button type="button" disabled={!file || loading} onClick={handlePreview}>
        {loading ? 'Reading…' : 'Preview'}
      </button>

      {error && <p role="alert">{error}</p>}
            {preview?.errors?.length > 0 && (
        <section>
          <h2>Prices to correct</h2>
          <ul>
            {preview.errors.map((message) => (
              <li key={message}>{message}</li>
            ))}
          </ul>
        </section>
      )}

      {preview && (
        <table>
          <thead>
            <tr>
              {preview.headers.map((header, index) => (
                <th key={index} scope="col">{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {preview.rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((value, columnIndex) => (
                  <td key={columnIndex}>{value ?? '—'}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </main>
  )
}