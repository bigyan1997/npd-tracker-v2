import { useEffect, useRef, useState } from 'react'
import { AddSuggestionDialog } from './AddSuggestionDialog'
import { ConfirmDialog } from './ConfirmDialog'
import { YesNoToggle } from './YesNoToggle'

const inputClass =
  'rounded-md border border-line bg-[#fdfcf9] px-2.5 py-2 text-[13.5px] font-sans'

function ComboField({ value, onChange, suggestions, placeholder, onAddNew, onRenameItem, onDeleteItem }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [renameTarget, setRenameTarget] = useState(null)
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [deleteError, setDeleteError] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const containerRef = useRef(null)

  const handleDelete = async () => {
    if (!deleteTarget || !onDeleteItem) return
    setDeleting(true)
    setDeleteError(null)
    try {
      await onDeleteItem(deleteTarget)
      if (value === deleteTarget) onChange('')
      setDeleteTarget(null)
    } catch (err) {
      setDeleteError(err?.response?.data?.detail ?? 'Could not delete — try again.')
    } finally {
      setDeleting(false)
    }
  }

  useEffect(() => {
    if (!open) return
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const filtered = query.trim()
    ? suggestions.filter((s) => s.toLowerCase().includes(query.trim().toLowerCase()))
    : suggestions

  const alreadyExists = suggestions.some((s) => s.toLowerCase() === value.trim().toLowerCase())

  return (
    <div ref={containerRef} className="relative">
      <div className="flex gap-1.5">
        <div className="relative flex-1">
          <input
            type="text"
            value={value}
            readOnly={alreadyExists}
            onChange={(e) => {
              onChange(e.target.value)
              setQuery(e.target.value)
              setOpen(true)
            }}
            onFocus={() => {
              setQuery('')
              setOpen(true)
            }}
            placeholder={placeholder ?? ''}
            className={
              inputClass +
              ' w-full' +
              (alreadyExists ? ' cursor-default bg-[#f2f0e6] pr-7' : '')
            }
          />
          {alreadyExists && (
            <button
              type="button"
              title="Clear"
              onClick={() => {
                onChange('')
                setQuery('')
              }}
              className="absolute top-1/2 right-1.5 -translate-y-1/2 rounded px-1 text-[14px] text-[#9a9484] hover:text-[#a13a2c]"
            >
              ×
            </button>
          )}
        </div>
        {onAddNew && (
          <button
            type="button"
            title="Add a new supplier"
            onClick={() => {
              setOpen(false)
              setAddDialogOpen(true)
            }}
            className="rounded-md border border-line bg-[#fdfcf9] px-3 text-[15px] font-bold text-moss-dark hover:bg-[#efece0] disabled:cursor-not-allowed disabled:opacity-40"
          >
            +
          </button>
        )}
      </div>
      {addDialogOpen && onAddNew && (
        <AddSuggestionDialog
          title="Add Supplier"
          // Prefill only a name that isn't in the list yet; when the box
          // already holds a known supplier, start blank for a new one.
          initialValue={alreadyExists ? '' : value}
          existing={suggestions}
          onClose={() => setAddDialogOpen(false)}
          onConfirm={async (name) => {
            await onAddNew(name)
            onChange(name)
          }}
        />
      )}
      {renameTarget && onRenameItem && (
        <AddSuggestionDialog
          title="Rename Supplier"
          initialValue={renameTarget}
          existing={suggestions.filter((s) => s !== renameTarget)}
          blockDuplicates
          confirmLabel="Save"
          savingLabel="Saving…"
          onClose={() => setRenameTarget(null)}
          onConfirm={async (name) => {
            await onRenameItem(renameTarget, name)
            if (value === renameTarget) onChange(name)
          }}
        />
      )}
      {deleteTarget && (
        <ConfirmDialog
          title="Delete supplier?"
          message={`Delete "${deleteTarget}" from the supplier list? This can't be undone.`}
          errorMessage={deleteError}
          confirming={deleting}
          onCancel={() => {
            setDeleteTarget(null)
            setDeleteError(null)
          }}
          onConfirm={handleDelete}
        />
      )}
      {open && filtered.length > 0 && (
        <div className="absolute z-10 mt-1 max-h-48 w-full overflow-y-auto rounded-md border border-line bg-white shadow-[0_4px_14px_rgba(30,40,35,.15)]">
          {filtered.map((s) => (
            <div
              key={s}
              onMouseDown={(e) => {
                e.preventDefault()
                onChange(s)
                setOpen(false)
              }}
              className="flex cursor-pointer items-center justify-between gap-2 px-2.5 py-1.5 text-[13.5px] hover:bg-[#f5f3ea]"
            >
              <span className="flex-1">{s}</span>
              {onRenameItem && (
                <button
                  type="button"
                  title="Rename supplier"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    setOpen(false)
                    setRenameTarget(s)
                  }}
                  className="shrink-0 rounded px-1 text-[#c9c4b3] hover:text-moss-dark"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="inline-block h-[13px] w-[13px] align-middle"
                  >
                    <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
                  </svg>
                </button>
              )}
              {onDeleteItem && (
                <button
                  type="button"
                  title="Delete supplier"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    setDeleteTarget(s)
                    setDeleteError(null)
                  }}
                  className="shrink-0 rounded px-1 text-[#c9c4b3] hover:text-[#a13a2c]"
                >
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="inline-block h-[13px] w-[13px] align-middle"
                  >
                    <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6h16Z" />
                  </svg>
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function DynamicField({
  field,
  value,
  onChange,
  suggestions,
  onAddSuggestion,
  onRenameSuggestion,
  onDeleteSuggestion,
}) {
  if (field.type === 'yn') {
    return <YesNoToggle value={value} onChange={onChange} />
  }
  if (field.type === 'select') {
    return (
      <select value={value} onChange={(e) => onChange(e.target.value)} className={inputClass}>
        <option value=""></option>
        {(field.options ?? []).map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    )
  }
  if (field.type === 'combo') {
    return (
      <ComboField
        value={value}
        onChange={onChange}
        suggestions={suggestions ?? []}
        placeholder={field.placeholder}
        onAddNew={onAddSuggestion}
        onRenameItem={onRenameSuggestion}
        onDeleteItem={onDeleteSuggestion}
      />
    )
  }
  if (field.type === 'textarea') {
    return (
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.placeholder ?? ''}
        className={inputClass + ' min-h-[56px] resize-y'}
      />
    )
  }
  if (field.type === 'date') {
    // Storage/wire format is already ISO (yyyy-mm-dd), same as this input's
    // native format — no conversion needed (see lib/dates.js).
    return (
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
      />
    )
  }
  if (field.type === 'number') {
    return (
      <input
        type="number"
        step={field.step ?? '1'}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={inputClass}
      />
    )
  }
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={field.placeholder ?? ''}
      className={inputClass}
    />
  )
}
