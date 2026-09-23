import { ProductRow } from './ProductRow'

// Table columns are driven by the schema's "dashboard" flag, not hardcoded —
// this order is just a sensible reading order for the ones we expect. Any
// dashboard field not listed here still won't appear (falls back to the
// edit form / admin), and any listed field that's no longer flagged
// "dashboard" in the schema is automatically dropped.
const BEFORE_PIPELINE = ['date', 'product', 'supplier', 'status', 'active']
const AFTER_PIPELINE = ['imagesLocation', 'nutritionalsReceived', 'nutritionalsACP', 'cost', 'plannedLaunch']

export function ProductTable({ rows, fields, filtered, onClearFilters, sortKey, sortDir, onSort, onOpen, onDelete }) {
  const dashboardByKey = new Map(fields.filter((f) => f.dashboard && !f.pipeline).map((f) => [f.key, f]))
  const before = BEFORE_PIPELINE.map((k) => dashboardByKey.get(k)).filter(Boolean)
  const after = AFTER_PIPELINE.map((k) => dashboardByKey.get(k)).filter(Boolean)
  const columns = [...before, ...after]
  const pipelineFields = fields.filter((f) => f.pipeline)

  if (rows.length === 0 && filtered) {
    return (
      <div className="py-15 text-center text-off">
        <h3 className="mb-1.5 text-moss-dark">0 products found</h3>
        <div>
          Nothing matches your search or filters.{' '}
          <button onClick={onClearFilters} className="text-clay underline">
            Clear search and filters
          </button>
        </div>
      </div>
    )
  }
  if (rows.length === 0) {
    return (
      <div className="py-15 text-center text-off">
        <h3 className="mb-1.5 text-moss-dark">No products yet</h3>
        <div>Click "+ New Product" to get started.</div>
      </div>
    )
  }

  const thClass =
    'border-b border-line bg-[#efece0] px-3 py-2.5 text-left text-[11px] tracking-wide text-[#6b6656] uppercase whitespace-nowrap'
  const sortableThClass = thClass + ' cursor-pointer select-none hover:bg-[#e6e2d3]'

  const renderSortableTh = (f) => (
    <th key={f.key} className={sortableThClass} onClick={() => onSort(f.key)}>
      {f.tableLabel ?? f.label}
      {sortKey === f.key && <span className="ml-1">{sortDir === 'asc' ? '▲' : '▼'}</span>}
    </th>
  )

  return (
    <div className="overflow-x-auto rounded-[10px] bg-card shadow-[0_1px_2px_rgba(30,40,35,.06),0_4px_14px_rgba(30,40,35,.05)]">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            {before.map(renderSortableTh)}
            <th className={thClass}>Checklist</th>
            <th className={thClass} title="P = product photos · N = nutrition label photos">Photos</th>
            {after.map(renderSortableTh)}
            <th className={thClass} />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <ProductRow
              key={row.id}
              row={row}
              columns={columns}
              beforeCount={before.length}
              pipelineFields={pipelineFields}
              onOpen={() => onOpen(row)}
              onDelete={() => onDelete(row)}
            />
          ))}
        </tbody>
      </table>
    </div>
  )
}
