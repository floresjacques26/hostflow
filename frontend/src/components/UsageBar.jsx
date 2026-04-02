import clsx from 'clsx'

export default function UsageBar({ label, used, limit, className }) {
  const isUnlimited = limit === null || limit === undefined
  const pct = isUnlimited ? 0 : Math.min(100, Math.round((used / limit) * 100))
  const isNearLimit = !isUnlimited && pct >= 80
  const isAtLimit = !isUnlimited && pct >= 100

  return (
    <div className={clsx('space-y-1.5', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-slate-600">{label}</span>
        <span className={clsx(
          'font-medium',
          isAtLimit ? 'text-red-600' : isNearLimit ? 'text-orange-500' : 'text-slate-700'
        )}>
          {isUnlimited ? (
            <span className="text-slate-400 font-normal">Ilimitado</span>
          ) : (
            `${used} / ${limit}`
          )}
        </span>
      </div>
      {!isUnlimited && (
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className={clsx(
              'h-full rounded-full transition-all',
              isAtLimit ? 'bg-red-500' : isNearLimit ? 'bg-orange-400' : 'bg-brand-500'
            )}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  )
}
