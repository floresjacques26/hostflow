import { Check, Minus } from 'lucide-react'
import { COMPARISON_ROWS } from '../lib/plans'

/**
 * Full plan comparison table.
 * Derives all content from COMPARISON_ROWS in lib/plans.js.
 */
export default function PlanComparisonTable() {
  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-200">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-4 px-5 text-slate-500 font-medium w-1/2">Recurso</th>
            <th className="text-center py-4 px-4 text-slate-700 font-bold">Free</th>
            <th className="text-center py-4 px-4 text-brand-700 font-bold bg-brand-50">Pro</th>
            <th className="text-center py-4 px-4 text-purple-700 font-bold">Business</th>
          </tr>
        </thead>
        <tbody>
          {COMPARISON_ROWS.map(({ section, rows }) => (
            <>
              <tr key={`section-${section}`} className="bg-slate-50">
                <td
                  colSpan={4}
                  className="py-2.5 px-5 text-xs font-bold text-slate-400 uppercase tracking-wider"
                >
                  {section}
                </td>
              </tr>
              {rows.map((row) => (
                <tr
                  key={row.label}
                  className="border-t border-slate-100 hover:bg-slate-50/50 transition-colors"
                >
                  <td className="py-3.5 px-5 text-slate-700">{row.label}</td>
                  <td className="py-3.5 px-4 text-center">
                    <CellValue value={row.free} />
                  </td>
                  <td className="py-3.5 px-4 text-center bg-brand-50/30">
                    <CellValue value={row.pro} accent="brand" />
                  </td>
                  <td className="py-3.5 px-4 text-center">
                    <CellValue value={row.business} accent="purple" />
                  </td>
                </tr>
              ))}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CellValue({ value, accent }) {
  if (value === true) {
    const color = accent === 'brand'
      ? 'text-brand-600'
      : accent === 'purple'
        ? 'text-purple-600'
        : 'text-green-600'
    return (
      <span className={`flex justify-center ${color}`}>
        <Check className="w-4 h-4" strokeWidth={2.5} />
      </span>
    )
  }
  if (value === false) {
    return (
      <span className="flex justify-center text-slate-300">
        <Minus className="w-4 h-4" />
      </span>
    )
  }
  // String value
  const textColor = accent === 'brand'
    ? 'text-brand-700 font-medium'
    : accent === 'purple'
      ? 'text-purple-700 font-medium'
      : 'text-slate-600'
  return <span className={textColor}>{value}</span>
}
