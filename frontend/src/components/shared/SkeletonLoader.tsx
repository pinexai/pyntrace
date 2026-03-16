export default function SkeletonLoader() {
  return (
    <div className="p-6 space-y-4">
      <div className="skeleton-pulse h-4 w-32 rounded" />
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="skeleton-pulse h-20 rounded-xl" />
        ))}
      </div>
      <div className="skeleton-pulse h-48 rounded-xl" />
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="skeleton-pulse h-10 rounded" />
        ))}
      </div>
    </div>
  )
}
