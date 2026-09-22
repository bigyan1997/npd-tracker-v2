export function StageBar({ statusOptions, rows }) {
  const counts = {}
  statusOptions.forEach((o) => (counts[o] = 0))
  rows.forEach((r) => {
    if (counts[r.status] !== undefined) counts[r.status] += 1
  })

  return (
    <div className="mb-[18px] flex overflow-hidden rounded-[10px] border border-line bg-card">
      {statusOptions.map((o, i) => (
        <div
          key={o}
          className={
            'flex-1 px-2 py-2.5 text-center text-[11px] text-off' +
            (i < statusOptions.length - 1 ? ' border-r border-line' : '')
          }
        >
          <span className="block font-serif text-[19px] font-bold text-moss-dark">
            {counts[o]}
          </span>
          {o}
        </div>
      ))}
    </div>
  )
}
