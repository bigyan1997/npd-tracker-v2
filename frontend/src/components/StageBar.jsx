export function StageBar({ statusOptions, rows, activeStatus, onSelectStatus }) {
  const counts = {}
  statusOptions.forEach((o) => (counts[o] = 0))
  rows.forEach((r) => {
    if (counts[r.status] !== undefined) counts[r.status] += 1
  })

  return (
    <div className="mb-[18px] flex overflow-hidden rounded-[10px] border border-line bg-card">
      {statusOptions.map((o, i) => {
        const isActive = activeStatus === o
        return (
          <button
            key={o}
            type="button"
            onClick={() => onSelectStatus(isActive ? '' : o)}
            title={isActive ? 'Click to clear this filter' : `Filter by "${o}"`}
            className={
              'flex-1 cursor-pointer px-2 py-2.5 text-center text-[11px] text-off transition-colors' +
              (i < statusOptions.length - 1 ? ' border-r border-line' : '') +
              (isActive ? ' bg-[#efece0]' : ' hover:bg-[#f5f3ea]')
            }
          >
            <span className={'block font-serif text-[19px] font-bold ' + (isActive ? 'text-clay' : 'text-moss-dark')}>
              {counts[o]}
            </span>
            {o}
          </button>
        )
      })}
    </div>
  )
}
