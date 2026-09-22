export function Toast({ message, isError }) {
  if (!message) return null
  return (
    <div
      className={
        'fixed bottom-5.5 right-5.5 z-100 rounded-lg px-4.5 py-3 text-[13px] text-white shadow-[0_1px_2px_rgba(30,40,35,.06),0_4px_14px_rgba(30,40,35,.05)]' +
        (isError ? ' bg-[#8a2c22]' : ' bg-moss-dark')
      }
    >
      {message}
    </div>
  )
}
