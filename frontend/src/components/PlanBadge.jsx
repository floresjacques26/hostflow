import clsx from 'clsx'

const PLAN_STYLES = {
  free:     'bg-slate-100 text-slate-600',
  pro:      'bg-brand-100 text-brand-700',
  business: 'bg-purple-100 text-purple-700',
}

const PLAN_LABELS = {
  free:     'Free',
  pro:      'Pro',
  business: 'Business',
}

export default function PlanBadge({ plan, size = 'sm', className }) {
  const style = PLAN_STYLES[plan] || PLAN_STYLES.free
  const label = PLAN_LABELS[plan] || plan

  return (
    <span
      className={clsx(
        'inline-flex items-center font-semibold rounded-full capitalize',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
        style,
        className
      )}
    >
      {label}
    </span>
  )
}
