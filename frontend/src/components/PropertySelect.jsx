import { useEffect } from 'react'
import { Building2 } from 'lucide-react'
import useProperties from '../hooks/useProperties'
import clsx from 'clsx'

/**
 * Reusable property selector dropdown.
 * Props:
 *   value        - selected property id (number | null)
 *   onChange     - (id: number | null) => void
 *   placeholder  - text when nothing selected
 *   className
 */
export default function PropertySelect({ value, onChange, placeholder = 'Nenhum imóvel', className }) {
  const { properties, loaded, fetch } = useProperties()

  useEffect(() => {
    if (!loaded) fetch()
  }, [loaded, fetch])

  return (
    <div className={clsx('relative', className)}>
      <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
      <select
        className="input pl-9 appearance-none"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">{placeholder}</option>
        {properties.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
    </div>
  )
}
