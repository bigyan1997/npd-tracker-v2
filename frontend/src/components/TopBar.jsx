export function TopBar({ username, onLogout }) {
  return (
    <div className="flex items-center justify-between border-b-[3px] border-clay bg-moss-dark px-7 py-4 text-[#f4f2e9]">
      <div>
        <h1 className="m-0 font-serif text-xl font-bold tracking-wide">NPD Tracker</h1>
        <div className="mt-0.5 text-[11.5px] tracking-widest text-[#c9d6cb] uppercase">
          Achieve Cafe Provisions — New Product Development
        </div>
      </div>
      <div className="flex items-center gap-2.5">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-[#eef1ea] px-2.5 py-1.5 text-[11px] text-[#4a5a4e]">
          <span className="h-1.5 w-1.5 rounded-full bg-ok" />
          {username}
        </span>
        <button
          onClick={onLogout}
          className="rounded-md border border-[#5c7669] bg-transparent px-3.5 py-2 text-[13px] font-semibold text-[#f4f2e9] hover:bg-[#4a6558]"
        >
          Log out
        </button>
      </div>
    </div>
  )
}
