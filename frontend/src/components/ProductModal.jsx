import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchProductHistory } from '../api/products'
import { createSupplier, deleteSupplier, fetchSuppliers } from '../api/suppliers'
import { DynamicField } from './DynamicField'
import { ProductImageGallery } from './ProductImageGallery'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export function ProductModal({
  schema,
  record,
  onClose,
  onSave,
  onDelete,
  saving,
  deleting,
  errorMessage,
}) {
  const isEdit = Boolean(record)
  const [view, setView] = useState('form')
  const [values, setValues] = useState(() => {
    const initial = {}
    schema.fields.forEach((f) => {
      if (record) {
        initial[f.key] = record[f.key] ?? (f.type === 'yn' ? false : '')
      } else {
        initial[f.key] = f.type === 'yn' ? false : ''
      }
    })
    if (!record) {
      initial.date = todayIso()
      initial.active = true
    }
    return initial
  })

  const setValue = (key, value) => setValues((v) => ({ ...v, [key]: value }))

  // Only relevant when creating a new product (isEdit === false) — files
  // picked before the product exists are staged here and uploaded by the
  // caller (App.jsx) right after the product is actually created.
  const [pendingImages, setPendingImages] = useState({ product: [], nutrition: [] })

  const queryClient = useQueryClient()
  const suppliersQuery = useQuery({ queryKey: ['suppliers'], queryFn: fetchSuppliers })
  const addSupplierMutation = useMutation({
    mutationFn: createSupplier,
    onSuccess: (names) => queryClient.setQueryData(['suppliers'], names),
  })
  const deleteSupplierMutation = useMutation({
    mutationFn: deleteSupplier,
    onSuccess: (names) => queryClient.setQueryData(['suppliers'], names),
  })
  const historyQuery = useQuery({
    queryKey: ['productHistory', record?.id],
    queryFn: () => fetchProductHistory(record.id),
    enabled: isEdit && view === 'history',
  })

  // Only fields flagged for the dashboard are shown here; everything else is
  // still tracked in `values` above (so it round-trips on save) but is only
  // editable via Django admin.
  const dashboardFields = schema.fields.filter((f) => f.dashboard)
  const dashboardSections = schema.sections.filter((s) =>
    dashboardFields.some((f) => f.section === s),
  )

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-[rgba(30,40,35,.45)] px-5 py-10">
      <div className="w-full max-w-[860px] overflow-hidden rounded-xl bg-white shadow-[0_20px_60px_rgba(0,0,0,.25)]">
        <div className="flex items-center justify-between border-b border-line bg-[#faf9f4] px-6.5 py-5">
          <h2 className="m-0 font-serif text-lg text-moss-dark">
            {isEdit ? `Edit — ${record?.product || ''}` : 'New Product'}
          </h2>
          <div className="flex items-center gap-3">
            {isEdit && (
              <div className="flex rounded-md border border-line overflow-hidden text-[12px] font-semibold">
                <button
                  onClick={() => setView('form')}
                  className={'px-2.5 py-1 ' + (view === 'form' ? 'bg-clay text-white' : 'bg-white text-moss-dark hover:bg-[#efece0]')}
                >
                  Edit
                </button>
                <button
                  onClick={() => setView('history')}
                  className={'px-2.5 py-1 ' + (view === 'history' ? 'bg-clay text-white' : 'bg-white text-moss-dark hover:bg-[#efece0]')}
                >
                  History
                </button>
              </div>
            )}
            <button onClick={onClose} className="px-2 py-1 text-[15px] text-moss-dark">
              ✕
            </button>
          </div>
        </div>

        <div className="max-h-[70vh] overflow-y-auto px-6.5 py-5.5">
          {view === 'history' ? (
            <div className="flex flex-col gap-2">
              {historyQuery.isLoading && <div className="text-[13px] text-[#6b6656]">Loading…</div>}
              {historyQuery.data && historyQuery.data.length === 0 && (
                <div className="text-[13px] text-[#6b6656]">No history yet.</div>
              )}
              {historyQuery.data?.map((h, i) => (
                <div key={i} className="border-b border-[#ece9dd] pb-2 text-[12.5px]">
                  <div className="text-[11px] text-[#9a9484]">
                    {h.changedBy || 'Unknown'} · {new Date(h.changedAt).toLocaleString()}
                  </div>
                  {h.action === 'create' ? (
                    <div>
                      <span className="font-semibold">{h.fieldLabel}</span> set to "{h.newValue}"
                    </div>
                  ) : h.action === 'delete' ? (
                    <div className="font-semibold text-[#a13a2c]">Product deleted</div>
                  ) : (
                    <div>
                      <span className="font-semibold">{h.fieldLabel}</span> changed from "{h.oldValue}" to "
                      {h.newValue}"
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <>
              {errorMessage && (
                <div className="mb-4 rounded-md bg-[#fbeae5] px-3 py-2 text-[13px] font-semibold text-[#a13a2c]">
                  {errorMessage}
                </div>
              )}
              {dashboardSections.map((section) => (
            <div key={section}>
              <div className="mt-5.5 mb-2.5 border-b-2 border-[#f0e2d0] pb-1.5 text-[11px] font-bold tracking-wide text-clay uppercase first:mt-0">
                {section}
              </div>
              <div className="grid grid-cols-2 gap-3.5">
                {dashboardFields
                  .filter((f) => f.section === section)
                  .map((f) => (
                    <div
                      key={f.key}
                      className={'flex flex-col gap-1.5' + (f.type === 'textarea' ? ' col-span-2' : '')}
                    >
                      <label className="text-[11.5px] font-semibold text-[#6b6656]">
                        {f.label}
                        {f.required && <span className="text-[#a13a2c]"> *</span>}
                      </label>
                      <DynamicField
                        field={f}
                        value={values[f.key] ?? ''}
                        onChange={(v) => setValue(f.key, v)}
                        suggestions={f.key === 'supplier' ? suppliersQuery.data : undefined}
                        onAddSuggestion={
                          f.key === 'supplier' ? (name) => addSupplierMutation.mutateAsync(name) : undefined
                        }
                        onDeleteSuggestion={
                          f.key === 'supplier' ? (name) => deleteSupplierMutation.mutateAsync(name) : undefined
                        }
                      />
                    </div>
                  ))}
              </div>
            </div>
              ))}
              <div>
                <div className="mt-5.5 mb-2.5 border-b-2 border-[#f0e2d0] pb-1.5 text-[11px] font-bold tracking-wide text-clay uppercase">
                  Photos
                </div>
                <div className="grid grid-cols-2 gap-5">
                  <ProductImageGallery
                    productId={isEdit ? record.id : null}
                    category="product"
                    label="Product Photos"
                    images={record?.images}
                    onPendingChange={
                      isEdit ? undefined : (files) => setPendingImages((p) => ({ ...p, product: files }))
                    }
                  />
                  <ProductImageGallery
                    productId={isEdit ? record.id : null}
                    category="nutrition"
                    label="Nutrition Label Photos"
                    images={record?.images}
                    onPendingChange={
                      isEdit ? undefined : (files) => setPendingImages((p) => ({ ...p, nutrition: files }))
                    }
                  />
                </div>
              </div>
            </>
          )}
        </div>

        <div className="flex justify-end gap-2.5 border-t border-line bg-[#faf9f4] px-6.5 py-4">
          {view === 'history' ? (
            <button
              onClick={() => setView('form')}
              className="rounded-md border border-line bg-white px-3.5 py-2 text-[13px] font-semibold text-moss-dark hover:bg-[#efece0]"
            >
              Back to Edit
            </button>
          ) : (
            <>
              {isEdit && (
                <button
                  onClick={onDelete}
                  disabled={deleting}
                  className="rounded-md border border-[#e0bdb0] bg-white px-3.5 py-2 text-[13px] font-semibold text-[#a13a2c] hover:bg-[#fbeae5]"
                >
                  {deleting ? 'Deleting…' : 'Delete'}
                </button>
              )}
              <div className="flex-1" />
              <button
                onClick={onClose}
                className="rounded-md border border-line bg-white px-3.5 py-2 text-[13px] font-semibold text-moss-dark hover:bg-[#efece0]"
              >
                Cancel
              </button>
              <button
                onClick={() => onSave(values, isEdit ? undefined : pendingImages)}
                disabled={saving}
                className="rounded-md bg-clay px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-[#9c5518]"
              >
                {saving ? 'Saving…' : 'Save Product'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
