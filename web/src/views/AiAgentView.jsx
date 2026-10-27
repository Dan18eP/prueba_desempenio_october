import React, { useState, useEffect } from 'react';
import {
  Send,
  Cpu,
  Download,
  RefreshCw,
  Sparkles,
  Database,
  BarChart2,
  AlertCircle,
  CheckCircle,
  FileText
} from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { Bar, Line, Doughnut } from 'react-chartjs-2';
import { api } from '../api';

export default function AiAgentView({ currentUser }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: '¡Hola! Soy SismoWatch AI, tu analista sismológico basado en Qwen 2.5 y motor Dual. Puedo consultar el catálogo de sismos mediante Text-to-SQL y generar gráficos declarativos en tiempo real. ¿En qué puedo asistirte?',
      chart: null,
      sql: null,
      model: 'qwen2.5-coder:3b',
      latency: 12
    }
  ]);
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState(null);
  const [reportWindow, setReportWindow] = useState('24h'); // '24h' | '7d' | '30d'
  const [reportLoading, setReportLoading] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  const loadReport = async (window) => {
    setReportLoading(true);
    try {
      const data = await api.getLatestReport(window);
      setReport(data);
    } catch (err) {
      console.error('Error cargando reporte:', err);
    } finally {
      setReportLoading(false);
    }
  };

  useEffect(() => {
    loadReport(reportWindow);
  }, [reportWindow]);

  const handleSend = async (userText) => {
    const query = userText || prompt;
    if (!query.trim() || loading) return;

    setMessages((prev) => [...prev, { role: 'user', text: query }]);
    setPrompt('');
    setLoading(true);

    try {
      const response = await api.askChat(query);
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: response.answer,
          chart: response.chart,
          sql: response.sql_executed,
          model: response.model_used,
          latency: response.latency_ms,
          fallback: response.fallback_active
        }
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: `Error al procesar la consulta: ${err.message}`,
          chart: null,
          sql: null,
          model: 'error',
          latency: 0
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleRegenerateReport = async () => {
    if (currentUser?.role !== 'admin') {
      setActionMessage({ type: 'error', text: 'Solo administradores pueden regenerar reportes (HTTP 403).' });
      return;
    }
    setRegenerating(true);
    setActionMessage(null);
    try {
      const res = await api.regenerateReport(reportWindow);
      await loadReport(reportWindow);
      setActionMessage({ type: 'success', text: res.message || 'Reporte regenerado exitosamente.' });
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    } finally {
      setRegenerating(false);
    }
  };

  const renderDeclarativeChart = (chart) => {
    if (!chart || chart.type === 'none' || !chart.labels || !chart.datasets) return null;

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#cbd5e1', font: { family: 'monospace', size: 10 } } },
        title: {
          display: !!chart.title,
          text: chart.title || '',
          color: '#e2e8f0',
          font: { family: 'monospace', size: 12, weight: 'bold' }
        }
      },
      scales: chart.type !== 'doughnut' && chart.type !== 'pie' ? {
        x: { ticks: { color: '#94a3b8', font: { family: 'monospace', size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
        y: { beginAtZero: true, ticks: { color: '#94a3b8', font: { family: 'monospace', size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } }
      } : undefined
    };

    return (
      <div className="mt-3 p-3 rounded-xl bg-[#0a0e16] border border-[#262a33] h-52">
        {chart.type === 'bar' && <Bar data={chart} options={chartOptions} />}
        {chart.type === 'line' && <Line data={chart} options={chartOptions} />}
        {(chart.type === 'doughnut' || chart.type === 'pie') && (
          <div className="h-full flex items-center justify-center">
            <Doughnut data={chart} options={chartOptions} />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Left 7 Columns: Text-to-SQL Chat Console */}
      <div className="lg:col-span-7 flex flex-col rounded-2xl bg-[#12161f] border border-[#262a33] p-5 shadow-lg h-[640px]">
        {/* Console Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#262a33]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="text-sm font-bold text-white flex items-center gap-2">
                <span>Consola Analítica SismoWatch AI</span>
                <span className="text-[10px] font-mono bg-indigo-950/60 text-indigo-300 border border-indigo-500/30 px-1.5 py-0.5 rounded">
                  Dual-Engine Qwen2.5
                </span>
              </div>
              <div className="text-[10px] font-mono text-gray-400">
                Text-to-SQL seguro con validación de solo lectura (curated schema)
              </div>
            </div>
          </div>
        </div>

        {/* Suggested Quick Questions */}
        <div className="py-2.5 flex items-center gap-2 overflow-x-auto text-[11px] font-mono border-b border-[#262a33]">
          <span className="text-gray-500 shrink-0">Sugerencias:</span>
          {[
            '¿Hay sismos con alerta de tsunami?',
            'Ver distribución por severidad',
            'Sismos con magnitud mayor a 4',
            '¿Cuáles son las anomalías detectadas?'
          ].map((q, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(q)}
              disabled={loading}
              className="px-2.5 py-1 rounded-lg bg-[#181c24] hover:bg-[#1f2430] border border-[#262a33] text-indigo-300 hover:text-white shrink-0 transition-colors"
            >
              {q}
            </button>
          ))}
        </div>

        {/* Message Log */}
        <div className="flex-1 overflow-y-auto space-y-3.5 py-3 pr-1">
          {messages.map((m, idx) => {
            const isUser = m.role === 'user';
            return (
              <div
                key={idx}
                className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
              >
                <div
                  className={`max-w-[90%] rounded-2xl p-4 text-xs ${
                    isUser
                      ? 'bg-indigo-600 text-white rounded-br-none shadow-md'
                      : 'bg-[#181c24] border border-[#262a33] text-gray-200 rounded-bl-none shadow-sm'
                  }`}
                >
                  <p className="leading-relaxed">{m.text}</p>

                  {/* Render Declarative Chart if present */}
                  {renderDeclarativeChart(m.chart)}

                  {/* Assistant Footer Info */}
                  {!isUser && m.model && (
                    <div className="mt-2 text-[10px] font-mono text-gray-500 flex items-center justify-between">
                      <span>Modelo: {m.model}</span>
                      <span>{m.latency} ms</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {loading && (
            <div className="flex items-center gap-2 text-xs font-mono text-indigo-400 p-2">
              <span className="w-2 h-2 rounded-full bg-indigo-400 animate-ping"></span>
              <span>Procesando consulta Text-to-SQL y renderizando análisis...</span>
            </div>
          )}
        </div>

        {/* Prompt Input Form */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="pt-3 border-t border-[#262a33] flex items-center gap-2"
        >
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={loading}
            placeholder="Pregunta en lenguaje natural sobre sismos, magnitudes o alertas..."
            className="flex-1 px-4 py-2.5 rounded-xl bg-[#0a0e16] border border-[#262a33] text-xs text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 font-mono"
          />
          <button
            type="submit"
            disabled={loading || !prompt.trim()}
            className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>Enviar</span>
          </button>
        </form>
      </div>

      {/* Right 5 Columns: Daily Executive AI Report & Export */}
      <div className="lg:col-span-5 flex flex-col rounded-2xl bg-[#12161f] border border-[#262a33] p-5 shadow-lg h-[640px] overflow-y-auto">
        {/* Report Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#262a33]">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-indigo-400" />
            <div>
              <h3 className="text-sm font-bold text-white">Reporte Ejecutivo Sísmico</h3>
              <div className="text-[10px] font-mono text-gray-400">
                Generado automáticamente cada ciclo por Airflow
              </div>
            </div>
          </div>

          {currentUser?.role === 'admin' && (
            <button
              onClick={handleRegenerateReport}
              disabled={regenerating || reportLoading}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-amber-300 text-xs font-mono transition-colors"
            >
              <RefreshCw className={`w-3 h-3 ${regenerating ? 'animate-spin' : ''}`} />
              <span>Regenerar</span>
            </button>
          )}
        </div>

        {/* Time Window Switcher Tabs */}
        <div className="py-2.5 flex items-center justify-between border-b border-[#262a33] text-xs font-mono">
          <span className="text-gray-400 text-[11px]">Período de Análisis:</span>
          <div className="flex items-center gap-1">
            {[
              { id: '24h', label: '24 Horas' },
              { id: '7d', label: '7 Días' },
              { id: '30d', label: '30 Días / Mes' }
            ].map((win) => (
              <button
                key={win.id}
                onClick={() => setReportWindow(win.id)}
                disabled={reportLoading}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${
                  reportWindow === win.id
                    ? 'bg-indigo-600 text-white font-bold shadow-sm'
                    : 'bg-[#181c24] text-gray-400 hover:text-white border border-[#262a33]'
                }`}
              >
                {win.label}
              </button>
            ))}
          </div>
        </div>

        {actionMessage && (
          <div
            className={`my-3 p-3 rounded-xl border text-xs font-mono flex items-center gap-2 ${
              actionMessage.type === 'error'
                ? 'bg-red-950/40 border-red-500/40 text-red-200'
                : 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200'
            }`}
          >
            {actionMessage.type === 'error' ? <AlertCircle className="w-4 h-4 shrink-0" /> : <CheckCircle className="w-4 h-4 shrink-0" />}
            <span>{actionMessage.text}</span>
          </div>
        )}

        {/* Report Content */}
        {reportLoading ? (
          <div className="flex-1 flex flex-col items-center justify-center text-xs font-mono text-indigo-400 gap-2 p-8">
            <span className="w-3 h-3 rounded-full bg-indigo-400 animate-ping"></span>
            <span>Generando informe analítico ({reportWindow})...</span>
          </div>
        ) : report ? (
          <div className="space-y-4 py-3">
            <div>
              <span className="text-[10px] font-mono uppercase bg-indigo-950/60 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded font-bold">
                EVALUACIÓN DE RIESGO: {report.risk_assessment}
              </span>
              <h4 className="text-base font-bold text-white mt-2 leading-snug">
                {report.title}
              </h4>
              <div className="text-[11px] font-mono text-gray-500 mt-0.5">
                Región Crítica: <strong className="text-gray-300">{report.most_active_region}</strong>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-[#181c24] border border-[#262a33] text-xs text-gray-300 leading-relaxed">
              {report.executive_summary}
            </div>

            {/* Verified Metrics Card */}
            {report.verified_metrics && (
              <div className="p-4 rounded-xl bg-[#181c24] border border-[#262a33]">
                <div className="text-[11px] font-mono uppercase text-gray-400 mb-2 font-bold flex items-center justify-between">
                  <span>Métricas SQL Verificadas</span>
                  <span className="text-emerald-400 font-normal">Fidelidad 100%</span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs font-mono">
                  <div className="p-2 rounded bg-[#0a0e16] border border-[#262a33]">
                    <div className="text-gray-500 text-[10px]">Total Sismos</div>
                    <div className="text-base font-bold text-white">{report.verified_metrics.total_events}</div>
                  </div>
                  <div className="p-2 rounded bg-[#0a0e16] border border-[#262a33]">
                    <div className="text-gray-500 text-[10px]">Magnitud Pico</div>
                    <div className="text-base font-bold text-amber-400">M {report.verified_metrics.max_magnitude}</div>
                  </div>
                  <div className="p-2 rounded bg-[#0a0e16] border border-[#262a33]">
                    <div className="text-gray-500 text-[10px]">Profundidad Prom.</div>
                    <div className="text-base font-bold text-indigo-300">
                      {report.verified_metrics.avg_depth_km ?? report.verified_metrics.avg_depth ?? '0.0'} km
                    </div>
                  </div>
                  <div className="p-2 rounded bg-[#0a0e16] border border-[#262a33]">
                    <div className="text-gray-500 text-[10px]">Alertas Tsunami</div>
                    <div className="text-base font-bold text-red-400">
                      {report.verified_metrics.tsunami_alerts ?? report.verified_metrics.tsunami_alerts_count ?? 0}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Export Toolbar */}
            <div className="pt-2 border-t border-[#262a33] flex items-center justify-between gap-3">
              <a
                href={api.getExportUrl('csv', reportWindow)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-2 px-3 rounded-xl bg-[#181c24] hover:bg-[#1f2430] border border-[#262a33] text-indigo-300 hover:text-white text-xs font-mono font-medium flex items-center justify-center gap-1.5 transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Exportar CSV</span>
              </a>

              <a
                href={api.getExportUrl('html', reportWindow)}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 py-2 px-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-mono font-medium flex items-center justify-center gap-1.5 transition-colors shadow-md"
              >
                <FileText className="w-3.5 h-3.5" />
                <span>Imprimir / PDF</span>
              </a>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex items-center justify-center text-xs font-mono text-gray-500">
            Cargando informe ejecutivo...
          </div>
        )}
      </div>
    </div>
  );
}
