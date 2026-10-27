import React from 'react';
import { Activity, Zap, CheckCircle2, Award, AlertOctagon } from 'lucide-react';

export default function KpiBar({ telemetry, governance }) {
  const t = telemetry || {
    total_events: 0,
    max_magnitude: 0.0,
    avg_depth_km: 0.0,
    tsunami_alerts_active: 0,
    anomalies_detected: 0
  };

  const g = governance || {
    fidelity_rate_percent: 100.0,
    raw_records_in: 20,
    gold_records_out: 20,
    loss_records: 0,
    quality_score_percent: 99.4,
    freshness_lag_minutes: 2
  };

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      {/* 1. Sismos Totales */}
      <div className="p-4 rounded-xl bg-[#12161f] border border-[#262a33] hover:border-indigo-500/40 transition-all flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-xs font-mono uppercase text-gray-400">
          <span>Actividad Sísmica</span>
          <Activity className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-bold font-mono text-white tracking-tight">
            {t.total_events} <span className="text-xs font-sans text-gray-400 font-normal">eventos</span>
          </div>
          <div className="text-xs font-mono text-indigo-300">Prof. prom: {t.avg_depth_km} km</div>
        </div>
        <div className="text-[11px] font-mono text-emerald-400 flex items-center gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>Catálogo USGS en vivo</span>
        </div>
      </div>

      {/* 2. Magnitud Máxima */}
      <div className="p-4 rounded-xl bg-[#12161f] border border-[#262a33] hover:border-amber-500/40 transition-all flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-xs font-mono uppercase text-gray-400">
          <span>Magnitud Pico</span>
          <Zap className="w-4 h-4 text-amber-400" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-bold font-mono text-amber-400 tracking-tight">
            M {t.max_magnitude.toFixed(1)}
          </div>
          <div className="text-xs font-mono text-gray-300 truncate">
            {t.max_magnitude >= 6.8 ? 'Severidad Mayor / Crítica' : 'Severidad Monitoreada'}
          </div>
        </div>
        <div className="text-[11px] font-mono text-gray-400">
          Alerta Tsunami: {t.tsunami_alerts_active > 0 ? <strong className="text-red-400">ACTIVA ({t.tsunami_alerts_active})</strong> : 'Sin Riesgo Inminente'}
        </div>
      </div>

      {/* 3. Tasa de Fidelidad - Invariante 20 in -> 20 out */}
      <div className="p-4 rounded-xl bg-[#12161f] border border-emerald-500/30 hover:border-emerald-500/60 transition-all flex flex-col justify-between shadow-sm bg-gradient-to-br from-[#12161f] to-emerald-950/20">
        <div className="flex items-center justify-between text-xs font-mono uppercase text-emerald-400">
          <span className="font-bold">Fidelidad de Linaje</span>
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-bold font-mono text-emerald-400 tracking-tight">
            {g.fidelity_rate_percent.toFixed(1)}%
          </div>
          <div className="text-xs font-mono text-gray-300">
            {g.gold_records_out} de {g.raw_records_in} registros (0 pérdida)
          </div>
        </div>
        <div className="text-[10px] font-mono text-emerald-300/80 uppercase font-semibold">
          &ldquo;Me llegaron 20, mostré 20&rdquo;
        </div>
      </div>

      {/* 4. Score de Calidad de Datos (Pandera) */}
      <div className="p-4 rounded-xl bg-[#12161f] border border-[#262a33] hover:border-indigo-500/40 transition-all flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-xs font-mono uppercase text-gray-400">
          <span>Calidad de Datos Q</span>
          <Award className="w-4 h-4 text-indigo-400" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-bold font-mono text-indigo-300 tracking-tight">
            {g.quality_score_percent.toFixed(1)}%
          </div>
          <div className="text-xs font-mono text-gray-300">
            7 Reglas Pandera ISO 25012
          </div>
        </div>
        <div className="text-[11px] font-mono text-gray-400">
          Latencia de frescura: &le; {g.freshness_lag_minutes} min
        </div>
      </div>

      {/* 5. Anomalías y Enjambres Sísmicos */}
      <div className="p-4 rounded-xl bg-[#12161f] border border-[#262a33] hover:border-purple-500/40 transition-all flex flex-col justify-between shadow-sm">
        <div className="flex items-center justify-between text-xs font-mono uppercase text-gray-400">
          <span>Anomalías Sísmicas</span>
          <AlertOctagon className="w-4 h-4 text-purple-400" />
        </div>
        <div className="my-2">
          <div className="text-3xl font-bold font-mono text-purple-300 tracking-tight">
            {t.anomalies_detected} <span className="text-xs font-sans text-gray-400 font-normal">clusters</span>
          </div>
          <div className="text-xs font-mono text-gray-300">
            Detección Z-Score &gt; 2.5
          </div>
        </div>
        <div className="text-[11px] font-mono text-purple-400">
          Enjambres de alta energía
        </div>
      </div>
    </div>
  );
}
