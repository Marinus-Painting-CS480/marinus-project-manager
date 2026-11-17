// App shell: the frame every page sits in (header on top, page content below).
// Minimal style: white background, black type, one hairline under the header.
// Mobile-first: full width on phones, centered and capped at max-w-3xl on desktop.
// TODO(SCRUM-26): replace hard-coded text with i18n keys once English/Spanish setup lands.
export default function AppShell({ title, children }) {
  return (
    <div className="flex min-h-dvh flex-col bg-white">
      <header className="sticky top-0 z-10 border-b border-ink bg-white">
        <div className="mx-auto flex max-w-3xl items-baseline justify-between px-5 py-5 sm:px-8">
          <span className="text-sm font-bold tracking-[0.25em] uppercase">Marinus</span>
          <span className="text-xs tracking-[0.2em] text-gray-500 uppercase">{title}</span>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 py-10 sm:px-8 sm:py-16">
        {children}
      </main>
    </div>
  )
}
