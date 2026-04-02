import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, Circle, X, ChevronDown, ChevronUp, Zap, ArrowRight, PartyPopper } from 'lucide-react'
import useOnboarding from '../hooks/useOnboarding'
import clsx from 'clsx'

export default function OnboardingChecklist() {
  const { state, loaded, fetch, skip } = useOnboarding()
  const [collapsed, setCollapsed] = useState(false)
  const [justCompleted, setJustCompleted] = useState(false)
  const prevCompleted = useState(false)

  useEffect(() => {
    if (!loaded) fetch()
  }, [loaded, fetch])

  // Detect completion transition
  useEffect(() => {
    if (state?.completed && !prevCompleted[0]) {
      setJustCompleted(true)
      prevCompleted[1](true)
      // Auto-dismiss celebration after 4s
      const t = setTimeout(() => skip(), 4000)
      return () => clearTimeout(t)
    }
  }, [state?.completed]) // eslint-disable-line react-hooks/exhaustive-deps

  // Hide if not loaded, or already completed (and not in celebration)
  if (!loaded || !state) return null
  if (state.completed && !justCompleted) return null

  const pct = Math.round((state.completed_count / state.total_steps) * 100)

  // Find next pending step
  const nextStep = state.steps.find((s) => !s.done)

  // ── Completion celebration ────────────────────────────────────────────────
  if (justCompleted) {
    return (
      <div className="fixed bottom-5 right-5 z-40 w-72 card shadow-lg border border-green-200 bg-green-50 p-5 text-center">
        <PartyPopper className="w-8 h-8 text-green-500 mx-auto mb-2" />
        <p className="font-bold text-green-800 mb-1">Setup completo!</p>
        <p className="text-xs text-green-600">
          Você está pronto para automatizar suas respostas e economizar horas por semana.
        </p>
      </div>
    )
  }

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
                className="h-full bg-brand-500 rounded-full transition-all duration-500"
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
          {state.steps.map((step) => {
            const isNext = nextStep?.key === step.key

            return (
              <Link
                key={step.key}
                to={step.path}
                className={clsx(
                  'flex items-start gap-3 p-2.5 rounded-lg transition-colors group',
                  step.done
                    ? 'opacity-50 cursor-default pointer-events-none'
                    : isNext
                      ? 'bg-brand-50 border border-brand-100 hover:bg-brand-100'
                      : 'hover:bg-slate-50'
                )}
              >
                <div className="shrink-0 mt-0.5 relative">
                  {step.done ? (
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                  ) : isNext ? (
                    <>
                      <Circle className="w-4 h-4 text-brand-500" />
                      <span className="absolute inset-0 rounded-full animate-ping bg-brand-300 opacity-40" />
                    </>
                  ) : (
                    <Circle className="w-4 h-4 text-slate-300 group-hover:text-slate-400 transition-colors" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className={clsx(
                    'text-xs font-medium leading-snug',
                    step.done ? 'text-slate-400 line-through' : isNext ? 'text-brand-700' : 'text-slate-700'
                  )}>
                    {step.title}
                  </p>
                  {!step.done && (
                    <p className="text-xs text-slate-400 mt-0.5 leading-snug">{step.description}</p>
                  )}
                </div>
                {isNext && !step.done && (
                  <ArrowRight className="w-3.5 h-3.5 text-brand-400 shrink-0 mt-0.5" />
                )}
              </Link>
            )
          })}

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
