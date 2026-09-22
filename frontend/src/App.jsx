import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { logout, me } from './api/auth'
import { uploadProductImage } from './api/images'
import { createProduct, deleteProduct, fetchProducts, updateProduct } from './api/products'
import { fetchSchema } from './api/schema'
import { DeletedProductsModal } from './components/DeletedProductsModal'
import { ImportModal } from './components/ImportModal'
import { LoginPage } from './components/LoginPage'
import { ProductModal } from './components/ProductModal'
import { ProductTable } from './components/ProductTable'
import { StageBar } from './components/StageBar'
import { Toast } from './components/Toast'
import { Toolbar } from './components/Toolbar'
import { TopBar } from './components/TopBar'

function useToast() {
  const [toast, setToast] = useState({ message: '', isError: false })
  const show = (message, isError = false) => {
    setToast({ message, isError })
    setTimeout(() => setToast({ message: '', isError: false }), 3200)
  }
  return { toast, show }
}

function App() {
  const meQuery = useQuery({ queryKey: ['me'], queryFn: me })

  if (meQuery.isLoading) return null
  if (meQuery.isError || !meQuery.data) return <LoginPage />
  return <MainApp username={meQuery.data.username} />
}

function MainApp({ username }) {
  const queryClient = useQueryClient()
  const { toast, show } = useToast()

  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [active, setActive] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState(null)
  const [modalError, setModalError] = useState(null)
  const [importModalOpen, setImportModalOpen] = useState(false)
  const [deletedModalOpen, setDeletedModalOpen] = useState(false)
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')

  const schemaQuery = useQuery({ queryKey: ['schema'], queryFn: fetchSchema })
  const productsQuery = useQuery({
    queryKey: ['products', { search, status, active }],
    queryFn: () => fetchProducts({ search, status, active }),
    enabled: Boolean(schemaQuery.data),
  })

  const statusOptions = useMemo(
    () => schemaQuery.data?.fields.find((f) => f.key === 'status')?.options ?? [],
    [schemaQuery.data],
  )

  const sortedRows = useMemo(() => {
    const rows = productsQuery.data ?? []
    const field = schemaQuery.data?.fields.find((f) => f.key === sortKey)
    if (!field) return rows
    const dir = sortDir === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      const av = a[field.key]
      const bv = b[field.key]
      if (field.type === 'yn') return ((av === true) === (bv === true) ? 0 : av ? 1 : -1) * dir
      if (field.type === 'number') return ((parseFloat(av) || 0) - (parseFloat(bv) || 0)) * dir
      // Dates are stored as plain ISO strings (yyyy-mm-dd), which sort
      // correctly with a plain string compare — no parsing needed.
      return String(av || '').localeCompare(String(bv || '')) * dir
    })
  }, [productsQuery.data, schemaQuery.data, sortKey, sortDir])

  const handleSort = (key) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const invalidateProducts = () => queryClient.invalidateQueries({ queryKey: ['products'] })

  const createMutation = useMutation({
    mutationFn: async ({ data, images }) => {
      const product = await createProduct(data)
      let failedUploads = 0
      for (const category of ['product', 'nutrition']) {
        for (const file of images?.[category] ?? []) {
          try {
            await uploadProductImage(product.id, category, file)
          } catch {
            failedUploads += 1
          }
        }
      }
      return { product, failedUploads }
    },
    onSuccess: ({ failedUploads }) => {
      invalidateProducts()
      setModalOpen(false)
      if (failedUploads > 0) {
        show(`Product added, but ${failedUploads} photo${failedUploads === 1 ? '' : 's'} failed to upload.`, true)
      } else {
        show('Product added.')
      }
    },
    onError: (err) => setModalError(err?.response?.data?.detail ?? 'Save failed.'),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => updateProduct(id, data),
    onSuccess: () => {
      invalidateProducts()
      setModalOpen(false)
      show('Product updated.')
    },
    onError: (err) => setModalError(err?.response?.data?.detail ?? 'Save failed.'),
  })

  const deleteMutation = useMutation({
    mutationFn: deleteProduct,
    onSuccess: () => {
      invalidateProducts()
      setModalOpen(false)
      show('Product deleted.')
    },
    onError: () => show('Delete failed.', true),
  })

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSuccess: () => {
      queryClient.setQueryData(['me'], null)
      queryClient.clear()
    },
  })

  const openNew = () => {
    setEditingRecord(null)
    setModalError(null)
    setModalOpen(true)
  }
  const openEdit = (row) => {
    setEditingRecord(row)
    setModalError(null)
    setModalOpen(true)
  }

  const handleSave = (data, images) => {
    const missing = (schemaQuery.data?.fields ?? [])
      .filter((f) => f.required && f.type !== 'yn' && !String(data[f.key] ?? '').trim())
      .map((f) => f.label)
    if (missing.length > 0) {
      setModalError(`${missing.join(', ')} ${missing.length === 1 ? 'is' : 'are'} required.`)
      return
    }
    setModalError(null)
    if (editingRecord) {
      updateMutation.mutate({ id: editingRecord.id, data })
    } else {
      createMutation.mutate({ data, images })
    }
  }

  const handleExport = () => {
    if (!schemaQuery.data || !productsQuery.data) return
    const fields = schemaQuery.data.fields
    const header = ['RecordID', ...fields.map((f) => f.label)]
    const csvRows = [
      header,
      ...productsQuery.data.map((r) => [
        r.id,
        ...fields.map((f) => (f.type === 'yn' ? (r[f.key] ? 'Y' : 'N') : r[f.key] || '')),
      ]),
    ]
    const csv = csvRows
      .map((row) =>
        row
          .map((cell) => {
            const s = String(cell ?? '')
            return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
          })
          .join(','),
      )
      .join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `npd-tracker-${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (schemaQuery.isLoading) return null

  return (
    <div className="min-h-screen bg-paper">
      <TopBar username={username} onLogout={() => logoutMutation.mutate()} />
      <div className="px-7 py-5.5 pb-15">
        {schemaQuery.data && <StageBar statusOptions={statusOptions} rows={productsQuery.data ?? []} />}
        <Toolbar
          search={search}
          onSearchChange={setSearch}
          status={status}
          onStatusChange={setStatus}
          active={active}
          onActiveChange={setActive}
          statusOptions={statusOptions}
          onExport={handleExport}
          onImport={() => setImportModalOpen(true)}
          onShowDeleted={() => setDeletedModalOpen(true)}
          onAdd={openNew}
        />
        {schemaQuery.data && (
          <ProductTable
            rows={sortedRows}
            fields={schemaQuery.data.fields}
            sortKey={sortKey}
            sortDir={sortDir}
            onSort={handleSort}
            onOpen={openEdit}
            onDelete={(row) => deleteMutation.mutate(row.id)}
          />
        )}
      </div>

      {modalOpen && schemaQuery.data && (
        <ProductModal
          schema={schemaQuery.data}
          record={editingRecord}
          onClose={() => setModalOpen(false)}
          onSave={handleSave}
          onDelete={() => editingRecord && deleteMutation.mutate(editingRecord.id)}
          saving={createMutation.isPending || updateMutation.isPending}
          deleting={deleteMutation.isPending}
          errorMessage={modalError}
        />
      )}

      {importModalOpen && (
        <ImportModal
          onClose={() => setImportModalOpen(false)}
          onImported={(count, skipped) => {
            invalidateProducts()
            setImportModalOpen(false)
            const skippedNote = skipped > 0 ? ` (${skipped} skipped — missing/invalid data)` : ''
            show(`Imported ${count} product${count === 1 ? '' : 's'}.${skippedNote}`)
          }}
        />
      )}

      {deletedModalOpen && (
        <DeletedProductsModal
          onClose={() => setDeletedModalOpen(false)}
          onRestored={(name) => {
            invalidateProducts()
            show(`Restored "${name}".`)
          }}
        />
      )}

      <Toast message={toast.message} isError={toast.isError} />
    </div>
  )
}

export default App
