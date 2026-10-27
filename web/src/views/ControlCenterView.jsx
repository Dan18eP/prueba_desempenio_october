import React, { useEffect, useRef, useState, useMemo } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';
import {
  Compass,
  Radio,
  Filter,
  Play,
  Pause,
  Layers,
  Activity,
  AlertTriangle,
  Waves
} from 'lucide-react';
import { formatBogotaDate, formatBogotaTimeOnly } from '../utils/date';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

export default function ControlCenterView({
  events = [],
  timeseries,
  severityData,
  isPaused,
  setIsPaused,
  onSelectEvent,
  selectedEvent,
  timeWindow = '24h',
  onTimeWindowChange,
  eventsLoading = false
}) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  const [minMagFilter, setMinMagFilter] = useState(0.0);
  const [tsunamiOnlyFilter, setTsunamiOnlyFilter] = useState(false);
  const [activeChartTab, setActiveChartTab] = useState('overview'); // 'overview' | 'depth_regions'
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');

  // Initialize Leaflet Map with Canvas renderer for high throughput
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    // Tactical dark map tiles (CARTO Basemaps Dark Matter)
    const map = L.map(mapContainerRef.current, {
      center: [15.0, -90.0],
      zoom: 3,
      minZoom: 2,
      maxZoom: 12,
      attributionControl: false,
      preferCanvas: true // Hardware-accelerated canvas rendering for 10k points
    });

    const cartoKey = import.meta.env.VITE_CARTO_API_KEY || '';
    const tileUrl = cartoKey
      ? `https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png?key=${cartoKey}`
      : 'https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png';

    L.tileLayer(tileUrl, {
      maxZoom: 19,
      subdomains: 'abcd',
      attribution: 'CARTO Basemaps, USGS Real-Time'
    }).addTo(map);

    markersLayerRef.current = L.layerGroup().addTo(map);
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Filtered events based on magnitude and tsunami toggle
  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      const matchMag = e.magnitude >= minMagFilter;
      const matchTsunami = !tsunamiOnlyFilter || e.tsunami_alert;
      return matchMag && matchTsunami;
    });
  }, [events, minMagFilter, tsunamiOnlyFilter]);

  // Update Map Markers
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;
    markersLayerRef.current.clearLayers();

    filteredEvents.forEach((e) => {
      if (!e.latitude || !e.longitude) return;

      const isTsunami = e.tsunami_alert;
      const isAnomaly = e.is_anomaly;

      // Color coding by magnitude and critical risk
      let color = '#10b981'; // green < 3.5
      if (e.magnitude >= 6.8 || isTsunami) color = '#ef4444'; // critical red
      else if (e.magnitude >= 5.0) color = '#f59e0b'; // orange
      else if (e.magnitude >= 3.5) color = '#eab308'; // yellow

      const radius = Math.max(4, Math.min(22, (e.magnitude || 2) * 2.8));

      const marker = L.circleMarker([e.latitude, e.longitude], {
        radius: radius,
        fillColor: color,
        color: isTsunami ? '#ffffff' : color,
        weight: isTsunami ? 2.5 : 1,
        opacity: 0.9,
        fillOpacity: isTsunami ? 0.9 : 0.6
      });

      const popupHtml = `
        <div style="font-family: monospace; font-size: 11px; color: #0f172a; padding: 4px; min-width: 200px;">
          <div style="font-weight: bold; font-size: 13px; margin-bottom: 2px;">
            M ${e.magnitude.toFixed(1)} — ${e.severity_label}
          </div>
          <div style="color: #334155; margin-bottom: 4px;">${e.place}</div>
          <div style="border-top: 1px solid #cbd5e1; padding-top: 4px; line-height: 1.4;">
            Profundidad: <strong>${e.depth_km} km</strong><br/>
            Hora Bogota: <strong>${formatBogotaTimeOnly(e.event_time_utc)}</strong><br/>
            Fecha: <strong>${formatBogotaDate(e.event_time_utc, false)}</strong><br/>
            ${isTsunami ? '<div style="color: #dc2626; font-weight: bold; margin-top: 2px;">[ALERTA TSUNAMI ACTIVA]</div>' : ''}
            ${isAnomaly ? '<div style="color: #7c3aed; font-weight: bold; margin-top: 2px;">[ANOMALIA ESTADISTICA]</div>' : ''}
          </div>
        </div>
      `;

      marker.bindPopup(popupHtml);
      markersLayerRef.current.addLayer(marker);
    });
  }, [filteredEvents]);

  // Center map on selected event
  useEffect(() => {
    if (selectedEvent && mapInstanceRef.current && selectedEvent.latitude && selectedEvent.longitude) {
      mapInstanceRef.current.setView([selectedEvent.latitude, selectedEvent.longitude], 6, {
        animate: true,
        duration: 1
      });
    }
  }, [selectedEvent]);

  // Operational Analytics Derived Directly from Events (100% Real Data)
  const depthDistribution = useMemo(() => {
    let superficial = 0; // < 70 km
    let intermedio = 0;  // 70 - 300 km
    let profundo = 0;    // > 300 km

    events.forEach((e) => {
      const d = Number(e.depth_km) || 0;
      if (d < 70) superficial++;
      else if (d <= 300) intermedio++;
      else profundo++;
    });

    return {
      labels: ['Superficial (< 70km)', 'Intermedio (70-300km)', 'Profundo (> 300km)'],
      data: [superficial, intermedio, profundo]
    };
  }, [events]);

  const topRegions = useMemo(() => {
    const regionCounts = {};
    events.forEach((e) => {
      if (!e.place) return;
      const parts = e.place.split(',');
      const region = (parts[parts.length - 1] || 'Global').trim();
      regionCounts[region] = (regionCounts[region] || 0) + 1;
    });

    const sorted = Object.entries(regionCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);

    return {
      labels: sorted.map((s) => s[0]),
      data: sorted.map((s) => s[1])
    };
  }, [events]);

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
        data: severityData?.data || [0, 0, 0, 0],
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

  // Chart 3: Depth Distribution
  const depthChartData = {
    labels: depthDistribution.labels,
    datasets: [
      {
        data: depthDistribution.data,
        backgroundColor: [
          'rgba(239, 68, 68, 0.75)',
          'rgba(245, 158, 11, 0.75)',
          'rgba(59, 130, 246, 0.75)'
        ],
        borderWidth: 1,
        borderColor: '#12161f'
      }
    ]
  };

  // Chart 4: Top Regions Bar Chart
  const topRegionsChartData = {
    labels: topRegions.labels,
    datasets: [
      {
        label: 'Sismos',
        data: topRegions.data,
        backgroundColor: 'rgba(16, 185, 129, 0.6)',
        borderColor: '#10b981',
        borderWidth: 1,
        borderRadius: 4
      }
    ]
  };

  const chartCommonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right',
        labels: {
          color: '#cbd5e1',
          font: { family: 'monospace', size: 10 },
          boxWidth: 10
        }
      }
    }
  };

  const tsunamiEventsCount = events.filter((e) => e.tsunami_alert).length;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Left 7 Columns: Tactical Map & Analytical Breakdown */}
      <div className="lg:col-span-7 flex flex-col gap-6">
        {/* Leaflet Geospatial View */}
        <div className="rounded-2xl bg-[#12161f] border border-[#262a33] p-4 flex flex-col shadow-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Compass className="w-4 h-4 text-indigo-400" />
              <span className="text-sm font-bold text-white tracking-wide">
                Mapa Tactico Geoespacial (USGS Live)
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

        {/* Dynamic Analytics Panel with Tab Switcher */}
        <div className="rounded-2xl bg-[#12161f] border border-[#262a33] p-4 flex flex-col shadow-lg">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-[#262a33]">
            <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-wider text-white">
              <Activity className="w-4 h-4 text-indigo-400" />
              <span>Analitica Operacional de Sismicidad Global</span>
            </div>
            <div className="flex items-center gap-1 bg-[#0a0e16] p-1 rounded-lg border border-[#262a33] text-xs font-mono">
              <button
                onClick={() => setActiveChartTab('overview')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  activeChartTab === 'overview'
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Frecuencia & Severidad
              </button>
              <button
                onClick={() => setActiveChartTab('depth_regions')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  activeChartTab === 'depth_regions'
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                Profundidad & Regiones Top
              </button>
            </div>
          </div>

          {activeChartTab === 'overview' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 rounded-xl bg-[#0e121a] border border-[#262a33]">
                <div className="text-[11px] font-mono uppercase text-gray-400 mb-2">
                  Actividad Sismica Horaria (24h)
                </div>
                <div className="h-40">
                  <Bar data={timeseriesChartData} options={timeseriesOptions} />
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[#0e121a] border border-[#262a33]">
                <div className="text-[11px] font-mono uppercase text-gray-400 mb-2">
                  Distribucion por Severidad (ISO)
                </div>
                <div className="h-40 flex items-center justify-center">
                  <Doughnut data={severityChartData} options={chartCommonOptions} />
                </div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 rounded-xl bg-[#0e121a] border border-[#262a33]">
                <div className="text-[11px] font-mono uppercase text-gray-400 mb-2">
                  Distribucion por Profundidad Sismica
                </div>
                <div className="h-40 flex items-center justify-center">
                  <Doughnut data={depthChartData} options={chartCommonOptions} />
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[#0e121a] border border-[#262a33]">
                <div className="text-[11px] font-mono uppercase text-gray-400 mb-2">
                  Top 5 Zonas Sismicas con Mayor Actividad
                </div>
                <div className="h-40">
                  <Bar data={topRegionsChartData} options={timeseriesOptions} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right 5 Columns: Real-Time SSE Stream Feed */}
      <div className="lg:col-span-5 flex flex-col rounded-2xl bg-[#12161f] border border-[#262a33] p-5 shadow-lg h-[640px]">
        {/* Stream Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[#262a33]">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
            <span className="text-sm font-bold text-white tracking-wide">
              Telemetria en Tiempo Real
            </span>
            <span className="text-xs font-mono text-gray-400">
              ({filteredEvents.length} eventos)
            </span>
            {eventsLoading && (
              <span className="text-[10px] font-mono text-indigo-400 animate-pulse">
                Cargando...
              </span>
            )}
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

        {/* Time Window Buttons */}
        <div className="py-2 flex items-center justify-between gap-1 border-b border-[#262a33] text-xs font-mono">
          <span className="text-gray-400 text-[11px] shrink-0">Ventana:</span>
          <div className="flex items-center gap-1">
            {[
              { id: '24h', label: '24 Horas' },
              { id: '7d', label: '7 Días' },
              { id: '30d', label: '30 Días / Todos' }
            ].map((win) => (
              <button
                key={win.id}
                onClick={() => onTimeWindowChange && onTimeWindowChange(win.id)}
                disabled={eventsLoading}
                className={`px-2 py-0.5 rounded text-[11px] transition-colors ${
                  timeWindow === win.id
                    ? 'bg-indigo-600 text-white font-bold'
                    : 'bg-[#181c24] text-gray-400 hover:text-white border border-[#262a33]'
                }`}
              >
                {win.label}
              </button>
            ))}
          </div>
        </div>

        {/* Date Range Custom Filter */}
        <div className="py-1.5 flex items-center gap-1.5 border-b border-[#262a33] text-[10px] font-mono">
          <span className="text-gray-400 shrink-0">Filtro Fecha:</span>
          <input
            type="date"
            value={customStartDate}
            onChange={(e) => setCustomStartDate(e.target.value)}
            className="px-1.5 py-0.5 rounded bg-[#0a0e16] border border-[#262a33] text-gray-200 text-[10px]"
          />
          <span className="text-gray-500">-</span>
          <input
            type="date"
            value={customEndDate}
            onChange={(e) => setCustomEndDate(e.target.value)}
            className="px-1.5 py-0.5 rounded bg-[#0a0e16] border border-[#262a33] text-gray-200 text-[10px]"
          />
          <button
            onClick={() => onTimeWindowChange && onTimeWindowChange('custom', { startDate: customStartDate, endDate: customEndDate })}
            disabled={!customStartDate || !customEndDate || eventsLoading}
            className="px-2 py-0.5 rounded bg-[#181c24] hover:bg-indigo-600 text-gray-300 hover:text-white border border-[#262a33] text-[10px] transition-colors disabled:opacity-40"
          >
            Aplicar
          </button>
        </div>

        {/* Filter Toolbar */}
        <div className="py-2 flex flex-wrap items-center justify-between gap-2 text-xs font-mono border-b border-[#262a33]">
          {/* Tsunami Dedicated Filter */}
          <button
            onClick={() => setTsunamiOnlyFilter(!tsunamiOnlyFilter)}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-xs font-mono font-bold transition-colors ${
              tsunamiOnlyFilter
                ? 'bg-red-600 text-white shadow-md'
                : 'bg-red-950/30 text-red-300 border border-red-500/30 hover:bg-red-900/40'
            }`}
          >
            <Waves className="w-3 h-3" />
            <span>Alertas Tsunami ({tsunamiEventsCount})</span>
          </button>

          {/* Magnitude Threshold Filter */}
          <div className="flex items-center gap-1">
            <span className="text-gray-500 text-[11px] mr-1">Mag &ge;</span>
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
                {val.toFixed(1)}
              </button>
            ))}
          </div>
        </div>

        {/* Events Feed Scrollable List */}
        <div className="flex-1 overflow-y-auto space-y-2.5 pt-3 pr-1">
          {filteredEvents.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-gray-500 text-xs font-mono">
              <span>No hay eventos que cumplan con los filtros seleccionados</span>
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
                        M {Number(e.magnitude).toFixed(1)}
                      </span>
                      <span className="text-xs font-medium text-white truncate max-w-[210px]">
                        {e.place}
                      </span>
                    </div>

                    <div className="text-[10px] font-mono text-gray-400 shrink-0 text-right">
                      <div>{formatBogotaDate(e.event_time_utc, false)}</div>
                      <div className="text-gray-300 font-semibold">{formatBogotaTimeOnly(e.event_time_utc)}</div>
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
                          ALERTA TSUNAMI
                        </span>
                      )}
                      {isAnomaly && (
                        <span className="px-1.5 py-0.5 rounded bg-purple-900/60 text-purple-300 border border-purple-500/30 text-[9px] font-bold">
                          ANOMALIA
                        </span>
                      )}
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
