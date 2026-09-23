export function Toolbar({
  search,
  onSearchChange,
  status,
  onStatusChange,
  active,
  onActiveChange,
  photos,
  onPhotosChange,
  statusOptions,
  onExport,
  onImport,
  onShowDeleted,
  onAdd,
}) {
  return (
    <div className="mb-4 flex flex-wrap items-center gap-2.5">
      <input
        type="text"
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search product, supplier, code..."
        className="min-w-[220px] flex-1 rounded-md border border-line bg-white px-3.5 py-2 text-[13.5px]"
      />
      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value)}
        className="rounded-md border border-line bg-white px-2.5 py-2 text-[13px]"
      >
        <option value="">All statuses</option>
        {statusOptions.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
      <select
        value={active}
        onChange={(e) => onActiveChange(e.target.value)}
        className="rounded-md border border-line bg-white px-2.5 py-2 text-[13px]"
      >
        <option value="">Active + Inactive</option>
        <option value="Y">Active only</option>
        <option value="N">Inactive only</option>
      </select>
      <select
        value={photos}
        onChange={(e) => onPhotosChange(e.target.value)}
        className="rounded-md border border-line bg-white px-2.5 py-2 text-[13px]"
      >
        <option value="">All photos</option>
        <option value="missing">Missing photos</option>
        <option value="no-product">No product photos</option>
        <option value="no-nutrition">No nutrition label</option>
      </select>
      <button
        onClick={onExport}
        className="rounded-md border border-line bg-white px-3.5 py-2 text-[13px] font-semibold text-moss-dark hover:bg-[#efece0]"
      >
        Export CSV
      </button>
      <button
        onClick={onImport}
        className="rounded-md border border-line bg-white px-3.5 py-2 text-[13px] font-semibold text-moss-dark hover:bg-[#efece0]"
      >
        Import CSV
      </button>
      <button
        onClick={onShowDeleted}
        className="rounded-md border border-line bg-white px-3.5 py-2 text-[13px] font-semibold text-moss-dark hover:bg-[#efece0]"
      >
        Recently Deleted
      </button>
      <button
        onClick={onAdd}
        className="rounded-md bg-clay px-3.5 py-2 text-[13px] font-semibold text-white hover:bg-[#9c5518]"
      >
        + New Product
      </button>
    </div>
  )
}
