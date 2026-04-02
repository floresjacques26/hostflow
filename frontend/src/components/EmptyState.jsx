import { Link } from 'react-router-dom'
import clsx from 'clsx'

/**
 * Reusable empty state panel.
 *
 * Props:
 *   icon        Lucide icon component
 *   title       string
 *   description string
 *   cta         { label, to?, onClick? }   — primary action (link or button)
 *   secondaryCta { label, to?, onClick? }  — optional secondary action
 *   compact     bool  — reduced vertical padding (for sidebars / panels)
 */
export default function EmptyState({ icon: Icon, title, description, cta, secondaryCta, compact }) {
  return (
    <div className={clsx('flex flex-col items-center text-center', compact ? 'py-8 px-4' : 'py-14 px-6')}>
      {Icon && (
        <div className="w-12 h-12 bg-slate-50 rounded-2xl flex items-center justify-center mb-4">
          <Icon className="w-6 h-6 text-slate-300" />
        </div>
      )}
      <p className="font-semibold text-slate-700 mb-1">{title}</p>
      {description && (
        <p className="text-sm text-slate-400 max-w-xs leading-relaxed mb-5">{description}</p>
      )}
      {cta && (
        <div className="flex flex-col items-center gap-2">
          <CtaButton {...cta} primary />
          {secondaryCta && <CtaButton {...secondaryCta} />}
        </div>
      )}
    </div>
  )
}

function CtaButton({ label, to, onClick, primary }) {
  const cls = primary
    ? 'btn-primary inline-flex items-center gap-2 text-sm'
    : 'text-sm text-brand-600 hover:underline'

  if (to) {
    return <Link to={to} className={cls}>{label}</Link>
  }
  return <button onClick={onClick} className={cls}>{label}</button>
}
