import { useState } from 'react'

export function AddSuggestionDialog({ title, initialValue, existing = [], onConfirm, onClose }) {
  const [name, setName] = useState(initialValue)
  const [status, setStatus] = useState('idle')
  const match = existing.find((s) => s.toLowerCase() === name.trim().toLowerCase())

  const handleAdd = async () => {
    if (!name.trim() || status === 'saving') return
    setStatus('saving')
    try {
      await onConfirm(name.trim())
      onClose()
    } catch {
      setStatus('error')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(30,40,35,.45)] px-5"
      onClick={onClose}
    >
      <div
        className="w-full max-w-[380px] rounded-xl bg-white p-6 shadow-[0_20px_60px_rgba(0,0,0,.25)]"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-3 font-serif text-lg text-moss-dark">{title}</h3>
        <input
          autoFocus
          type="text"
          value={name}
          onChange={(e) => {
            setName(e.target.value)
            setStatus('idle')
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleAdd()
          }}
          placeholder="Name"
          className="w-full rounded-md border border-line bg-[#fdfcf9] px-2.5 py-2 text-[13.5px]"
        />
        {match && status !== 'error' && (
          <div className="mt-1.5 text-[11.5px] text-off">"{match}" is already in the list — Add will just select it.</div>
        )}
        {status === 'error' && (
          <div className="mt-1.5 text-[11.5px] font-semibold text-[#a13a2c]">Could not add — try again.</div>
        )}
        <div className="mt-4 flex justify-end gap-2.5">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-line bg-white px-3.5 py-2 text-[13px] font-semibold text-moss-dark hover:bg-[#efece0]"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleAdd}
            disabled={!name.trim() || status === 'saving'}
            className="rounded-md bg-clay px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-[#9c5518] disabled:opacity-60"
          >
            {status === 'saving' ? 'Adding…' : 'Add'}
          </button>
        </div>
      </div>
    </div>
  )
}
