import { useState, useEffect } from "react";
import {
  Zap, Plus, Trash2, Edit2, CheckCircle, XCircle, Clock,
  AlertTriangle, Shield, ChevronDown, ChevronUp, ToggleLeft, ToggleRight,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

const CONTEXT_OPTIONS = [
  { value: "", label: "Qualquer contexto" },
  { value: "checkin", label: "Check-in" },
  { value: "checkout", label: "Check-out" },
  { value: "early_checkin", label: "Check-in antecipado" },
  { value: "late_checkout", label: "Check-out tardio" },
  { value: "house_rules", label: "Regras da casa" },
  { value: "amenities", label: "Comodidades" },
  { value: "wifi", label: "Wi-Fi" },
  { value: "parking", label: "Estacionamento" },
  { value: "pets", label: "Animais" },
  { value: "question", label: "Pergunta geral" },
  { value: "general", label: "Geral" },
];

const CHANNEL_OPTIONS = [
  { value: "", label: "Qualquer canal" },
  { value: "gmail", label: "Gmail" },
  { value: "manual", label: "Manual" },
];

const DECISION_BADGE = {
  sent: { label: "Auto-enviado", color: "bg-green-100 text-green-700", icon: CheckCircle },
  blocked: { label: "Bloqueado", color: "bg-red-100 text-red-700", icon: Shield },
  manual_review: { label: "Revisão manual", color: "bg-yellow-100 text-yellow-700", icon: AlertTriangle },
};

const REASON_LABELS = {
  ok: "Aprovado",
  no_rule: "Sem regra configurada",
  low_confidence: "Confiança baixa",
  no_template: "Template não encontrado",
  risky_keyword: "Palavra-chave de risco",
  blocked_category: "Categoria bloqueada",
  message_too_long: "Mensagem muito longa",
  complaint_sentiment: "Tom de reclamação detectado",
  outside_time_window: "Fora da janela de horário",
};

function StatCard({ label, value, sub, color = "text-gray-900" }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4">
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
    </div>
  );
}

