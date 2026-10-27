import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import TsunamiBanner from './components/TsunamiBanner';
import KpiBar from './components/KpiBar';
import LoginView from './views/LoginView';
import ControlCenterView from './views/ControlCenterView';
import LineageView from './views/LineageView';
import AiAgentView from './views/AiAgentView';
import GovernanceView from './views/GovernanceView';
import { api } from './api';
import { RefreshCw, X, Check, AlertCircle } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('control');
  const [currentUser, setCurrentUser] = useState(() => api.user);
  const [isBackfillModalOpen, setIsBackfillModalOpen] = useState(false);

  // Operational Data State
  const [events, setEvents] = useState([]);
  const [kpis, setKpis] = useState(null);
  const [timeseries, setTimeseries] = useState(null);
  const [severityData, setSeverityData] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isPaused, setIsPaused] = useState(false);
  const [isLive, setIsLive] = useState(false);
  const [lastEventTime, setLastEventTime] = useState(null);

  // Backfill modal state
  const [backfillStart, setBackfillStart] = useState('2026-10-01');
  const [backfillEnd, setBackfillEnd] = useState('2026-10-27');
  const [backfillMag, setBackfillMag] = useState(4.0);
  const [backfillLoading, setBackfillLoading] = useState(false);
  const [backfillNotice, setBackfillNotice] = useState(null);

  const [timeWindow, setTimeWindow] = useState('24h');
  const [eventsLoading, setEventsLoading] = useState(false);

  // Initial Data Fetch (Default 24h for Zero-Lag rendering)
  useEffect(() => {
    async function fetchInitialData() {
      if (!api.token || !currentUser) return;
      try {
        const [kpiRes, tsRes, sevRes, evRes] = await Promise.all([
          api.getKpis().catch(() => null),
          api.getTimeseries().catch(() => null),
          api.getSeverity().catch(() => null),
          api.getEvents({ hours: 24, limit: 1000 }).catch(() => null)
        ]);

        if (kpiRes) setKpis(kpiRes);
        if (tsRes) setTimeseries(tsRes);
        if (sevRes) setSeverityData(sevRes);
        if (evRes && evRes.events) {
          setEvents(evRes.events);
          if (evRes.events.length > 0) {
            setLastEventTime(evRes.events[0].event_time_utc);
          }
        }
      } catch (err) {
        console.error('Error fetching initial operational data:', err);
      }
    }

    fetchInitialData();
  }, [currentUser]);

  const handleTimeWindowChange = async (window, customFilter = null) => {
    setTimeWindow(window);
    setEventsLoading(true);
    try {
      let params = { limit: 1000 };
      if (window === '24h') {
        params.hours = 24;
      } else if (window === '7d') {
        params.hours = 168;
        params.limit = 3000;
      } else if (window === '30d' || window === 'all') {
        params.hours = 720;
        params.limit = 10000;
      }
      if (customFilter?.startDate) params.start_date = customFilter.startDate;
      if (customFilter?.endDate) params.end_date = customFilter.endDate;

      const evRes = await api.getEvents(params);
      if (evRes && evRes.events) {
        setEvents(evRes.events);
      }
    } catch (err) {
      console.error('Error changing event window:', err);
    } finally {
      setEventsLoading(false);
    }
  };

  // RBAC Tab Protection Guard
  useEffect(() => {
    if (currentUser?.role === 'viewer' && ['lineage', 'governance'].includes(activeTab)) {
      setActiveTab('control');
    }
  }, [currentUser, activeTab]);

  // Real-Time Server-Sent Events (SSE) Stream
  useEffect(() => {
    let eventSource = null;

    try {
      eventSource = api.createEventSource();

      eventSource.addEventListener('connected', () => {
        setIsLive(true);
      });

      eventSource.addEventListener('initial_batch', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (Array.isArray(data) && data.length > 0) {
            setEvents(data);
            setLastEventTime(data[0].event_time_utc);
          }
        } catch (e) {
          console.error('Error parsing initial_batch:', e);
        }
      });

      eventSource.addEventListener('earthquake_update', (event) => {
        if (isPaused) return;
        try {
          const newEvent = JSON.parse(event.data);
          setEvents((prev) => {
            const filtered = prev.filter((e) => e.id !== newEvent.id);
            return [newEvent, ...filtered];
          });
          setLastEventTime(newEvent.event_time_utc);
        } catch (e) {
          console.error('Error parsing earthquake_update:', e);
        }
      });

      eventSource.onerror = () => {
        setIsLive(false);
      };
    } catch (err) {
      console.warn('SSE connection unavailable, using polling fallback:', err);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [isPaused, currentUser]);

  // Check for active tsunami condition strictly scoped to current events in view
  const currentTsunamiEvents = events.filter((e) => e.tsunami_alert);
  const tsunamiCount = currentTsunamiEvents.length;
  const latestTsunami = currentTsunamiEvents.length > 0 ? currentTsunamiEvents[0] : null;

  const handleLogout = () => {
    api.logout();
    setCurrentUser(null);
  };

  const handleBackfillSubmit = async (e) => {
    e.preventDefault();
    setBackfillLoading(true);
    setBackfillNotice(null);
    try {
      const res = await api.triggerBackfill(backfillStart, backfillEnd, parseFloat(backfillMag));
      setBackfillNotice({ type: 'success', text: res.message || 'Backfill encolado correctamente en Airflow.' });
      setTimeout(() => {
        setIsBackfillModalOpen(false);
        setBackfillNotice(null);
      }, 2500);
    } catch (err) {
      setBackfillNotice({ type: 'error', text: err.message });
    } finally {
      setBackfillLoading(false);
    }
  };

  // If no user or token is authenticated, present full-screen Login View
  if (!currentUser || !api.token) {
    return <LoginView onLoginSuccess={(user) => setCurrentUser(user)} />;
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#0a0e16] text-[#e2e8f0]">
      {/* Tactical Dark Mode Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentUser={currentUser}
        onOpenLogin={() => handleLogout()}
        onLogout={handleLogout}
        onOpenBackfill={() => setIsBackfillModalOpen(true)}
        isLive={isLive}
        lastEventTime={lastEventTime}
      />

      {/* Main Tactical Container */}
      <main className="flex-1 pt-20 px-6 pb-12 max-w-[1920px] w-full mx-auto">
        {/* Tsunami Alert Banner (M >= 6.8 & Depth <= 100km) */}
        <TsunamiBanner alertsCount={tsunamiCount} latestTsunamiEvent={latestTsunami} />

        {/* 5 Operational Telemetry KPI Cards */}
        <KpiBar telemetry={kpis?.telemetry_24h} governance={kpis?.governance_and_fidelity} />

        {/* Dynamic Views */}
        {activeTab === 'control' && (
          <ControlCenterView
            events={events}
            timeseries={timeseries}
            severityData={severityData}
            isPaused={isPaused}
            setIsPaused={setIsPaused}
            onSelectEvent={setSelectedEvent}
            selectedEvent={selectedEvent}
            timeWindow={timeWindow}
            onTimeWindowChange={handleTimeWindowChange}
            eventsLoading={eventsLoading}
          />
        )}

        {activeTab === 'lineage' && <LineageView />}

        {activeTab === 'agent' && <AiAgentView currentUser={currentUser} />}

        {activeTab === 'governance' && (
          <GovernanceView currentUser={currentUser} />
        )}
      </main>

      {/* Ground Truth Invariant Footer */}
      <footer className="bg-[#12161f] border-t border-[#262a33] py-2.5 px-6 text-xs font-mono text-gray-400 flex flex-col md:flex-row items-center justify-between gap-2">
        <div>
          <span>TELEMETRÍA GROUND TRUTH: </span>
          <strong className="text-emerald-400 font-bold">Linaje y Trazabilidad Verificada (Fidelidad 100%)</strong>
          <span className="mx-2 text-gray-600">|</span>
          <span className="text-indigo-400">Preservación Total de Datos (Linaje Puro)</span>
          <span className="mx-2 text-gray-600">|</span>
          <span className="text-gray-300">OpenLineage & Pandera ISO 25012</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>SismoWatch SuperApp Platform &bull; Node Latam-1</span>
        </div>
      </footer>

      {/* Admin Backfill Modal */}
      {isBackfillModalOpen && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-2xl bg-[#141822] border border-[#262a33] p-6 shadow-2xl relative">
            <button
              onClick={() => setIsBackfillModalOpen(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-5">
              <div className="p-2.5 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-400">
                <RefreshCw className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Backfill Histórico USGS</h3>
                <p className="text-xs text-gray-400">Disparo administrativo de DAG Airflow</p>
              </div>
            </div>

            {backfillNotice && (
              <div
                className={`mb-4 p-3 rounded-xl border text-xs font-mono flex items-center gap-2 ${
                  backfillNotice.type === 'error'
                    ? 'bg-red-950/40 border-red-500/40 text-red-200'
                    : 'bg-emerald-950/40 border-emerald-500/40 text-emerald-200'
                }`}
              >
                {backfillNotice.type === 'error' ? <AlertCircle className="w-4 h-4" /> : <Check className="w-4 h-4" />}
                <span>{backfillNotice.text}</span>
              </div>
            )}

            <form onSubmit={handleBackfillSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-mono uppercase text-gray-400 mb-1">Fecha Inicio (UTC)</label>
                <input
                  type="date"
                  value={backfillStart}
                  onChange={(e) => setBackfillStart(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-xl bg-[#0a0e16] border border-[#262a33] text-xs font-mono text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-gray-400 mb-1">Fecha Fin (UTC)</label>
                <input
                  type="date"
                  value={backfillEnd}
                  onChange={(e) => setBackfillEnd(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-xl bg-[#0a0e16] border border-[#262a33] text-xs font-mono text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono uppercase text-gray-400 mb-1">Magnitud Mínima</label>
                <input
                  type="number"
                  step="0.1"
                  min="0"
                  max="10"
                  value={backfillMag}
                  onChange={(e) => setBackfillMag(e.target.value)}
                  required
                  className="w-full px-3 py-2 rounded-xl bg-[#0a0e16] border border-[#262a33] text-xs font-mono text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <button
                type="submit"
                disabled={backfillLoading}
                className="w-full py-2.5 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold font-mono transition-colors shadow-lg disabled:opacity-50"
              >
                {backfillLoading ? 'Encolando en Airflow...' : 'Ejecutar Backfill'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
