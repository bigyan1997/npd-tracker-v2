import { useState } from 'react'
import { deleteProductImage, uploadProductImage } from '../api/images'
import { ConfirmDialog } from './ConfirmDialog'

export function ProductImageGallery({ productId, category, label, images }) {
  const [localImages, setLocalImages] = useState(() =>
    (images || []).filter((img) => img.category === category),
  )
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const handleFiles = async (fileList) => {
    const files = Array.from(fileList || [])
    if (files.length === 0) return
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

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteProductImage(productId, deleteTarget.id)
      setLocalImages((prev) => prev.filter((img) => img.id !== deleteTarget.id))
      setDeleteTarget(null)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <label className="text-[11.5px] font-semibold text-[#6b6656]">{label}</label>
      <div className="flex flex-wrap gap-2">
        {localImages.map((img) => (
          <div key={img.id} className="group relative h-20 w-20 overflow-hidden rounded-md border border-line">
            <img src={img.image} alt="" className="h-full w-full object-cover" />
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
      {uploadError && <div className="text-[11.5px] font-semibold text-[#a13a2c]">{uploadError}</div>}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete image?"
          message="This photo will be removed. This can't be undone."
          confirming={deleting}
          onCancel={() => setDeleteTarget(null)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  )
}
