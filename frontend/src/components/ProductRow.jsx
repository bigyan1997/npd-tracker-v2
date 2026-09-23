import { useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { formatDateDisplay } from '../lib/dates'
import { photoCounts } from '../lib/photos'
import { ConfirmDialog } from './ConfirmDialog'

function PipelineChips({ row, pipelineFields }) {
  const [tooltipPos, setTooltipPos] = useState(null)
  const wrapRef = useRef(null)

  return (
    <td className="px-3 py-2.5 text-[13.5px]">
      <div
        ref={wrapRef}
        className="inline-flex items-center gap-1"
        onMouseEnter={() => {
          const rect = wrapRef.current?.getBoundingClientRect()
          if (rect) setTooltipPos({ top: rect.bottom + 6, left: rect.left })
        }}
        onMouseLeave={() => setTooltipPos(null)}
      >
        {pipelineFields.map((f) => {
          const isY = row[f.key] === true
          return (
            <span
              key={f.key}
              className={
                'flex h-5 min-w-5 shrink-0 items-center justify-center rounded px-1 text-[9.5px] font-bold ' +
                (isY ? 'bg-ok text-white' : 'border border-[#c9c4b3] text-[#9a9484]')
              }
            >
              {f.chipLabel ?? f.tableLabel ?? f.label}
            </span>
          )
        })}
      </div>
      {tooltipPos &&
        createPortal(
          <div
            className="fixed z-50 w-64 rounded-md border border-line bg-white p-3 text-[12.5px] shadow-[0_8px_24px_rgba(0,0,0,.2)]"
            style={{ top: tooltipPos.top, left: tooltipPos.left }}
          >
            {pipelineFields.map((f) => {
              const isY = row[f.key] === true
              return (
                <div key={f.key} className="flex items-center justify-between gap-3 py-0.5">
                  <span className="text-[#4a463a]">{f.label}</span>
                  <span className={'font-bold ' + (isY ? 'text-ok' : 'text-[#b03a3a]')}>{isY ? 'Y' : 'N'}</span>
                </div>
              )
            })}
          </div>,
          document.body,
        )}
    </td>
  )
}

function plural(n, word) {
  return `${n} ${word}${n === 1 ? '' : 's'}`
}

// Only a category with *no* photos is flagged — one photo is still progress.
function PhotosCell({ row }) {
  const c = photoCounts(row)
  if (c.product === 0 && c.nutrition === 0) {
    return (
      <td className="px-3 py-2.5 text-[13.5px] whitespace-nowrap">
        <span className="rounded bg-[#fef3c7] px-1.5 py-0.5 text-[10.5px] font-bold text-[#92400e]">No photos</span>
      </td>
    )
  }
  const part = (n, letter, word) => (
    <span className={n === 0 ? 'font-semibold text-[#b45309]' : 'text-[#4a463a]'}>
      <span className="text-[10.5px] font-bold text-[#9a9484]">{letter}</span> {n === 0 ? '—' : n}
      <span className="sr-only"> {plural(n, word)}</span>
    </span>
  )
  const title =
    `${plural(c.product, 'product photo')}, ${plural(c.nutrition, 'nutrition label photo')}` +
    (c.product === 0 ? ' — no product photo yet' : '') +
    (c.nutrition === 0 ? ' — no nutrition label yet' : '')
  return (
    <td className="px-3 py-2.5 text-[13px] whitespace-nowrap" title={title}>
      {part(c.product, 'P', 'product photo')}
      <span className="mx-1 text-[#c9c4b3]">·</span>
      {part(c.nutrition, 'N', 'nutrition label')}
    </td>
  )
}

function Cell({ field, row }) {
  const raw = row[field.key]
  const value = field.type === 'yn' ? '' : raw || ''
  if (field.key === 'product') {
    return (
      <td
        className="max-w-[220px] overflow-hidden px-3 py-2.5 text-[13.5px] text-ellipsis whitespace-nowrap"
        title={value || undefined}
      >
        <strong>{value || '(untitled)'}</strong>
      </td>
    )
  }
  if (field.key === 'status') {
    const stuck = row.stuck === true
    return (
      <td
        className="max-w-[220px] overflow-hidden text-ellipsis whitespace-nowrap px-3 py-2.5 text-[13.5px]"
        title={value || undefined}
      >
        {value}
        {stuck && (
          <span
            title={`In this status for ${row.daysInStatus}+ days`}
            className="ml-1.5 rounded bg-[#fef3c7] px-1.5 py-0.5 text-[10px] font-bold whitespace-nowrap text-[#92400e]"
          >
            ⚠ Stuck
          </span>
        )}
      </td>
    )
  }
  if (field.type === 'yn') {
    const isY = raw === true
    return (
      <td className={'px-3 py-2.5 text-[13.5px] font-bold whitespace-nowrap ' + (isY ? 'text-ok' : 'text-[#b03a3a]')}>
        {isY ? 'Y' : 'N'}
      </td>
    )
  }
  if (field.type === 'date') {
    return <td className="whitespace-nowrap px-3 py-2.5 text-[13.5px]">{formatDateDisplay(value)}</td>
  }
  if (field.type === 'number') {
    return <td className="px-3 py-2.5 text-[13.5px]">{value ? `$${value}` : ''}</td>
  }
  return (
    <td
      className="max-w-[220px] overflow-hidden px-3 py-2.5 text-[13.5px] text-ellipsis whitespace-nowrap"
      title={value || undefined}
    >
      {value}
    </td>
  )
}

export function ProductRow({ row, columns, beforeCount, pipelineFields, onOpen, onDelete }) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const before = columns.slice(0, beforeCount)
  const after = columns.slice(beforeCount)

  return (
    <tr onClick={onOpen} className="cursor-pointer border-b border-[#ece9dd] hover:bg-[#fbfaf5]">
      {before.map((f) => (
        <Cell key={f.key} field={f} row={row} />
      ))}
      <PipelineChips row={row} pipelineFields={pipelineFields} />
      <PhotosCell row={row} />
      {after.map((f) => (
        <Cell key={f.key} field={f} row={row} />
      ))}
      <td className="px-3 py-2.5 text-[13.5px] whitespace-nowrap">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onOpen()
          }}
          className="rounded px-2 py-1 text-[15px] text-moss-dark"
        >
          ✎
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            setConfirmOpen(true)
          }}
          className="rounded px-2 py-1 text-moss-dark"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="inline-block h-[15px] w-[15px] align-middle"
          >
            <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6h16Z" />
          </svg>
        </button>
      </td>
      {confirmOpen && (
        <ConfirmDialog
          title="Delete product?"
          message={`Delete "${row.product || '(untitled)'}"? Its photo folder will also be deleted from Google Drive (it can be restored from the Drive Bin for 30 days). Do you want to continue?`}
          onCancel={() => setConfirmOpen(false)}
          onConfirm={() => {
            setConfirmOpen(false)
            onDelete()
          }}
        />
      )}
    </tr>
  )
}
