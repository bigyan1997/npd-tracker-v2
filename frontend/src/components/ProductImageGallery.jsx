import { useState } from 'react'
import { deleteProductImage, uploadProductImage } from '../api/images'
import { ConfirmDialog } from './ConfirmDialog'

// When productId is null (a not-yet-saved new product), selected files are
// staged locally — previewed via an object URL, not actually uploaded —
// since there's no product to attach them to yet. The parent (ProductModal)
// is notified of the staged file list via onPendingChange and uploads them
// itself once the product has been created.
export function ProductImageGallery({ productId, category, label, images, folderUrl, onPendingChange }) {
  const isPending = !productId
  const [localImages, setLocalImages] = useState(() =>
    (images || []).filter((img) => img.category === category),
  )
  // `images` is replaced when the fresh list arrives from Google Drive.
  const [syncedImages, setSyncedImages] = useState(images)
  if (images !== syncedImages) {
    setSyncedImages(images)
    setLocalImages((images || []).filter((img) => img.category === category))
  }
  const [pendingFiles, setPendingFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState(null)

  const setPending = (next) => {
    setPendingFiles(next)
    onPendingChange?.(next.map((p) => p.file))
  }

  const handleFiles = async (fileList) => {
    const files = Array.from(fileList || [])
    if (files.length === 0) return

    if (isPending) {
      const additions = files.map((file) => ({ file, previewUrl: URL.createObjectURL(file) }))
      setPending([...pendingFiles, ...additions])
      return
    }

    setUploading(true)
    setUploadError(null)
    try {
      for (const file of files) {
        const image = await uploadProductImage(productId, category, file)
        setLocalImages((prev) => [...prev, image])
      }
    } catch (err) {
      setUploadError(err?.response?.data?.detail ?? 'Could not upload image.')
    } finally {
      setUploading(false)
    }
  }

  const removePending = (index) => {
    setPending(pendingFiles.filter((_, i) => i !== index))
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await deleteProductImage(productId, deleteTarget.id)
      setLocalImages((prev) => prev.filter((img) => img.id !== deleteTarget.id))
      setDeleteTarget(null)
    } catch (err) {
      setDeleteError(err?.response?.data?.detail ?? 'Could not delete photo.')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <label className="text-[11.5px] font-semibold text-[#6b6656]">
          {label}
          {!isPending && <span className="font-normal text-[#9a9484]"> ({localImages.length})</span>}
        </label>
        {folderUrl && (
          <a
            href={folderUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[11px] text-clay hover:underline"
          >
            Open in Google Drive ↗
          </a>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        {isPending
          ? pendingFiles.map((p, i) => (
              <div key={i} className="group relative h-20 w-20 overflow-hidden rounded-md border border-line">
                <img src={p.previewUrl} alt="" className="h-full w-full object-cover" />
                <button
                  type="button"
                  title="Remove"
                  onClick={() => removePending(i)}
                  className="absolute top-0.5 right-0.5 rounded bg-[rgba(30,40,35,.55)] px-1 text-[11px] text-white opacity-0 group-hover:opacity-100"
                >
                  ✕
                </button>
              </div>
            ))
          : localImages.map((img) => (
              <div key={img.id} className="group relative h-20 w-20 overflow-hidden rounded-md border border-line">
                <a href={img.image} target="_blank" rel="noopener noreferrer" title={img.filename || 'View full size'}>
                  <img src={img.thumb ?? img.image} alt="" loading="lazy" className="h-full w-full object-cover" />
                </a>
                <button
                  type="button"
                  title="Delete image"
                  onClick={() => setDeleteTarget(img)}
                  className="absolute top-0.5 right-0.5 rounded bg-[rgba(30,40,35,.55)] px-1 text-[11px] text-white opacity-0 group-hover:opacity-100"
                >
                  ✕
                </button>
              </div>
            ))}
        <label className="flex h-20 w-20 cursor-pointer flex-col items-center justify-center rounded-md border border-dashed border-line bg-[#fdfcf9] text-[11px] text-off hover:bg-[#f5f3ea]">
          {uploading ? 'Uploading…' : '+ Add'}
          <input
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            disabled={uploading}
            onChange={(e) => {
              handleFiles(e.target.files)
              e.target.value = ''
            }}
          />
        </label>
      </div>
      {!isPending && localImages.length === 0 && (
        <div className="rounded-md bg-[#fef3c7]/60 px-2.5 py-1.5 text-[11.5px] text-[#92400e]">
          No {label.toLowerCase()} yet. Add one here
          {folderUrl ? (
            <>
              , or drop it into{' '}
              <a href={folderUrl} target="_blank" rel="noopener noreferrer" className="font-semibold underline">
                this product&apos;s Google Drive folder
              </a>
              .
            </>
          ) : (
            '.'
          )}
        </div>
      )}
      {isPending && pendingFiles.length > 0 && (
        <div className="text-[11px] text-off">Photos will be uploaded after you save.</div>
      )}
      {uploadError && <div className="text-[11.5px] font-semibold text-[#a13a2c]">{uploadError}</div>}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete photo?"
          message="This photo will also be deleted from Google Drive (it can be restored from the Drive Bin for 30 days). Do you want to continue?"
          errorMessage={deleteError}
          confirming={deleting}
          onCancel={() => {
            setDeleteTarget(null)
            setDeleteError(null)
          }}
          onConfirm={handleDelete}
        />
      )}
    </div>
  )
}
