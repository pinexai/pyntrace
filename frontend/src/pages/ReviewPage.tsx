import { useReviewItems } from '../api/queries'
import DataTable from '../components/shared/DataTable'
import EmptyState from '../components/shared/EmptyState'
import SkeletonLoader from '../components/shared/SkeletonLoader'

export default function ReviewPage() {
  const { data, isLoading } = useReviewItems()
  if (isLoading) return <SkeletonLoader />
  const items = Array.isArray(data) ? data : (data as { pending?: unknown[] })?.pending ?? []
  if (!items.length) return <EmptyState icon="✅" title="Review queue is empty" desc="All annotations are up to date. Nothing needs attention right now." />
  return (
    <div className="p-6 space-y-5">
      <div className="bg-card rounded-xl border border-border p-4">
        <div className="text-sm font-semibold text-t2 mb-3">Annotation Queue ({items.length})</div>
        <DataTable
          rows={items as unknown as Record<string, unknown>[]}
          columns={[
            { key: 'result_id', label: 'Result ID' },
            { key: 'plugin',    label: 'Plugin' },
            { key: 'severity',  label: 'Severity' },
            { key: 'label',     label: 'Label' },
            { key: 'reviewer',  label: 'Reviewer' },
            { key: 'created_at', label: 'Date', render: (v) => new Date((v as number) * 1000).toLocaleDateString() },
          ]}
        />
      </div>
    </div>
  )
}
