interface BadgeProps {
  variant: 'critical' | 'medium' | 'low' | 'info'
  children: React.ReactNode
}

const variantClass: Record<string, string> = {
  critical: 'bg-red-500/20 text-red-300 border-red-500/30',
  medium:   'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
  low:      'bg-green-500/20 text-green-300 border-green-500/30',
  info:     'bg-blue-500/20 text-blue-300 border-blue-500/30',
}

export default function Badge({ variant, children }: BadgeProps) {
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium border ${variantClass[variant]}`}>
      {children}
    </span>
  )
}
