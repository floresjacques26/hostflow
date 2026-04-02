import { useEffect, useState } from 'react'
import { Copy, Gift, Check } from 'lucide-react'
import toast from 'react-hot-toast'
import api from '../lib/api'

const APP_URL = typeof window !== 'undefined' ? window.location.origin : 'https://app.hostflow.com'

export default function ReferralCard() {
  const [stats, setStats] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    api.get('/referrals/stats')
      .then(({ data }) => setStats(data))
      .catch(() => {})
  }, [])

  if (!stats) return null

  const referralLink = `${APP_URL}/register?ref=${stats.referral_code}`

  const handleCopy = () => {
    navigator.clipboard.writeText(referralLink)
    setCopied(true)
    toast.success('Link copiado!')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="card p-5 border border-brand-100 bg-gradient-to-br from-brand-50/60 to-white">
      <div className="flex items-start gap-3 mb-4">
        <div className="w-9 h-9 rounded-lg bg-brand-100 flex items-center justify-center shrink-0">
          <Gift className="w-4 h-4 text-brand-600" />
        </div>
        <div>
          <p className="font-semibold text-slate-800 text-sm">Indique amigos e ganhe</p>
          <p className="text-xs text-slate-500 mt-0.5">{stats.reward_description}</p>
        </div>
      </div>

      <div className="flex items-center gap-2 mb-4">
        <div className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-xs text-slate-600 font-mono truncate">
          {referralLink}
        </div>
        <button
          onClick={handleCopy}
          className="shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-lg bg-brand-600 text-white text-xs font-medium hover:bg-brand-700 transition-colors"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copiado' : 'Copiar'}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="bg-white rounded-lg px-3 py-2 border border-slate-100">
          <p className="text-lg font-bold text-slate-800 leading-none">{stats.total_referrals}</p>
          <p className="text-xs text-slate-500 mt-0.5">indicações</p>
        </div>
        <div className="bg-white rounded-lg px-3 py-2 border border-slate-100">
          <p className="text-lg font-bold text-green-600 leading-none">{stats.rewarded_referrals}</p>
          <p className="text-xs text-slate-500 mt-0.5">recompensas ganhas</p>
        </div>
      </div>
    </div>
  )
}
