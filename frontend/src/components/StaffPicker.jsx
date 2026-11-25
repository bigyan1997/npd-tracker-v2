import { useState } from 'react'
import { addStaff, removeStaff } from '../api/staff'
import { ConfirmDialog } from './ConfirmDialog'
import { Toast } from './Toast'

// "Who's working?" — shown after sign-in (everyone shares one login). The
// chosen name is recorded against every change. Removing a name never alters
// past records.
export function StaffPicker({ names, onPick, onChanged }) {
  const [newName, setNewName] = useState('')
  const [error, setError] = useState('')
  const [toRemove, setToRemove] = useState(null)
  const [toast, setToast] = useState('')

  const add = async () => {
    const name = newName.trim().split(/\s+/).join(' ')
    if (!name) return
    try {
      const list = await addStaff(name)
      onChanged(list)
      setNewName('')
      setError('')
      onPick(list.find((n) => n.toLowerCase() === name.toLowerCase()) ?? name)
    } catch (err) {
      setError(err?.response?.data?.detail ?? 'Could not add name.')
    }
  }

  const confirmRemove = async () => {
    if (!toRemove) return
    const name = toRemove
    onChanged(await removeStaff(name))
    setToRemove(null)
    setToast(`Removed "${name}". Their past edits are unchanged.`)
    setTimeout(() => setToast(''), 3500)
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper p-6">
      <div className="w-full max-w-sm rounded-xl border border-line bg-white p-7 shadow-sm">
        <h1 className="m-0 font-serif text-xl font-bold text-moss-dark">Who&apos;s working?</h1>
        <p className="mt-1 mb-4 text-[13px] text-[#5b6a5f]">Pick your name. Your changes will be saved under it.</p>
        <div className="flex flex-col gap-2">
          {names.map((n) => (
            <div key={n} className="flex gap-2">
              <button
                onClick={() => onPick(n)}
                className="flex-1 rounded-md border border-line bg-white px-4 py-2.5 text-left text-sm font-semibold text-moss-dark hover:bg-[#eef1ea]"
              >
                {n}
              </button>
              <button
                onClick={() => setToRemove(n)}
                title={`Remove ${n}`}
                className="rounded-md border border-line bg-white px-3 text-[#8a948c] hover:text-[#a13a2c]"
              >
                ×
              </button>
            </div>
          ))}
          {names.length === 0 && (
            <div className="text-[12.5px] text-[#6b6656]">No names yet — add yours below.</div>
          )}
        </div>
        <div className="mt-4 flex gap-2 border-t border-line pt-4">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()}
            placeholder="New name"
            maxLength={100}
            className="min-w-0 flex-1 rounded-md border border-line px-3 py-2 text-sm"
          />
          <button onClick={add} className="rounded-md bg-moss-dark px-3.5 py-2 text-sm font-semibold text-[#f4f2e9]">
            Add
          </button>
        </div>
        {error && <div className="mt-2 text-[12.5px] text-[#a13a2c]">{error}</div>}
      </div>
      {toRemove && (
        <ConfirmDialog
          title={`Remove ${toRemove}?`}
          message={`${toRemove} will no longer appear in the name list. Products and history are not affected — anything ${toRemove} changed will still show "${toRemove}" as the editor.`}
          confirmLabel="Remove name"
          onConfirm={confirmRemove}
          onCancel={() => setToRemove(null)}
        />
      )}
      <Toast message={toast} isError={false} />
    </div>
  )
}
