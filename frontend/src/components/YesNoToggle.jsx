export function YesNoToggle({ value, onChange }) {
  const isY = value === true
  return (
    <div className="flex gap-1.5">
      <button
        type="button"
        onClick={() => onChange(true)}
        className={
          'flex-1 rounded-md border px-2 py-1.5 text-xs font-bold ' +
          (isY
            ? 'border-[#bcdcc0] bg-[#e3efe4] text-ok'
            : 'border-line bg-[#fdfcf9] text-off')
        }
      >
        YES
      </button>
      <button
        type="button"
        onClick={() => onChange(false)}
        className={
          'flex-1 rounded-md border px-2 py-1.5 text-xs font-bold ' +
          (!isY
            ? 'border-[#e0cbb0] bg-[#f5eee6] text-[#a06a3a]'
            : 'border-line bg-[#fdfcf9] text-off')
        }
      >
        NO
      </button>
    </div>
  )
}
