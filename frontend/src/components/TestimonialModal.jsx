import { useState } from 'react'
import { X, Star } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'

export default function TestimonialModal({ triggerEvent, onClose }) {
  const [rating, setRating] = useState(0)
  const [hovered, setHovered] = useState(0)
  const [quote, setQuote] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (rating === 0) { toast.error('Selecione uma nota'); return }
    if (quote.trim().length < 10) { toast.error('Conte um pouco mais (mínimo 10 caracteres)'); return }

    setLoading(true)
    try {
      await api.post('/testimonials', { rating, quote: quote.trim(), trigger_event: triggerEvent })
      toast.success('Obrigado pelo seu feedback!')
      onClose()
    } catch (err) {
      if (err.response?.status === 409) {
        onClose() // Already submitted, silently close
      } else {
        toast.error('Erro ao enviar avaliação')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center px-4" onClick={onClose} />
      <div className="fixed inset-0 z-50 flex items-center justify-center px-4 pointer-events-none">
        <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md pointer-events-auto" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-between p-5 border-b border-slate-100">
            <div>
              <p className="font-semibold text-slate-800">Como está sendo sua experiência?</p>
              <p className="text-xs text-slate-400 mt-0.5">Seu feedback nos ajuda a melhorar</p>
            </div>
            <button onClick={onClose} className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-50">
              <X className="w-4 h-4" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-5 space-y-4">
            {/* Star rating */}
            <div>
              <p className="text-sm font-medium text-slate-700 mb-2">Sua nota</p>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setRating(n)}
                    onMouseEnter={() => setHovered(n)}
                    onMouseLeave={() => setHovered(0)}
                    className="p-0.5 focus:outline-none"
                  >
                    <Star
                      className="w-8 h-8 transition-colors"
                      fill={(hovered || rating) >= n ? '#f59e0b' : 'none'}
                      stroke={(hovered || rating) >= n ? '#f59e0b' : '#cbd5e1'}
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Quote */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">
                O que você diria para outros anfitriões?
              </label>
              <textarea
                className="input resize-none"
                rows={3}
                placeholder="Ex: O HostFlow reduziu meu tempo de resposta a zero..."
                value={quote}
                onChange={(e) => setQuote(e.target.value)}
                maxLength={500}
              />
              <p className="text-xs text-slate-400 mt-1 text-right">{quote.length}/500</p>
            </div>

            <div className="flex gap-3">
              <button type="button" onClick={onClose} className="btn-secondary flex-1">
                Agora não
              </button>
              <button type="submit" className="btn-primary flex-1" disabled={loading}>
                {loading ? 'Enviando...' : 'Enviar avaliação'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
