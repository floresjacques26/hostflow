import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, Circle, X, ChevronDown, ChevronUp, Zap } from 'lucide-react'
import useOnboarding from '../hooks/useOnboarding'
import clsx from 'clsx'

export default function OnboardingChecklist() {
  const { state, loaded, fetch, skip } = useOnboarding()
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    if (!loaded) fetch()
  }, [loaded, fetch])

  // Hide if not loaded, or already completed
  if (!loaded || !state || state.completed) return null

  const pct = Math.round((state.completed_count / state.total_steps) * 100)

  return (
    <div className="fixed bottom-5 right-5 z-40 w-72 card shadow-lg border border-slate-200">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-100">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-brand-600" />
            <span className="text-sm font-semibold text-slate-800">Primeiros passos</span>
          </div>
          <div className="flex items-center gap-2 mt-1.5">
            <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-brand-500 rounded-full transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs text-slate-500 shrink-0">
              {state.completed_count}/{state.total_steps}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-1 ml-3">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1 text-slate-400 hover:text-slate-600 rounded"
          >
            {collapsed ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
          <button
            onClick={skip}
            className="p-1 text-slate-400 hover:text-slate-600 rounded"
            title="Fechar onboarding"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Steps */}
      {!collapsed && (
        <div className="p-3 space-y-1">
          {state.steps.map((step) => (
            <Link
              key={step.key}
              to={step.path}
              className={clsx(
                'flex items-start gap-3 p-2.5 rounded-lg transition-colors group',
                step.done
                  ? 'opacity-60 cursor-default pointer-events-none'
                  : 'hover:bg-brand-50'
              )}
            >
              <div className="shrink-0 mt-0.5">
                {step.done ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500" />
                ) : (
                  <Circle className="w-4 h-4 text-slate-300 group-hover:text-brand-400 transition-colors" />
                )}
              </div>
              <div>
                <p className={clsx('text-xs font-medium', step.done ? 'text-slate-400 line-through' : 'text-slate-700')}>
                  {step.title}
                </p>
                {!step.done && (
                  <p className="text-xs text-slate-400 mt-0.5">{step.description}</p>
                )}
              </div>
            </Link>
          ))}

          <div className="pt-1">
            <button
              onClick={skip}
              className="w-full text-xs text-slate-400 hover:text-slate-600 py-1 transition-colors"
            >
              Pular setup
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
