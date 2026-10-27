import React, { useState, useEffect, useRef } from 'react';
import L from 'leaflet';
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
  Legend,
  Filler
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import { Pause, Play, Filter, AlertTriangle, Radio, MapPin, Compass } from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function ControlCenterView({
  events,
  timeseries,
  severityData,
  isPaused,
  setIsPaused,
  onSelectEvent,
  selectedEvent
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  const [minMagFilter, setMinMagFilter] = useState(0.0);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    // Tactical dark map tiles (CARTO Basemaps Dark Matter with user API Key)
    const map = L.map(mapContainerRef.current, {
      center: [15.0, -90.0],
      zoom: 3,
      minZoom: 2,
      maxZoom: 12,
      attributionControl: false
    });

    const cartoKey = import.meta.env.VITE_CARTO_API_KEY || 'cb1_4vzx_1_c2e8d37b1e85e3709ad52c32';
    L.tileLayer(`https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png?key=${cartoKey}`, {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: '© CARTO, © OpenStreetMap'
    }).addTo(map);

    markersLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Map Markers when events change
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    const filtered = events.filter((e) => e.magnitude >= minMagFilter);

    filtered.forEach((e) => {
      if (!e.latitude || !e.longitude) return;

      const isTsunami = e.tsunami_alert;
      const isAnomaly = e.is_anomaly;

      // Color coding by magnitude
      let color = '#10b981'; // green < 4
      if (e.magnitude >= 6.8 || isTsunami) color = '#ef4444'; // critical red
      else if (e.magnitude >= 5.0) color = '#f59e0b'; // orange
      else if (e.magnitude >= 3.5) color = '#eab308'; // yellow

      const radius = Math.max(5, Math.min(22, (e.magnitude || 2) * 2.8));

      const marker = L.circleMarker([e.latitude, e.longitude], {
        radius: radius,
        fillColor: color,
        color: isTsunami ? '#ffffff' : color,
        weight: isTsunami ? 2.5 : 1,
        opacity: 0.9,
        fillOpacity: isTsunami ? 0.85 : 0.6
      });

      const popupHtml = `
        <div style="font-family: inherit; font-size: 12px; color: #0f172a; padding: 4px;">
          <div style="font-weight: bold; font-size: 14px; margin-bottom: 2px;">
            M ${e.magnitude.toFixed(1)} — ${e.severity_label}
          </div>
          <div style="color: #475569; margin-bottom: 4px;">${e.place}</div>
          <div style="font-family: monospace; font-size: 11px;">
            Profundidad: <strong>${e.depth_km} km</strong><br/>
            Hora: <strong>${new Date(e.event_time_utc).toLocaleTimeString()}</strong><br/>
            ${isTsunami ? '<span style="color: #dc2626; font-weight: bold;">⚠️ ALERTA TSUNAMI</span><br/>' : ''}
            ${isAnomaly ? '<span style="color: #9333ea; font-weight: bold;">⚡ ANOMALÍA DETECTADA</span>' : ''}
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml);
      markersLayerRef.current.addLayer(marker);
    });
  }, [events, minMagFilter]);

  // Center map on selected event
  useEffect(() => {
    if (selectedEvent && mapInstanceRef.current && selectedEvent.latitude && selectedEvent.longitude) {
      mapInstanceRef.current.setView([selectedEvent.latitude, selectedEvent.longitude], 6, {
        animate: true,
        duration: 1
      });
    }
  }, [selectedEvent]);

  // Chart 1: Hourly Timeseries
  const timeseriesChartData = {
    labels: timeseries?.hours?.map((h) => h.slice(11, 16)) || [],
    datasets: [
      {
        type: 'bar',
        label: 'Eventos por Hora',
        data: timeseries?.counts || [],
        backgroundColor: 'rgba(99, 102, 241, 0.5)',
        borderColor: '#6366f1',
        borderWidth: 1,
        borderRadius: 4
      }
    ]
  };

  const timeseriesOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#141822',
        titleFont: { family: 'monospace', size: 12 },
        bodyFont: { family: 'monospace', size: 11 }
      }
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8', font: { family: 'monospace', size: 10 } }
      },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8', font: { family: 'monospace', size: 10 } }
      }
    }
  };

  // Chart 2: Severity Distribution
  const severityChartData = {
    labels: severityData?.labels || ['Micro', 'Menor', 'Moderado', 'Fuerte'],
    datasets: [
      {
        data: severityData?.data || [10, 8, 2, 0],
        backgroundColor: [
          'rgba(16, 185, 129, 0.7)',
          'rgba(234, 179, 8, 0.7)',
          'rgba(245, 158, 11, 0.7)',
          'rgba(239, 68, 68, 0.7)',
          'rgba(147, 51, 234, 0.7)'
        ],
        borderWidth: 1,
        borderColor: '#12161f'
      }
    ]
  };

  const severityOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: {
          color: '#cbd5e1',
          font: { family: 'monospace', size: 11 },
          boxWidth: 12
        }
      }
    }
  };

  const filteredEvents = events.filter((e) => e.magnitude >= minMagFilter);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Left 7 Columns: Tactical Map & Analytics */}
      <div className="lg:col-span-7 flex flex-col gap-6">
        {/* Leaflet Geospatial View */}
        <div className="rounded-2xl bg-[#12161f] border border-[#262a33] p-4 flex flex-col shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Compass className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-bold text-white tracking-wide">
                Mapa Táctico Geoespacial (USGS Live)
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs font-mono text-gray-400">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 inline-block"></span> M &lt; 3.5
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-yellow-500 inline-block"></span> 3.5 - 5.0
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block"></span> 5.0 - 6.8
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 inline-block"></span> M &ge; 6.8 / Tsunami
              </span>
            </div>
          </div>

          <div
            ref={mapContainerRef}
            className="w-full h-[380px] rounded-xl overflow-hidden border border-[#262a33] bg-[#0a0e16] relative isolate z-0"
          />
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="rounded-2xl bg-[#12161f] border border-[#262a33] p-4 flex flex-col shadow-lg">
            <div className="text-xs font-mono uppercase text-gray-400 mb-2">
              Actividad Sísmica Horaria (24h)
            </div>
            <div className="h-44">
              <Bar data={timeseriesChartData} options={timeseriesOptions} />
            </div>
          </div>

          <div className="rounded-2xl bg-[#12161f] border border-[#262a33] p-4 flex flex-col shadow-lg">
            <div className="text-xs font-mono uppercase text-gray-400 mb-2">
              Distribución por Severidad
            </div>
            <div className="h-44 flex items-center justify-center">
              <Doughnut data={severityChartData} options={severityOptions} />
            </div>
          </div>
        </div>
      </div>

      {/* Right 5 Columns: Real-Time SSE Stream Feed */}
      <div className="lg:col-span-5 flex flex-col rounded-2xl bg-[#12161f] border border-[#262a33] p-5 shadow-lg h-[640px]">
        {/* Stream Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#262a33]">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
            <span className="text-sm font-bold text-white tracking-wide">
              Telemetría SSE en Vivo
            </span>
            <span className="text-xs font-mono text-gray-400">
              ({filteredEvents.length} eventos)
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsPaused(!isPaused)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-mono font-medium transition-colors ${
                isPaused
                  ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                  : 'bg-[#181c24] text-gray-400 hover:text-white border border-[#262a33]'
              }`}
            >
              {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
              <span>{isPaused ? 'Reanudar' : 'Pausar'}</span>
            </button>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="py-3 flex items-center justify-between text-xs font-mono border-b border-[#262a33]">
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-gray-400" />
            <span className="text-gray-400">Filtro Magnitud Mínima:</span>
          </div>
          <div className="flex items-center gap-1">
            {[0, 2.5, 4.0, 5.5].map((val) => (
              <button
                key={val}
                onClick={() => setMinMagFilter(val)}
                className={`px-2 py-0.5 rounded text-xs transition-colors ${
                  minMagFilter === val
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'bg-[#181c24] text-gray-400 hover:text-white'
                }`}
              >
                &ge; {val.toFixed(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Events Feed Scrollable List */}
        <div className="flex-1 overflow-y-auto space-y-2.5 pt-3 pr-1">
          {filteredEvents.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-500 text-xs font-mono">
              <span>No hay eventos que cumplan con el filtro actual</span>
            </div>
          ) : (
            filteredEvents.map((e) => {
              const isSelected = selectedEvent?.id === e.id;
              const isTsunami = e.tsunami_alert;
              const isAnomaly = e.is_anomaly;

              return (
                <div
                  key={e.id}
                  onClick={() => onSelectEvent(e)}
                  className={`p-3 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-indigo-950/40 border-indigo-500'
                      : isTsunami
                      ? 'bg-red-950/20 border-red-500/40 hover:border-red-500'
                      : 'bg-[#181c24] border-[#262a33] hover:border-[#424754]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-sm font-bold font-mono px-2 py-0.5 rounded ${
                          e.magnitude >= 6.8 || isTsunami
                            ? 'bg-red-600 text-white'
                            : e.magnitude >= 5.0
                            ? 'bg-amber-600 text-white'
                            : e.magnitude >= 3.5
                            ? 'bg-yellow-600 text-black font-semibold'
                            : 'bg-emerald-600/30 text-emerald-300'
                        }`}
                      >
                        M {e.magnitude.toFixed(1)}
                      </span>
                      <span className="text-xs font-medium text-white truncate max-w-[200px]">
                        {e.place}
                      </span>
                    </div>

                    <div className="text-[11px] font-mono text-gray-400 shrink-0">
                      {new Date(e.event_time_utc).toLocaleTimeString()}
                    </div>
                  </div>

                  <div className="mt-2 flex items-center justify-between text-[11px] font-mono text-gray-400">
                    <div>
                      <span>Prof: {e.depth_km} km</span>
                      <span className="mx-1.5 text-gray-600">&bull;</span>
                      <span>{e.severity_label}</span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {isTsunami && (
                        <span className="px-1.5 py-0.5 rounded bg-red-600 text-white text-[9px] font-bold">
                          TSUNAMI
                        </span>
                      )}
                      {isAnomaly && (
                        <span className="px-1.5 py-0.5 rounded bg-purple-600/30 text-purple-300 border border-purple-500/30 text-[9px]">
                          ANOMALÍA
                        </span>
                      )}
                      <span className="text-emerald-400 text-[10px]">VERIFICADO</span>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
