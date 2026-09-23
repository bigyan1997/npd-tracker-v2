import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { logout, me } from './api/auth'
import { uploadProductImage } from './api/images'
import { fetchLinks } from './api/links'
import { createProduct, deleteProduct, fetchProduct, fetchProducts, updateProduct } from './api/products'
import { fetchSchema } from './api/schema'
import { fetchSuppliers } from './api/suppliers'
import { PHOTO_FILTERS, photoCounts } from './lib/photos'
import { DeletedProductsModal } from './components/DeletedProductsModal'
import { LoginPage } from './components/LoginPage'
import { ProductModal } from './components/ProductModal'
import { ProductTable } from './components/ProductTable'
import { StageBar } from './components/StageBar'
import { Toast } from './components/Toast'
import { Toolbar } from './components/Toolbar'
import { TopBar } from './components/TopBar'
import { UpdateBanner } from './components/UpdateBanner'

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

function ResultCount({ count, search, filtered, onClear }) {
  const noun = count === 1 ? 'product' : 'products'
  return (
    <div className="mb-2.5 flex items-center gap-2 text-[12.5px] text-[#6b6656]" aria-live="polite">
      {filtered ? (
        <>
          <span>
            <strong className={count === 0 ? 'text-[#a13a2c]' : 'text-moss-dark'}>
              {count} {noun} found
            </strong>
            {search.trim() && <> for &ldquo;{search.trim()}&rdquo;</>}
          </span>
          <button onClick={onClear} className="text-clay underline-offset-2 hover:underline">
            Clear
          </button>
        </>
      ) : (
        <span>
          {count} {noun}
        </span>
      )}
    </div>
  )
}

function MainApp({ username }) {
  const queryClient = useQueryClient()
  const { toast, show } = useToast()

  const [search, setSearch] = useState('')
  const [supplier, setSupplier] = useState('')
  const [status, setStatus] = useState('')
  const [active, setActive] = useState('')
  const [photos, setPhotos] = useState('')
  const [modalOpen, setModalOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState(null)
  const [modalError, setModalError] = useState(null)
  const [modalConflict, setModalConflict] = useState(false)
  const [deletedModalOpen, setDeletedModalOpen] = useState(false)
  const [sortKey, setSortKey] = useState(null)
  const [sortDir, setSortDir] = useState('asc')

  const schemaQuery = useQuery({ queryKey: ['schema'], queryFn: fetchSchema })
  const linksQuery = useQuery({ queryKey: ['links'], queryFn: fetchLinks, staleTime: Infinity })
  const suppliersQuery = useQuery({ queryKey: ['suppliers'], queryFn: fetchSuppliers })
  const productsQuery = useQuery({
    queryKey: ['products', { search, status, active, supplier }],
    queryFn: () => fetchProducts({ search, status, active, supplier }),
    enabled: Boolean(schemaQuery.data),
    // Everyone shares one login on several devices — keep the list current
    // without a manual refresh. Open edit forms aren't affected.
    refetchInterval: 20 * 1000,
    // Keep showing the last results while a new search loads, instead of
    // flashing "0 products found" on every keystroke.
    placeholderData: keepPreviousData,
  })

  const statusOptions = useMemo(
    () => schemaQuery.data?.fields.find((f) => f.key === 'status')?.options ?? [],
    [schemaQuery.data],
  )

  const sortedRows = useMemo(() => {
    const photoFilter = PHOTO_FILTERS[photos]
    const rows = (productsQuery.data ?? []).filter((row) => !photoFilter || photoFilter(photoCounts(row)))
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
  }, [productsQuery.data, schemaQuery.data, sortKey, sortDir, photos])

  const isFiltered = Boolean(search.trim() || supplier || status || active || photos)
  const clearFilters = () => {
    setSearch('')
    setSupplier('')
    setStatus('')
    setActive('')
    setPhotos('')
  }

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
    // expectedUpdatedAt lets the server refuse to overwrite a change someone
    // else saved after this form was opened; `force` ("Save mine anyway") omits it.
    mutationFn: ({ id, data, force }) =>
      updateProduct(id, { ...data, expectedUpdatedAt: force ? '' : editingRecord?.lastEditedAt }),
    onSuccess: () => {
      invalidateProducts()
      setModalOpen(false)
      show('Product updated.')
    },
    onError: (err) => {
      setModalError(err?.response?.data?.detail ?? 'Save failed.')
      setModalConflict(err?.response?.status === 409)
    },
  })

  const loadLatestVersion = async () => {
    try {
      setEditingRecord(await fetchProduct(editingRecord.id))
      setModalError(null)
      setModalConflict(false)
      invalidateProducts()
    } catch {
      setModalError('Could not load the latest version — it may have been deleted.')
      setModalConflict(false)
    }
  }

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
    setModalConflict(false)
    setModalOpen(true)
  }
  const openEdit = (row) => {
    setEditingRecord(row)
    setModalError(null)
    setModalConflict(false)
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
    setModalConflict(false)
    if (editingRecord) {
      updateMutation.mutate({ id: editingRecord.id, data })
    } else {
      createMutation.mutate({ data, images })
    }
  }

  if (schemaQuery.isLoading) return null

  return (
    <div className="min-h-screen bg-paper">
      <UpdateBanner />
      <TopBar username={username} links={linksQuery.data} onLogout={() => logoutMutation.mutate()} />
      <div className="px-7 py-5.5 pb-15">
        {schemaQuery.data && <StageBar statusOptions={statusOptions} rows={productsQuery.data ?? []} />}
        <Toolbar
          search={search}
          onSearchChange={setSearch}
          supplier={supplier}
          onSupplierChange={setSupplier}
          suppliers={suppliersQuery.data ?? []}
          status={status}
          onStatusChange={setStatus}
          active={active}
          onActiveChange={setActive}
          photos={photos}
          onPhotosChange={setPhotos}
          statusOptions={statusOptions}
          onShowDeleted={() => setDeletedModalOpen(true)}
          onAdd={openNew}
        />
        {productsQuery.data && (
          <ResultCount
            count={sortedRows.length}
            search={search}
            filtered={isFiltered}
            onClear={clearFilters}
          />
        )}
        {schemaQuery.data && (
          <ProductTable
            rows={sortedRows}
            filtered={isFiltered}
            onClearFilters={clearFilters}
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
          // A new key (after "Load latest version") remounts the form with fresh values.
          key={editingRecord ? `${editingRecord.id}-${editingRecord.lastEditedAt}` : 'new'}
          schema={schemaQuery.data}
          record={editingRecord}
          onClose={() => {
            setModalOpen(false)
            invalidateProducts() // photo counts may have changed
          }}
          onSave={handleSave}
          onDelete={() => editingRecord && deleteMutation.mutate(editingRecord.id)}
          saving={createMutation.isPending || updateMutation.isPending}
          deleting={deleteMutation.isPending}
          errorMessage={modalError}
          conflict={modalConflict}
          onLoadLatest={loadLatestVersion}
          onSaveAnyway={() =>
            updateMutation.mutate({ id: editingRecord.id, data: updateMutation.variables.data, force: true })
          }
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