function RuleModal({ rule, onSave, onClose }) {
  const isEdit = !!rule?.id;
  const [form, setForm] = useState({
    context_key: rule?.context_key ?? "",
    channel_type: rule?.channel_type ?? "",
    min_confidence: rule?.min_confidence ?? 0.85,
    require_template_match: rule?.require_template_match ?? true,
    allowed_start_hour: rule?.allowed_start_hour ?? "",
    allowed_end_hour: rule?.allowed_end_hour ?? "",
    active: rule?.active ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const token = localStorage.getItem("token");

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true);
    setError("");
    const body = {
      ...form,
      context_key: form.context_key || null,
      channel_type: form.channel_type || null,
      allowed_start_hour: form.allowed_start_hour !== "" ? Number(form.allowed_start_hour) : null,
      allowed_end_hour: form.allowed_end_hour !== "" ? Number(form.allowed_end_hour) : null,
      min_confidence: Number(form.min_confidence),
    };

    try {
      const url = isEdit
        ? `${API}/auto-send/rules/${rule.id}`
        : `${API}/auto-send/rules`;
      const res = await fetch(url, {
        method: isEdit ? "PATCH" : "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error((await res.json()).detail ?? "Erro");
      const saved = await res.json();
      onSave(saved);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg">
        <div className="flex items-center justify-between p-6 border-b border-gray-100">
          <h2 className="text-lg font-semibold text-gray-900">
            {isEdit ? "Editar regra" : "Nova regra de auto-envio"}
          </h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl font-bold">×</button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Contexto</label>
              <select
                value={form.context_key}
                onChange={e => setForm(f => ({ ...f, context_key: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                {CONTEXT_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Canal</label>
              <select
                value={form.channel_type}
                onChange={e => setForm(f => ({ ...f, channel_type: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              >
                {CHANNEL_OPTIONS.map(o => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confiança mínima: <span className="font-bold text-violet-600">{Math.round(form.min_confidence * 100)}%</span>
            </label>
            <input
              type="range" min="0.5" max="1.0" step="0.05"
              value={form.min_confidence}
              onChange={e => setForm(f => ({ ...f, min_confidence: parseFloat(e.target.value) }))}
              className="w-full accent-violet-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>50% (mais permissivo)</span>
              <span>100% (mais restrito)</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hora início (UTC)</label>
              <input
                type="number" min="0" max="23" placeholder="ex: 8"
                value={form.allowed_start_hour}
                onChange={e => setForm(f => ({ ...f, allowed_start_hour: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Hora fim (UTC)</label>
              <input
                type="number" min="0" max="23" placeholder="ex: 22"
                value={form.allowed_end_hour}
                onChange={e => setForm(f => ({ ...f, allowed_end_hour: e.target.value }))}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-violet-500"
              />
            </div>
          </div>
          <p className="text-xs text-gray-400">Deixe em branco para enviar em qualquer horário.</p>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setForm(f => ({ ...f, require_template_match: !f.require_template_match }))}
              className={`w-10 h-6 rounded-full transition-colors ${form.require_template_match ? "bg-violet-600" : "bg-gray-300"}`}
            >
              <span className={`block w-4 h-4 bg-white rounded-full shadow transition-transform mx-1 ${form.require_template_match ? "translate-x-4" : ""}`} />
            </button>
            <div>
              <p className="text-sm font-medium text-gray-700">Exigir template correspondente</p>
              <p className="text-xs text-gray-400">Bloqueia auto-envio se nenhum template foi aplicado</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setForm(f => ({ ...f, active: !f.active }))}
              className={`w-10 h-6 rounded-full transition-colors ${form.active ? "bg-green-500" : "bg-gray-300"}`}
            >
              <span className={`block w-4 h-4 bg-white rounded-full shadow transition-transform mx-1 ${form.active ? "translate-x-4" : ""}`} />
            </button>
            <p className="text-sm font-medium text-gray-700">{form.active ? "Regra ativa" : "Regra inativa"}</p>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 bg-violet-600 hover:bg-violet-700 disabled:opacity-50 text-white rounded-lg py-2 text-sm font-medium"
            >
              {saving ? "Salvando…" : isEdit ? "Salvar alterações" : "Criar regra"}
            </button>
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">
              Cancelar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function RuleCard({ rule, onEdit, onDelete, onToggle }) {
  const ctx = CONTEXT_OPTIONS.find(o => o.value === rule.context_key)?.label ?? "Qualquer contexto";
  const ch = CHANNEL_OPTIONS.find(o => o.value === rule.channel_type)?.label ?? "Qualquer canal";

  return (
    <div className={`bg-white rounded-xl border p-4 ${rule.active ? "border-gray-200" : "border-gray-100 opacity-60"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <span className="text-xs bg-violet-100 text-violet-700 px-2 py-0.5 rounded-full font-medium">{ctx}</span>
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">{ch}</span>
            {rule.require_template_match && (
              <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">Requer template</span>
            )}
            {!rule.active && (
              <span className="text-xs bg-orange-100 text-orange-600 px-2 py-0.5 rounded-full">Inativa</span>
            )}
          </div>
          <div className="text-sm text-gray-600 space-y-0.5">
            <p>Confiança mínima: <span className="font-semibold">{Math.round(rule.min_confidence * 100)}%</span></p>
            {(rule.allowed_start_hour != null && rule.allowed_end_hour != null) && (
              <p className="flex items-center gap-1">
                <Clock size={12} />
                {rule.allowed_start_hour}h – {rule.allowed_end_hour}h UTC
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={() => onToggle(rule)}
            title={rule.active ? "Desativar" : "Ativar"}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            {rule.active ? <ToggleRight size={18} className="text-green-500" /> : <ToggleLeft size={18} />}
          </button>
          <button
            onClick={() => onEdit(rule)}
            className="p-1.5 rounded-lg hover:bg-gray-100 text-gray-400 hover:text-gray-700"
          >
            <Edit2 size={14} />
          </button>
          <button
            onClick={() => onDelete(rule.id)}
            className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-600"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AutoSend() {
  const [rules, setRules] = useState([]);
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState(null);
  const [showLogs, setShowLogs] = useState(false);
  const [loading, setLoading] = useState(true);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  async function loadAll() {
    setLoading(true);
    try {
      const [rulesRes, statsRes, logsRes] = await Promise.all([
        fetch(`${API}/auto-send/rules`, { headers }),
        fetch(`${API}/auto-send/stats`, { headers }),
        fetch(`${API}/auto-send/logs?limit=20`, { headers }),
      ]);
      if (rulesRes.ok) setRules(await rulesRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
      if (logsRes.ok) setLogs(await logsRes.json());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadAll(); }, []);

  async function handleDelete(id) {
    if (!confirm("Excluir esta regra?")) return;
    await fetch(`${API}/auto-send/rules/${id}`, { method: "DELETE", headers });
    setRules(r => r.filter(x => x.id !== id));
  }

  async function handleToggle(rule) {
    const res = await fetch(`${API}/auto-send/rules/${rule.id}`, {
      method: "PATCH",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ active: !rule.active }),
    });
    if (res.ok) {
      const updated = await res.json();
      setRules(r => r.map(x => x.id === updated.id ? updated : x));
    }
  }

  function handleSaved(saved) {
    setRules(r => {
      const existing = r.find(x => x.id === saved.id);
      return existing ? r.map(x => x.id === saved.id ? saved : x) : [saved, ...r];
    });
    setShowModal(false);
    setEditingRule(null);
  }

  const activeRules = rules.filter(r => r.active);
  const inactiveRules = rules.filter(r => !r.active);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-violet-100 rounded-xl">
            <Zap size={22} className="text-violet-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Auto-envio com guardrails</h1>
            <p className="text-sm text-gray-500">
              Configure quando a IA pode responder automaticamente — com segurança
            </p>
          </div>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
          <StatCard label="Avaliações totais" value={stats.total_evaluations} />
          <StatCard
            label="Auto-enviados"
            value={stats.auto_sent}
            sub={`${stats.auto_send_rate_pct}% de aprovação`}
            color="text-green-600"
          />
          <StatCard label="Bloqueados" value={stats.blocked} color="text-red-600" />
          <StatCard label="Revisão manual" value={stats.manual_review} color="text-yellow-600" />
        </div>
      )}

      {/* Top block reasons */}
      {stats?.top_block_reasons?.length > 0 && (
        <div className="bg-red-50 border border-red-100 rounded-xl p-4 mb-6">
          <p className="text-sm font-semibold text-red-700 mb-3 flex items-center gap-2">
            <Shield size={14} /> Principais motivos de bloqueio
          </p>
          <div className="space-y-1.5">
            {stats.top_block_reasons.map(r => (
              <div key={r.reason_code} className="flex items-center justify-between text-sm">
                <span className="text-red-600">{REASON_LABELS[r.reason_code] ?? r.reason_code}</span>
                <span className="font-semibold text-red-800">{r.count}×</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Rules */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-base font-semibold text-gray-900">
            Regras ativas
            {activeRules.length > 0 && (
              <span className="ml-2 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                {activeRules.length}
              </span>
            )}
          </h2>
          <button
            onClick={() => { setEditingRule(null); setShowModal(true); }}
            className="flex items-center gap-2 bg-violet-600 hover:bg-violet-700 text-white px-3 py-2 rounded-lg text-sm font-medium"
          >
            <Plus size={14} /> Nova regra
          </button>
        </div>

        {loading ? (
          <div className="text-center py-8 text-gray-400 text-sm">Carregando…</div>
        ) : activeRules.length === 0 ? (
          <div className="text-center py-10 bg-gray-50 rounded-xl border border-dashed border-gray-200">
            <Zap size={32} className="mx-auto text-gray-300 mb-3" />
            <p className="text-sm text-gray-500 font-medium mb-1">Nenhuma regra configurada</p>
            <p className="text-xs text-gray-400 max-w-xs mx-auto">
              Crie uma regra para que a IA envie respostas automaticamente em contextos seguros
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeRules.map(rule => (
              <RuleCard
                key={rule.id}
                rule={rule}
                onEdit={r => { setEditingRule(r); setShowModal(true); }}
                onDelete={handleDelete}
                onToggle={handleToggle}
              />
            ))}
          </div>
        )}

        {inactiveRules.length > 0 && (
          <div className="mt-4">
            <p className="text-xs text-gray-400 mb-2">Regras inativas ({inactiveRules.length})</p>
            <div className="space-y-2">
              {inactiveRules.map(rule => (
                <RuleCard
                  key={rule.id}
                  rule={rule}
                  onEdit={r => { setEditingRule(r); setShowModal(true); }}
                  onDelete={handleDelete}
                  onToggle={handleToggle}
                />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Guardrails info box */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
        <p className="text-sm font-semibold text-amber-800 mb-2 flex items-center gap-2">
          <AlertTriangle size={14} /> Categorias sempre bloqueadas
        </p>
        <p className="text-xs text-amber-700 mb-2">
          Mesmo com uma regra ativa, o auto-envio nunca ocorre para estas situações:
        </p>
        <div className="flex flex-wrap gap-1.5">
          {["Cobrança / pagamento", "Reclamação", "Conflito de cancelamento", "Reembolso",
            "Negociação de preço", "Questões legais / segurança", "Intenção mista não clara"
          ].map(cat => (
            <span key={cat} className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
              {cat}
            </span>
          ))}
        </div>
      </div>

      {/* Audit Log */}
      <div>
        <button
          onClick={() => setShowLogs(v => !v)}
          className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900 mb-3"
        >
          {showLogs ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          Histórico de decisões (últimas 20)
        </button>

        {showLogs && (
          <div className="space-y-2">
            {logs.length === 0 ? (
              <p className="text-sm text-gray-400 py-4 text-center">Nenhuma decisão registrada ainda.</p>
            ) : logs.map(log => {
              const badge = DECISION_BADGE[log.decision] ?? DECISION_BADGE.manual_review;
              const Icon = badge.icon;
              return (
                <div key={log.id} className="bg-white border border-gray-100 rounded-lg px-4 py-3 flex items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon size={15} className={badge.color.split(" ")[1]} />
                    <div className="min-w-0">
                      <p className="text-sm text-gray-700">
                        Conversa <span className="font-medium">#{log.thread_id}</span>
                      </p>
                      <p className="text-xs text-gray-400">
                        {REASON_LABELS[log.reason_code] ?? log.reason_code}
                        {log.reason_message && ` — ${log.reason_message}`}
                      </p>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${badge.color}`}>
                      {badge.label}
                    </span>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(log.created_at).toLocaleString("pt-BR")}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Modal */}
      {showModal && (
        <RuleModal
          rule={editingRule}
          onSave={handleSaved}
          onClose={() => { setShowModal(false); setEditingRule(null); }}
        />
      )}
    </div>
  );
}
