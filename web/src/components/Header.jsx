import React from 'react';
import { Activity, Shield, Database, Cpu, Radio, User, LogIn, LogOut, RefreshCw } from 'lucide-react';
import { formatBogotaTimeOnly } from '../utils/date';

export default function Header({
  activeTab,
  setActiveTab,
  currentUser,
  onOpenLogin,
  onLogout,
  onOpenBackfill,
  isLive,
  lastEventTime
}) {
  const isAdmin = currentUser?.role === 'admin';

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-[#0a0e16]/95 backdrop-blur-md border-b border-[#262a33] h-16 px-6 flex items-center justify-between">
      {/* Brand & Live Stream Indicator */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 cursor-pointer" onClick={() => setActiveTab('control')}>
          <div className="w-9 h-9 rounded-lg bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shadow-[0_0_15px_rgba(99,102,241,0.25)]">
            <Activity className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg text-white tracking-tight">SismoWatch</span>
              <span className="text-[10px] bg-[#1c2028] text-indigo-300 px-1.5 py-0.5 rounded border border-[#424754]/40 font-mono">v2.4</span>
            </div>
            <div className="text-[9px] font-mono tracking-wider text-gray-400 uppercase font-semibold">
              OPERATIONAL SEISMIC INTELLIGENCE
            </div>
          </div>
        </div>

        {/* Live SSE Pulse */}
        <div className="hidden xl:flex items-center gap-3 pl-6 border-l border-[#262a33] text-xs font-mono">
          <div className={`flex items-center gap-2 px-2.5 py-1 rounded border ${isLive ? 'bg-emerald-950/40 border-emerald-500/30' : 'bg-amber-950/40 border-amber-500/30'}`}>
            <span className="relative flex h-2 w-2">
              {isLive && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>}
              <span className={`relative inline-flex rounded-full h-2 w-2 ${isLive ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
            </span>
            <span className={`font-medium ${isLive ? 'text-emerald-400' : 'text-amber-400'}`}>
              {isLive ? 'SSE STREAM ACTIVO' : 'RECONECTANDO SSE'}
            </span>
          </div>
          {lastEventTime && (
            <span className="text-gray-400 text-[11px]">
              Ultimo sismo: {formatBogotaTimeOnly(lastEventTime)}
            </span>
          )}
        </div>
      </div>

      {/* Center Navigation Tabs (Strict RBAC-filtered) */}
      <nav className="hidden lg:flex items-center gap-1 bg-[#141822] p-1 rounded-xl border border-[#262a33] text-xs font-medium">
        <button
          onClick={() => setActiveTab('control')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition-all ${
            activeTab === 'control'
              ? 'bg-indigo-600/30 text-indigo-300 font-semibold border border-indigo-500/40 shadow-inner'
              : 'text-gray-400 hover:text-white hover:bg-[#1f2430]'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span>Centro de Control</span>
        </button>

        {isAdmin && (
          <button
            onClick={() => setActiveTab('lineage')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition-all ${
              activeTab === 'lineage'
                ? 'bg-indigo-600/30 text-indigo-300 font-semibold border border-indigo-500/40 shadow-inner'
                : 'text-gray-400 hover:text-white hover:bg-[#1f2430]'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Linaje de Datos</span>
          </button>
        )}

        <button
          onClick={() => setActiveTab('agent')}
          className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition-all ${
            activeTab === 'agent'
              ? 'bg-indigo-600/30 text-indigo-300 font-semibold border border-indigo-500/40 shadow-inner'
              : 'text-gray-400 hover:text-white hover:bg-[#1f2430]'
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          <span>Agente IA & Analitica</span>
        </button>

        {isAdmin && (
          <button
            onClick={() => setActiveTab('governance')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg transition-all ${
              activeTab === 'governance'
                ? 'bg-indigo-600/30 text-indigo-300 font-semibold border border-indigo-500/40 shadow-inner'
                : 'text-gray-400 hover:text-white hover:bg-[#1f2430]'
            }`}
          >
            <Shield className="w-3.5 h-3.5" />
            <span>Gobernanza & Calidad</span>
          </button>
        )}
      </nav>

      {/* Right Tools & User Profile */}
      <div className="flex items-center gap-3">
        {/* OpenMetadata external quick link (Admin only) */}
        {isAdmin && (
          <a
            href="http://localhost:8585"
            target="_blank"
            rel="noopener noreferrer"
            title="Abrir Visor de Linaje OpenMetadata"
            className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded bg-[#141822] hover:bg-[#1f2430] border border-[#262a33] text-xs font-mono text-indigo-300 transition-colors"
          >
            <span className="w-2 h-2 rounded-full bg-indigo-400"></span>
            <span>OpenMetadata :8585</span>
          </a>
        )}

        {/* Backfill button (Admin only) */}
        {isAdmin && (
          <button
            onClick={onOpenBackfill}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-xs font-mono text-amber-300 transition-colors"
            title="Ejecutar backfill historico de sismos"
          >
            <RefreshCw className="w-3 h-3" />
            <span>Backfill</span>
          </button>
        )}

        {/* User Auth Pill */}
        {currentUser ? (
          <div className="flex items-center gap-2 pl-3 border-l border-[#262a33]">
            <div className="flex flex-col text-right">
              <span className="text-xs font-medium text-white">{currentUser.username}</span>
              <span className={`text-[9px] font-mono uppercase font-bold tracking-wider ${isAdmin ? 'text-amber-400' : 'text-blue-400'}`}>
                {isAdmin ? 'ADMINISTRADOR (FULL RBAC)' : 'OPERADOR TACTICO (READ ONLY)'}
              </span>
            </div>
            <button
              onClick={onLogout}
              title="Cerrar Sesion"
              className="p-1.5 rounded-lg bg-[#141822] hover:bg-red-500/20 text-gray-400 hover:text-red-400 border border-[#262a33] transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={onOpenLogin}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium shadow-md transition-colors"
          >
            <LogIn className="w-3.5 h-3.5" />
            <span>Ingresar</span>
          </button>
        )}
      </div>
    </header>
  );
}
