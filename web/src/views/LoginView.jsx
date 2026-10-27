import React, { useState } from 'react';
import { Shield, User, Lock, Activity, Check, AlertCircle, ArrowRight } from 'lucide-react';
import { api } from '../api';

export default function LoginView({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.login(username, password);
      onLoginSuccess(data.user);
    } catch (err) {
      setError(err.message || 'Credenciales de autenticación no válidas');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = async (user, pass) => {
    setUsername(user);
    setPassword(pass);
    setLoading(true);
    setError(null);
    try {
      const data = await api.login(user, pass);
      onLoginSuccess(data.user);
    } catch (err) {
      setError(err.message || 'Error de autenticación');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#07090e] flex flex-col justify-center items-center p-4 relative overflow-hidden select-none">
      {/* Background Ambient Glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-indigo-950/20 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[350px] h-[350px] bg-blue-950/15 rounded-full blur-[100px] pointer-events-none" />

      {/* Main Card */}
      <div className="w-full max-w-md rounded-3xl bg-[#0f131c]/95 border border-[#1f2637] p-8 shadow-2xl relative z-10 backdrop-blur-xl">
        {/* Brand Header */}
        <div className="flex flex-col items-center text-center mb-8">
          <div className="w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center text-indigo-400 mb-4 shadow-[0_0_25px_rgba(99,102,241,0.35)]">
            <Activity className="w-8 h-8 animate-pulse text-indigo-400" />
          </div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-2xl font-bold tracking-tight text-white font-sans">
              SismoWatch
            </h1>
            <span className="text-[10px] bg-[#1c2233] text-indigo-300 px-2 py-0.5 rounded-full border border-indigo-500/30 font-mono font-bold">
              v2.4
            </span>
          </div>
          <p className="text-xs font-mono uppercase tracking-widest text-gray-400">
            Operational Seismic Intelligence
          </p>
          <div className="mt-2 text-[11px] text-gray-500 max-w-xs">
            Plataforma de monitoreo y gobernanza de datos sísmicos en tiempo real (USGS FDSN & Medallion Lakehouse)
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-3.5 rounded-2xl bg-red-950/70 border border-red-500/60 flex items-start gap-3 text-xs text-red-200 animate-fadeIn">
            <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <div className="flex-1 leading-relaxed">{error}</div>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono uppercase text-gray-400 mb-1.5">
              Identificador de Usuario
            </label>
            <div className="relative">
              <User className="w-4 h-4 absolute left-3.5 top-3.5 text-gray-500" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#090c13] border border-[#232b3e] text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
                placeholder="admin o viewer"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-gray-400 mb-1.5">
              Clave de Seguridad
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 absolute left-3.5 top-3.5 text-gray-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#090c13] border border-[#232b3e] text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all font-mono"
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:scale-[0.99] text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/30 flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading ? (
              <span>Validando Credenciales JWT...</span>
            ) : (
              <>
                <span>Ingresar a la Plataforma</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {/* 1-Click Evaluation Profiles */}
        <div className="mt-8 pt-6 border-t border-[#1f2637]">
          <div className="text-[11px] font-mono uppercase tracking-wider text-gray-400 mb-3 text-center">
            Perfiles de Evaluación Inmediata (1-Click)
          </div>
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => handleQuickLogin('admin', 'SismoAdmin2026!Secret')}
              disabled={loading}
              className="p-3 rounded-2xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-left transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <div className="text-xs font-bold text-amber-300 font-mono flex items-center justify-between">
                <span>ADMIN</span>
                <span className="text-[10px] bg-amber-500/25 px-1.5 py-0.5 rounded font-mono">RBAC Full</span>
              </div>
              <div className="text-[10px] text-gray-400 mt-1 leading-tight">
                Backfills, Reportes IA y Gobernanza
              </div>
            </button>

            <button
              type="button"
              onClick={() => handleQuickLogin('viewer', 'SismoViewer2026!')}
              disabled={loading}
              className="p-3 rounded-2xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-left transition-all hover:scale-[1.02] active:scale-[0.98]"
            >
              <div className="text-xs font-bold text-indigo-300 font-mono flex items-center justify-between">
                <span>VIEWER</span>
                <span className="text-[10px] bg-indigo-500/25 px-1.5 py-0.5 rounded font-mono">Read Only</span>
              </div>
              <div className="text-[10px] text-gray-400 mt-1 leading-tight">
                Monitoreo, Mapa Táctico y Chat IA
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Security Footer Notice */}
      <div className="mt-6 text-center text-[11px] font-mono text-gray-500">
        Control de Acceso Basado en Roles (RBAC) • JWT HS256 • Conforme a OWASP ASVS 4.0
      </div>
    </div>
  );
}
