import { useState } from 'react'

interface Column<T> {
  key: keyof T | string
  label: string
  render?: (val: unknown, row: T) => React.ReactNode
}

interface DataTableProps<T extends Record<string, unknown>> {
  rows: T[]
  columns: Column<T>[]
  onRowClick?: (row: T) => void
}

export default function DataTable<T extends Record<string, unknown>>({
  rows, columns, onRowClick,
}: DataTableProps<T>) {
  const [filter, setFilter] = useState('')
  const [sort, setSort] = useState<{ col: string; dir: 1 | -1 } | null>(null)

  const filtered = rows.filter(r =>
    !filter || JSON.stringify(r).toLowerCase().includes(filter.toLowerCase())
  )

  const sorted = sort
    ? [...filtered].sort((a, b) => {
        const av = a[sort.col] as string | number
        const bv = b[sort.col] as string | number
        if (av == null) return 1
        if (bv == null) return -1
        return av < bv ? -sort.dir : av > bv ? sort.dir : 0
      })
    : filtered

  return (
    <div>
      <div className="flex items-center gap-3 px-1 mb-3">
        <input
          className="flex-1 bg-surface border border-border rounded-lg px-3 py-1.5 text-sm text-t1 placeholder:text-t3 focus:outline-none focus:border-accent"
          placeholder="Filter…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
          aria-label="Filter table"
        />
        <span className="text-xs text-t3">{sorted.length} rows</span>
      </div>
      <div className="overflow-x-auto rounded-lg border border-border" tabIndex={0} role="region" aria-label="Data table">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-card">
              {columns.map(col => (
                <th
                  key={String(col.key)}
                  scope="col"
                  className="px-4 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-t3 cursor-pointer hover:text-t1 select-none"
                  onClick={() => setSort(s =>
                    s?.col === col.key ? { col: String(col.key), dir: (s.dir === 1 ? -1 : 1) } : { col: String(col.key), dir: 1 }
                  )}
                >
                  {col.label}
                  {sort?.col === col.key && (sort.dir === 1 ? ' ↑' : ' ↓')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr
                key={i}
                className={`border-b border-border/50 ${onRowClick ? 'cursor-pointer hover:bg-white/5' : ''}`}
                onClick={() => onRowClick?.(row)}
              >
                {columns.map(col => (
                  <td key={String(col.key)} className="px-4 py-2.5 text-t1">
                    {col.render
                      ? col.render(row[col.key as keyof T], row)
                      : String(row[col.key as keyof T] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
            {!sorted.length && (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-t3 text-sm">
                  No results
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
