interface EmptyStateProps {
  icon: string
  title: string
  desc: string
  cmd?: string | null
  est?: string | null
}

export default function EmptyState({ icon, title, desc, cmd, est }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[40vh] text-center px-8">
      <div className="text-5xl mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-t1 mb-2">{title}</h3>
      <p className="text-sm text-t3 max-w-sm mb-4">{desc}</p>
      {cmd && (
        <div className="bg-surface border border-border rounded-lg px-4 py-2.5 font-mono text-sm text-accent">
          {cmd}
          {est && <span className="text-t3 ml-3 font-sans text-xs">{est}</span>}
        </div>
      )}
    </div>
  )
}
