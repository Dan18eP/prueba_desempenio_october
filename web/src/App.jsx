import React, { useState } from 'react';

export default function App() {
  const [activeTab, setActiveTab] = useState('control');
  const [userRole, setUserRole] = useState('admin'); // 'admin' | 'viewer'

  return (
    <div className="min-h-screen flex flex-col bg-surface-lowest text-on-surface">
      {/* Tactical Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[#0a0e16]/90 backdrop-blur-md border-b border-[#262a33] h-16 px-6 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-indigo-400 text-3xl">radar</span>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-lg text-white tracking-tight">SismoWatch</span>
                <span className="text-[10px] bg-[#1c2028] text-indigo-300 px-1.5 py-0.5 rounded border border-[#424754]/40 font-mono">v2.4-prod</span>
              </div>
              <div className="text-[9px] font-mono tracking-wider text-outline uppercase font-semibold">OPERATIONAL SEISMIC INTELLIGENCE</div>
            </div>
          </div>

          <div className="hidden xl:flex items-center gap-3 pl-6 border-l border-[#262a33] text-xs font-mono">
            <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#181c24] border border-emerald-500/30">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-emerald-400 font-medium">SSE STREAM EN VIVO</span>
            </div>
            <span className="text-outline">/api/stream</span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden lg:flex items-center gap-1 bg-[#181c24] p-1 rounded-xl border border-[#262a33] text-sm">
          <button
            onClick={() => setActiveTab('control')}
            className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'control' ? 'bg-[#262a33] text-indigo-300 font-semibold shadow-inner' : 'text-on-surface-variant hover:text-white'}`}
          >
            Centro de Control
          </button>
          <button
            onClick={() => setActiveTab('lineage')}
            className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'lineage' ? 'bg-[#262a33] text-indigo-300 font-semibold shadow-inner' : 'text-on-surface-variant hover:text-white'}`}
          >
            Linaje de Datos
          </button>
          <button
            onClick={() => setActiveTab('agent')}
            className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'agent' ? 'bg-[#262a33] text-indigo-300 font-semibold shadow-inner' : 'text-on-surface-variant hover:text-white'}`}
          >
            Agente IA & Analítica
          </button>
          <button
            onClick={() => setActiveTab('governance')}
            className={`px-3 py-1.5 rounded-lg transition-all ${activeTab === 'governance' ? 'bg-[#262a33] text-indigo-300 font-semibold shadow-inner' : 'text-on-surface-variant hover:text-white'}`}
          >
            Gobernanza & Auditoría
          </button>
        </nav>

        {/* Right Tools & User Profile */}
        <div className="flex items-center gap-4">
          <div className="hidden 2xl:flex items-center gap-2 px-3 py-1 rounded bg-[#181c24] border border-[#262a33] text-xs font-mono text-outline">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>MinIO: OK</span>
            <span className="text-gray-600">|</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>AF: Ready</span>
            <span className="text-gray-600">|</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span>OM :8585</span>
          </div>

          <div className="flex items-center gap-2 pl-4 border-l border-[#262a33]">
            <span className="material-symbols-outlined text-gray-400">account_circle</span>
            <div className="flex flex-col text-left">
              <span className="text-xs font-medium text-white">Daniel Echeverria</span>
              <span className="text-[10px] font-mono text-emerald-400 font-bold uppercase">{userRole} RBAC</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main View Area */}
      <main className="flex-1 pt-20 px-6 pb-12 max-w-[1920px] w-full mx-auto">
        {/* KPI Banner */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <div className="p-4 rounded-xl bg-surface-low border border-[#262a33] flex flex-col justify-between">
            <div className="text-xs font-mono uppercase text-outline">Eventos (24h)</div>
            <div className="text-2xl font-bold font-mono text-white my-1">142 <span className="text-xs font-sans text-gray-400">sismos</span></div>
            <div className="text-xs font-mono text-emerald-400">+12.4% vs anterior</div>
          </div>

          <div className="p-4 rounded-xl bg-surface-low border border-[#262a33] flex flex-col justify-between">
            <div className="text-xs font-mono uppercase text-outline">Magnitud Máxima</div>
            <div className="text-2xl font-bold font-mono text-red-400 my-1">M 7.2 <span className="text-xs font-sans text-gray-400">Oaxaca</span></div>
            <div className="text-xs font-mono text-outline">Prof: 18.4 km</div>
          </div>

          <div className="p-4 rounded-xl bg-surface-low border border-[#262a33] flex flex-col justify-between">
            <div className="text-xs font-mono uppercase text-outline">Tasa Fidelidad</div>
            <div className="text-2xl font-bold font-mono text-emerald-400 my-1">100.0%</div>
            <div className="text-xs font-mono text-gray-400">20 de 20 eventos reflejados</div>
          </div>

          <div className="p-4 rounded-xl bg-surface-low border border-[#262a33] flex flex-col justify-between">
            <div className="text-xs font-mono uppercase text-outline">Calidad Datos Q</div>
            <div className="text-2xl font-bold font-mono text-indigo-400 my-1">99.4%</div>
            <div className="text-xs font-mono text-gray-400">7 reglas Pandera OK</div>
          </div>

          <div className="p-4 rounded-xl bg-surface-low border border-[#262a33] flex flex-col justify-between">
            <div className="text-xs font-mono uppercase text-outline">Anomalías (Z-Score)</div>
            <div className="text-2xl font-bold font-mono text-amber-400 my-1">3 <span className="text-xs font-sans text-gray-400">clusters</span></div>
            <div className="text-xs font-mono text-gray-400">Z &gt; 2.5 en Ventana 24h</div>
          </div>
        </div>

        {/* Content Placeholder for Phase 5 */}
        <div className="p-8 rounded-xl bg-surface-low border border-[#262a33] text-center">
          <span className="material-symbols-outlined text-4xl text-indigo-400 mb-2">dashboard</span>
          <h2 className="text-xl font-bold text-white mb-2">SismoWatch React Platform Ready</h2>
          <p className="text-sm text-gray-400 max-w-xl mx-auto">
            Estructura base de React JS con Vite y Tailwind inicializada. En la Fase 5 se enlazarán los componentes reactivos de Chart.js, el mapa ligero Leaflet, el chatbot con Qwen 2.5 y el stream SSE en tiempo real.
          </p>
        </div>
      </main>

      {/* Ground Truth Footer */}
      <footer className="bg-surface-low border-t border-[#262a33] py-2 px-6 text-xs font-mono text-outline flex flex-col md:flex-row items-center justify-between gap-2">
        <div>
          <span>TELEMETRY GROUND TRUTH: </span>
          <span className="text-emerald-400 font-semibold">20 Ingeridos / 20 Publicados (Fidelidad 100%)</span>
          <span className="mx-2 text-gray-600">|</span>
          <span className="text-indigo-400">Cero Pérdida Destructiva</span>
          <span className="mx-2 text-gray-600">|</span>
          <span>OpenLineage Activo</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>Lakehouse Node Latam-1</span>
        </div>
      </footer>
    </div>
  );
}
