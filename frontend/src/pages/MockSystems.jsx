import { useState, useEffect } from 'react';
import api from '../api';

export default function MockSystems() {
  const [vumpa, setVumpa] = useState(null);
  const [evtms, setEvtms] = useState(null);
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('vumpa');

  const loadAll = async () => {
    try {
      const [v, e, b] = await Promise.all([
        api.get('/mock/vumpa/vessels'),
        api.get('/mock/evtms/traffic'),
        api.get('/mock/billing/summary'),
      ]);
      setVumpa(v.data); setEvtms(e.data); setBilling(b.data);
    } catch(e) {}
    setLoading(false);
  };
  useEffect(() => { loadAll(); }, []);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const iv = setInterval(loadAll, 5000);
    return () => clearInterval(iv);
  }, []);

  const statusColors = {
    approaching: 'var(--accent-cyan)', in_transit: 'var(--accent-emerald)',
    waiting: 'var(--accent-amber)', completed: 'var(--text-muted)', anchored: 'var(--accent-purple)',
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">External Systems Monitor</h2>
          <p className="page-subtitle">Simulated real-time data from VUMPA, EVTMS, and Billing</p>
        </div>
        <div style={{display:'flex',gap:8}}>
          {['vumpa', 'evtms', 'billing'].map(tab => (
            <button key={tab} className={`btn btn-sm ${activeTab === tab ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab(tab)}>
              {tab === 'vumpa' ? '🛰️ VUMPA' : tab === 'evtms' ? '🚦 EVTMS' : '💰 Billing'}
            </button>
          ))}
        </div>
      </div>

      {loading ? <div className="loading-page"><div className="spinner" /></div> : (
        <>
          {activeTab === 'vumpa' && vumpa && (
            <div>
              <div className="stats-grid" style={{marginBottom:20}}>
                <div className="stat-card" style={{color:'var(--accent-cyan)'}}>
                  <div className="stat-value">{vumpa.vessel_count}</div>
                  <div className="stat-label">Active Vessels</div>
                </div>
                <div className="stat-card" style={{color:'var(--accent-emerald)'}}>
                  <div className="stat-value">{vumpa.vessels?.filter(v=>v.status==='in_transit').length}</div>
                  <div className="stat-label">In Transit</div>
                </div>
                <div className="stat-card" style={{color:'var(--accent-amber)'}}>
                  <div className="stat-value">{vumpa.vessels?.filter(v=>v.status==='waiting').length}</div>
                  <div className="stat-label">Waiting</div>
                </div>
                <div className="stat-card" style={{color:'var(--accent-blue)'}}>
                  <div className="stat-value">{vumpa.vessels?.filter(v=>v.status==='approaching').length}</div>
                  <div className="stat-label">Approaching</div>
                </div>
              </div>
              <div className="card">
                <div className="card-header">
                  <div className="card-title">🛰️ VUMPA — Vessel Positions</div>
                  <div style={{fontSize:11,color:'var(--accent-emerald)'}}>● Live — Updates every 5s</div>
                </div>
                <div className="table-wrapper">
                  <table>
                    <thead><tr>
                      <th>Vessel</th><th>Category</th><th>Status</th><th>Position</th>
                      <th>Speed</th><th>Heading</th><th>Draft</th><th>ETA</th>
                    </tr></thead>
                    <tbody>
                      {vumpa.vessels?.map(v => (
                        <tr key={v.id}>
                          <td style={{fontWeight:600}}>{v.name}</td>
                          <td><span className="badge badge-booked">{v.category}</span></td>
                          <td><span style={{color: statusColors[v.status]}}>{v.status?.replace(/_/g,' ')}</span></td>
                          <td style={{fontSize:11}}>{v.latitude?.toFixed(4)}°N, {v.longitude?.toFixed(4)}°W</td>
                          <td>{v.speed_knots} kn</td>
                          <td>{v.heading}°</td>
                          <td>{v.draft_meters}m</td>
                          <td style={{fontSize:11}}>{new Date(v.eta).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'evtms' && evtms && (
            <div>
              <div className="stats-grid" style={{marginBottom:20}}>
                <div className="stat-card" style={{color:'var(--accent-emerald)'}}>
                  <div className="stat-value">{evtms.operational_summary?.vessels_in_transit}</div>
                  <div className="stat-label">In Transit</div>
                </div>
                <div className="stat-card" style={{color:'var(--accent-amber)'}}>
                  <div className="stat-value">{evtms.operational_summary?.vessels_waiting}</div>
                  <div className="stat-label">Waiting</div>
                </div>
                <div className="stat-card" style={{color:'var(--accent-cyan)'}}>
                  <div className="stat-value">{evtms.operational_summary?.locks_active}</div>
                  <div className="stat-label">Locks Active</div>
                </div>
                <div className="stat-card" style={{color:'var(--accent-blue)'}}>
                  <div className="stat-value">{evtms.operational_summary?.avg_transit_time_hours}h</div>
                  <div className="stat-label">Avg Transit Time</div>
                </div>
              </div>
              <div className="card">
                <div className="card-header">
                  <div className="card-title">🚦 EVTMS — Traffic Events</div>
                  <div style={{fontSize:11,color:'var(--accent-emerald)'}}>● Live — Updates every 5s</div>
                </div>
                {evtms.events?.map(e => (
                  <div key={e.id} className={`event-card ${e.priority}`}>
                    <div style={{display:'flex',justifyContent:'space-between',marginBottom:4}}>
                      <strong style={{fontSize:13}}>{e.type?.replace(/_/g,' ')}</strong>
                      <span style={{fontSize:11,color:'var(--text-muted)'}}>{new Date(e.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div style={{fontSize:12,color:'var(--text-secondary)'}}>
                      {e.vessel_name} — {e.location} — {e.direction === 'northbound' ? '⬆️' : '⬇️'} {e.direction}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'billing' && billing && (
            <div>
              <div className="stats-grid" style={{marginBottom:20}}>
                <div className="stat-card" style={{color:'var(--accent-emerald)'}}>
                  <div className="stat-value">${(billing.total_revenue/1000000).toFixed(1)}M</div>
                  <div className="stat-label">Total Revenue</div>
                </div>
                <div className="stat-card" style={{color:'var(--accent-blue)'}}>
                  <div className="stat-value">{billing.total_invoices}</div>
                  <div className="stat-label">Total Invoices</div>
                </div>
                <div className="stat-card" style={{color:'var(--accent-amber)'}}>
                  <div className="stat-value">{billing.pending_payments}</div>
                  <div className="stat-label">Pending Payments</div>
                </div>
              </div>
              <div className="card">
                <div className="card-header"><div className="card-title">💰 Recent Invoices</div></div>
                <div className="table-wrapper">
                  <table>
                    <thead><tr><th>Invoice</th><th>Customer</th><th>Amount</th><th>Type</th><th>Status</th><th>Date</th></tr></thead>
                    <tbody>
                      {billing.recent_invoices?.map(inv => (
                        <tr key={inv.id}>
                          <td style={{fontWeight:600}}>{inv.id}</td>
                          <td>{inv.customer}</td>
                          <td style={{fontWeight:700}}>${inv.amount?.toLocaleString()}</td>
                          <td>{inv.type?.replace(/_/g,' ')}</td>
                          <td><span className={`badge badge-${inv.status === 'paid' ? 'approved' : inv.status === 'overdue' ? 'rejected' : 'pending'}`}>{inv.status}</span></td>
                          <td style={{fontSize:12}}>{new Date(inv.date).toLocaleDateString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
