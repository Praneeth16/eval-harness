import Link from "next/link";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/runs", label: "Runs" },
  { href: "/detection", label: "Detection" },
  { href: "/clusters", label: "Clusters" },
  { href: "/optimize", label: "Optimize" },
  { href: "/pareto", label: "Pareto" },
  { href: "/portability", label: "Portability" },
  { href: "/prompt-diff", label: "Prompts" },
];

export function Sidebar() {
  return (
    <aside className="w-[240px] shrink-0 border-r border-line bg-canvas-surface/40 backdrop-blur-sm">
      <div className="sticky top-0 flex flex-col h-screen">
        <div className="px-6 py-6 border-b border-line">
          <Link href="/" className="block">
            <div className="font-display text-title leading-none tracking-tight">
              eval-harness
            </div>
            <div className="mt-1 text-ui-sm text-ink-muted">
              agents learn from their own failures
            </div>
          </Link>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block px-3 py-2 text-ui text-ink-secondary rounded-md hover:bg-canvas-elevated hover:text-ink-primary transition-colors duration-micro"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="px-6 py-4 border-t border-line text-ui-sm text-ink-muted">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-improved animate-pulse" />
            <span className="font-mono tnum">v0.1.0</span>
          </div>
        </div>
      </div>
    </aside>
  );
}
