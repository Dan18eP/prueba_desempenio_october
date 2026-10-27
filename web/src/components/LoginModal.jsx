import React, { useState } from 'react';
import { Shield, User, Lock, X, Check, AlertCircle } from 'lucide-react';
import { api } from '../api';

export default function LoginModal({ isOpen, onClose, onLoginSuccess }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('SismoAdmin2026!Secret');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const data = await api.login(username, password);
      onLoginSuccess(data.user);
      onClose();
    } catch (err) {
      setError(err.message || 'Error de autenticación');
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
      onClose();
    } catch (err) {
      setError(err.message || 'Error de autenticación');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-md rounded-2xl bg-[#141822] border border-[#262a33] p-6 shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-[#1f2430] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3 mb-6">
          <div className="p-2.5 rounded-xl bg-indigo-600/20 border border-indigo-500/40 text-indigo-400">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Autenticación SismoWatch</h2>
            <p className="text-xs text-gray-400">Control de Acceso Basado en Roles (RBAC)</p>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-950/60 border border-red-500/50 flex items-center gap-2 text-xs text-red-200">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-mono uppercase text-gray-400 mb-1.5">Usuario</label>
            <div className="relative">
              <User className="w-4 h-4 absolute left-3 top-3 text-gray-500" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#0a0e16] border border-[#262a33] text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
                placeholder="admin o viewer"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-mono uppercase text-gray-400 mb-1.5">Contraseña</label>
            <div className="relative">
              <Lock className="w-4 h-4 absolute left-3 top-3 text-gray-500" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full pl-9 pr-3 py-2 rounded-xl bg-[#0a0e16] border border-[#262a33] text-sm text-white focus:outline-none focus:border-indigo-500 font-mono"
                placeholder="••••••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors shadow-lg disabled:opacity-50"
          >
            {loading ? 'Validando Credenciales...' : 'Iniciar Sesión'}
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-[#262a33]">
          <div className="text-[11px] font-mono uppercase text-gray-400 mb-3 text-center">
            Perfiles de Evaluación Rápida (1-Click)
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => handleQuickLogin('admin', 'SismoAdmin2026!Secret')}
              disabled={loading}
              className="p-2.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 border border-amber-500/30 text-left transition-all"
            >
              <div className="text-xs font-bold text-amber-300 font-mono flex items-center justify-between">
                <span>ADMIN</span>
                <span className="text-[10px] bg-amber-500/20 px-1 rounded">RBAC Full</span>
              </div>
              <div className="text-[10px] text-gray-400 mt-0.5">Cuarentena y Backfills</div>
            </button>

            <button
              onClick={() => handleQuickLogin('viewer', 'ViewerSismo2026!')}
              disabled={loading}
              className="p-2.5 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 text-left transition-all"
            >
              <div className="text-xs font-bold text-indigo-300 font-mono flex items-center justify-between">
                <span>VIEWER</span>
                <span className="text-[10px] bg-indigo-500/20 px-1 rounded">Read Only</span>
              </div>
              <div className="text-[10px] text-gray-400 mt-0.5">Consulta y Analítica</div>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
