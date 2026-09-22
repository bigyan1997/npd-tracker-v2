import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { commitImport, previewImport } from '../api/import'

export function ImportModal({ onClose, onImported }) {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [excluded, setExcluded] = useState(new Set())

  const previewMutation = useMutation({
    mutationFn: (f) => previewImport(f),
    onSuccess: (data) => {
      setPreview(data)
      setExcluded(new Set(data.rows.filter((r) => r.errors.length > 0).map((r) => r.rowNumber)))
    },
  })

  const commitMutation = useMutation({
    mutationFn: commitImport,
    onSuccess: (data) => onImported(data.imported, data.skipped),
  })

  const includedRows = preview?.rows.filter((r) => !excluded.has(r.rowNumber)) ?? []

  const toggleRow = (rowNumber) => {
    setExcluded((prev) => {
      const next = new Set(prev)
      if (next.has(rowNumber)) next.delete(rowNumber)
      else next.add(rowNumber)
      return next
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-[rgba(30,40,35,.45)] px-5 py-10">
      <div className="w-full max-w-[860px] overflow-hidden rounded-xl bg-white shadow-[0_20px_60px_rgba(0,0,0,.25)]">
        <div className="flex items-center justify-between border-b border-line bg-[#faf9f4] px-6.5 py-5">
          <h2 className="m-0 font-serif text-lg text-moss-dark">Import Products</h2>
          <button onClick={onClose} className="px-2 py-1 text-[15px] text-moss-dark">
            ✕
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-6.5 py-5.5">
          {!preview && (
            <>
              <p className="mb-4 text-[13px] text-[#6b6656]">
                Upload a CSV file to add products in bulk. Tip: use{' '}
                <span className="font-semibold">Export CSV</span> first to get a file in the exact
                column format.
              </p>
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="mb-4 block rounded-md border border-line bg-[#fdfcf9] px-2.5 py-2 text-[13px]"
              />
              {previewMutation.isError && (
                <div className="mb-4 rounded-md bg-[#fbeae5] px-3 py-2 text-[13px] font-semibold text-[#a13a2c]">
                  {previewMutation.error?.response?.data?.detail ?? 'Could not read file.'}
                </div>
              )}
            </>
          )}

          {preview && (
            <>
              {preview.unmappedColumns.length > 0 && (
                <div className="mb-4 rounded-md bg-[#fef6e6] px-3 py-2 text-[12.5px] text-[#8a6a1f]">
                  Ignored columns (no matching field): {preview.unmappedColumns.join(', ')}
                </div>
              )}
              <div className="mb-3 text-[13px] text-[#6b6656]">
                {includedRows.length} of {preview.rows.length} rows will be imported.
              </div>
              <div className="overflow-hidden rounded-md border border-line">
                <table className="w-full text-[12.5px]">
                  <thead>
                    <tr className="bg-[#faf9f4] text-left text-[11px] uppercase tracking-wide text-[#6b6656]">
                      <th className="px-3 py-2"></th>
                      <th className="px-3 py-2">Row</th>
                      <th className="px-3 py-2">Product</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">Notes</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row) => {
                      const isExcluded = excluded.has(row.rowNumber)
                      const hasError = row.errors.length > 0
                      return (
                        <tr
                          key={row.rowNumber}
                          className={
                            'border-t border-line ' + (isExcluded ? 'opacity-50' : '')
                          }
                        >
                          <td className="px-3 py-2">
                            <input
                              type="checkbox"
                              checked={!isExcluded}
                              onChange={() => toggleRow(row.rowNumber)}
                            />
                          </td>
                          <td className="px-3 py-2">{row.rowNumber}</td>
                          <td className="px-3 py-2">{row.data.product || <em>blank</em>}</td>
                          <td className="px-3 py-2">{row.data.status}</td>
                          <td className="px-3 py-2">
                            {hasError && (
                              <div className="font-semibold text-[#a13a2c]">
                                {row.errors.join(' ')}
                              </div>
                            )}
                            {row.warnings.map((w, i) => (
                              <div key={i} className="text-[#8a6a1f]">
                                {w}
                              </div>
                            ))}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end gap-2.5 border-t border-line bg-[#faf9f4] px-6.5 py-4">
          {preview && (
            <button
              onClick={() => {
                setPreview(null)
                setFile(null)
              }}
              className="rounded-md border border-line bg-white px-3.5 py-2 text-[13px] font-semibold text-moss-dark hover:bg-[#efece0]"
            >
              Choose a different file
            </button>
          )}
          <div className="flex-1" />
          <button
            onClick={onClose}
            className="rounded-md border border-line bg-white px-3.5 py-2 text-[13px] font-semibold text-moss-dark hover:bg-[#efece0]"
          >
            Cancel
          </button>
          {!preview ? (
            <button
              onClick={() => file && previewMutation.mutate(file)}
              disabled={!file || previewMutation.isPending}
              className="rounded-md bg-clay px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-[#9c5518]"
            >
              {previewMutation.isPending ? 'Reading…' : 'Preview'}
            </button>
          ) : (
            <button
              onClick={() => commitMutation.mutate(includedRows)}
              disabled={includedRows.length === 0 || commitMutation.isPending}
              className="rounded-md bg-clay px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-[#9c5518]"
            >
              {commitMutation.isPending ? 'Importing…' : `Import ${includedRows.length} Products`}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
