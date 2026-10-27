import React from 'react';
import { Waves } from 'lucide-react';

export default function TsunamiBanner({ alertsCount, latestTsunamiEvent }) {
  if (!alertsCount || alertsCount === 0) {
    return (
      <div className="mb-4 rounded-xl bg-[#12161f] border border-[#262a33] px-4 py-2.5 text-xs font-mono flex items-center justify-between text-gray-400">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-gray-300 font-semibold">MONITOREO DE TSUNAMIS ACTIVO:</span>
          <span>0 Alertas Criticas en curso (Matriz NOAA M &ge; 6.8 y Prof &le; 100km en Calma)</span>
        </div>
        <span className="text-[10px] text-gray-500 hidden md:inline">Protocolo NOAA / PTWC Normal</span>
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-xl bg-gradient-to-r from-red-950/80 via-red-900/60 to-red-950/80 border-2 border-red-500/80 p-4 shadow-[0_0_25px_rgba(239,68,68,0.3)] animate-pulse">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-lg bg-red-600 text-white shadow-lg">
            <Waves className="w-6 h-6 animate-bounce" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-red-600 text-white font-mono text-xs font-black tracking-wider uppercase">
                ALERTA DE TSUNAMI ACTIVA
              </span>
              <span className="text-xs font-mono text-red-200">
                ({alertsCount} {alertsCount === 1 ? 'evento critico detectado' : 'eventos criticos detectados'})
              </span>
            </div>
            <p className="text-sm text-red-100 font-medium mt-1">
              {latestTsunamiEvent ? (
                <>
                  Sismo M <strong className="text-white text-base">{latestTsunamiEvent.magnitude}</strong> en{' '}
                  <strong className="text-white">{latestTsunamiEvent.place}</strong> — Profundidad:{' '}
                  {latestTsunamiEvent.depth_km} km. Matriz de Riesgo Activada.
                </>
              ) : (
                'Protocolo de emergencia NOAA/PTWC en curso para zonas costeras en el radio de impacto.'
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 self-end md:self-center">
          <div className="text-right font-mono text-xs text-red-300">
            <div>CONDICION MATRIZ:</div>
            <div className="font-bold text-white">M &ge; 6.8 &bull; Prof &le; 100km</div>
          </div>
        </div>
      </div>
    </div>
  );
}
