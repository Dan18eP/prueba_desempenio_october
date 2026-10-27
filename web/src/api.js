// Centralized SismoWatch API Service
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.token = localStorage.getItem('sismowatch_token') || null;
    this.user = JSON.parse(localStorage.getItem('sismowatch_user') || 'null');
  }

  setSession(token, user) {
    this.token = token;
    this.user = user;
    if (token) {
      localStorage.setItem('sismowatch_token', token);
      localStorage.setItem('sismowatch_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('sismowatch_token');
      localStorage.removeItem('sismowatch_user');
    }
  }

  getHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async login(username, password) {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error al iniciar sesión' }));
      throw new Error(err.detail || 'Credenciales incorrectas');
    }
    const data = await res.json();
    this.setSession(data.access_token, data.user);
    return data;
  }

  logout() {
    this.setSession(null, null);
  }

  async getKpis() {
    const res = await fetch(`${API_BASE_URL}/api/kpis`, {
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Error al obtener KPIs');
    return res.json();
  }

  async getTimeseries() {
    const res = await fetch(`${API_BASE_URL}/api/stats/timeseries`, {
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Error al obtener series temporales');
    return res.json();
  }

  async getSeverity() {
    const res = await fetch(`${API_BASE_URL}/api/stats/severity`, {
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Error al obtener severidad');
    return res.json();
  }

  async getEvents(params = {}) {
    const cleanParams = { ...params };
    if (cleanParams.hours === undefined && !cleanParams.start_date) {
      cleanParams.hours = 24;
    }
    const query = new URLSearchParams(cleanParams).toString();
    const res = await fetch(`${API_BASE_URL}/api/events?${query}`, {
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Error al obtener eventos');
    return res.json();
  }

  async getLatestReport(window = '24h') {
    const res = await fetch(`${API_BASE_URL}/api/reports/latest?window=${window}`, {
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Error al obtener reporte ejecutivo');
    return res.json();
  }

  async getReportHistory() {
    const res = await fetch(`${API_BASE_URL}/api/reports/history`, {
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Error al obtener historial de reportes');
    return res.json();
  }

  getExportUrl(format = 'csv', window = '24h') {
    const tokenParam = this.token ? `&token=${encodeURIComponent(this.token)}` : '';
    return `${API_BASE_URL}/api/reports/export?format=${format}&window=${window}${tokenParam}`;
  }

  async askChat(prompt) {
    const res = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ prompt })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error en consulta IA' }));
      throw new Error(err.detail || 'Error en consulta IA');
    }
    return res.json();
  }

  async getLineage() {
    const res = await fetch(`${API_BASE_URL}/api/governance/lineage`, {
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Error al obtener linaje');
    return res.json();
  }

  async getQualityRules() {
    const res = await fetch(`${API_BASE_URL}/api/governance/quality-rules`, {
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Error al obtener reglas de calidad');
    return res.json();
  }

  async getPipelineStatus() {
    const res = await fetch(`${API_BASE_URL}/api/governance/status`, {
      headers: this.getHeaders()
    });
    if (!res.ok) throw new Error('Error al obtener estado de pipelines');
    return res.json();
  }

  async getQualityAuditFlags() {
    const res = await fetch(`${API_BASE_URL}/api/quality/audit-flags`, {
      headers: this.getHeaders()
    });
    if (res.status === 403) {
      throw new Error('ACCESO_DENEGADO: Solo usuarios con rol Administrador pueden auditar advertencias de calidad.');
    }
    if (!res.ok) throw new Error('Error al consultar auditoría de calidad');
    return res.json();
  }

  async triggerBackfill(startDate, endDate, minMagnitude = 4.0) {
    const res = await fetch(`${API_BASE_URL}/api/admin/backfill`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        start_date: startDate,
        end_date: endDate,
        min_magnitude: minMagnitude
      })
    });
    if (res.status === 403) {
      throw new Error('ACCESO_DENEGADO: Se requieren privilegios de Administrador para disparar backfills.');
    }
    if (!res.ok) throw new Error('Error al solicitar backfill');
    return res.json();
  }

  async regenerateReport(window = '24h') {
    const res = await fetch(`${API_BASE_URL}/api/admin/reports/regenerate?window=${window}`, {
      method: 'POST',
      headers: this.getHeaders()
    });
    if (res.status === 403) {
      throw new Error('ACCESO_DENEGADO: Se requieren privilegios de Administrador para forzar reporte.');
    }
    if (!res.ok) throw new Error('Error al regenerar reporte');
    return res.json();
  }

  createEventSource() {
    const tokenParam = this.token ? `?token=${encodeURIComponent(this.token)}` : '';
    return new EventSource(`${API_BASE_URL}/api/stream${tokenParam}`);
  }
}

export const api = new ApiService();
