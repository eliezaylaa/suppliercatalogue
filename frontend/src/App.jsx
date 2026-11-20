import { useState } from 'react'

async function postWorkbook(url, form, csrfToken) {
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken },
    body: form,
  })

  if (!response.ok) {
    const details = await response.json().catch(() => ({}))
    throw new Error(details.error || `Request failed (${response.status}).`)
  }

  return response
}

export default function App() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [csrfToken, setCsrfToken] = useState('')
  const [edits, setEdits] = useState({})
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  function handleFileChange(event) {
    setFile(event.target.files[0] ?? null)
    setPreview(null)
    setEdits({})
    setError('')
  }

  async function handlePreview() {
    if (!file) return

    setBusy('preview')
    setError('')
    setPreview(null)
    setEdits({})

    try {
      const tokenResponse = await fetch('/api/preview/')
      if (!tokenResponse.ok) {
        throw new Error(`Could not reach Django (${tokenResponse.status}).`)
      }

      const tokenData = await tokenResponse.json()
      setCsrfToken(tokenData.csrfToken)

      const form = new FormData()
      form.append('file', file)

      const response = await postWorkbook('/api/preview/', form, tokenData.csrfToken)
      setPreview(await response.json())
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  const priceColumn = preview?.headers.indexOf('price_eur') ?? -1
  const referenceColumn = preview?.headers.indexOf('reference') ?? -1

  function currentPrice(row, index) {
    return edits[index] ?? row[priceColumn] ?? ''
  }

  const warnings = []
  if (preview) {
    preview.rows.forEach((row, index) => {
      const price = String(currentPrice(row, index)).trim()
      const product = row[referenceColumn]
      const label = `Excel row ${index + 2}: product ${product}`

      if (price === '') {
        warnings.push(`${label} is missing a price.`)
      } else if (!Number.isFinite(Number(price)) || Number(price) < 0) {
        warnings.push(`${label} needs a numeric price of zero or more.`)
      }
    })
  }

  async function handleDownload() {
    if (!file || !preview || warnings.length > 0) return

    setBusy('download')
    setError('')

    try {
      const prices = preview.rows.map((row, index) => ({
        value: currentPrice(row, index),
        edited: Object.hasOwn(edits, index),
      }))

      const form = new FormData()
      form.append('file', file)
      form.append('prices', JSON.stringify(prices))

      const response = await postWorkbook('/api/download/', form, csrfToken)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)

      const link = document.createElement('a')
      link.href = url
      link.download = file.name.replace(/\.xlsx$/i, '_corrected.xlsx')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
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
          disabled={Boolean(busy)}
          onChange={handleFileChange}
        />
      </label>

      <button type="button" disabled={!file || Boolean(busy)} onClick={handlePreview}>
        {busy === 'preview' ? 'Reading…' : 'Preview'}
      </button>

      {error && <p role="alert">{error}</p>}

      {preview && (
        <>
          {warnings.length > 0 && (
            <section>
              <h2>Prices to correct</h2>
              <ul>
                {warnings.map((message) => <li key={message}>{message}</li>)}
              </ul>
            </section>
          )}

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
                    <td key={columnIndex}>
                      {columnIndex === priceColumn ? (
                        <input
                          type="number"
                          min="0"
                          step="any"
                          aria-label={`Price for ${row[referenceColumn]}`}
                          value={currentPrice(row, rowIndex)}
                          disabled={Boolean(busy)}
                          onChange={(event) => {
                            const price = event.target.value
                            setEdits((previous) => ({
                              ...previous,
                              [rowIndex]: price,
                            }))
                          }}
                        />
                      ) : (
                        value ?? '—'
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>

          <button
            type="button"
            disabled={Boolean(busy) || warnings.length > 0}
            onClick={handleDownload}
          >
            {busy === 'download' ? 'Preparing file…' : 'Download corrected Excel'}
          </button>
        </>
      )}
    </main>
  )
}