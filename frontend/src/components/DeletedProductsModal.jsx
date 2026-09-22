import { useMutation, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchDeletedProducts, restoreProduct } from '../api/products'

export function DeletedProductsModal({ onClose, onRestored }) {
  const [restoredIds, setRestoredIds] = useState(new Set())
  const deletedQuery = useQuery({ queryKey: ['deletedProducts'], queryFn: fetchDeletedProducts })
  const restoreMutation = useMutation({
    mutationFn: restoreProduct,
    onSuccess: (record, auditId) => {
      setRestoredIds((prev) => new Set(prev).add(auditId))
      onRestored(record.product || 'Product')
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-[rgba(30,40,35,.45)] px-5 py-10">
      <div className="w-full max-w-[600px] overflow-hidden rounded-xl bg-white shadow-[0_20px_60px_rgba(0,0,0,.25)]">
        <div className="flex items-center justify-between border-b border-line bg-[#faf9f4] px-6.5 py-5">
          <h2 className="m-0 font-serif text-lg text-moss-dark">Recently Deleted</h2>
          <button onClick={onClose} className="px-2 py-1 text-[15px] text-moss-dark">
            ✕
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-6.5 py-5.5">
          {deletedQuery.isLoading && <div className="text-[13px] text-[#6b6656]">Loading…</div>}
          {deletedQuery.data && deletedQuery.data.length === 0 && (
            <div className="text-[13px] text-[#6b6656]">Nothing's been deleted recently.</div>
          )}
          {deletedQuery.data && deletedQuery.data.length > 0 && (
            <div className="overflow-hidden rounded-md border border-line">
              <table className="w-full text-[13px]">
                <thead>
                  <tr className="bg-[#faf9f4] text-left text-[11px] uppercase tracking-wide text-[#6b6656]">
                    <th className="px-3 py-2">Product</th>
                    <th className="px-3 py-2">Deleted by</th>
                    <th className="px-3 py-2">Deleted at</th>
                    <th className="px-3 py-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {deletedQuery.data.map((d) => (
                    <tr key={d.auditId} className="border-t border-line">
                      <td className="px-3 py-2 font-semibold">{d.productName || '(untitled)'}</td>
                      <td className="px-3 py-2">{d.deletedBy}</td>
                      <td className="px-3 py-2">{new Date(d.deletedAt).toLocaleString()}</td>
                      <td className="px-3 py-2 text-right">
                        <button
                          onClick={() => restoreMutation.mutate(d.auditId)}
                          disabled={restoreMutation.isPending || restoredIds.has(d.auditId)}
                          className="rounded-md border border-line bg-white px-2.5 py-1 text-[12px] font-semibold text-moss-dark hover:bg-[#efece0] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {restoredIds.has(d.auditId) ? 'Restored ✓' : 'Restore'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2.5 border-t border-line bg-[#faf9f4] px-6.5 py-4">
          <button
            onClick={onClose}
            className="rounded-md border border-line bg-white px-3.5 py-2 text-[13px] font-semibold text-moss-dark hover:bg-[#efece0]"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}
