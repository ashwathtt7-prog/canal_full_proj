import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import api from '../api';

export default function Slots() {
  const { user } = useAuth();
  const [slots, setSlots] = useState([]);
  const [summary, setSummary] = useState(null);
  const [selectedDate, setSelectedDate] = useState(new Date(Date.now() + 2*86400000).toISOString().split('T')[0]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);

  const loadSlots = async () => {
    setLoading(true);
    try {
      const [slotsRes, availRes] = await Promise.all([
        api.get(`/slots/?transit_date=${selectedDate}`),
        api.get(`/slots/availability?transit_date=${selectedDate}`),
      ]);
      setSlots(slotsRes.data);
      setSummary(availRes.data);
    } catch(e) {}
    setLoading(false);
  };

  useEffect(() => { loadSlots(); }, [selectedDate]);

  const generateSlots = async () => {
    setGenerating(true);
    try {
      await api.post(`/slots/generate-range?start_date=${selectedDate}&days=30`);
      loadSlots();
    } catch(e) {}
    setGenerating(false);
  };

  const categories = ['neopanamax', 'supers', 'regular'];
  const catLabels = { neopanamax: 'Neopanamax', supers: 'Supers', regular: 'Regular' };
  const getSlotsByCategory = (cat) => slots.filter(s => s.category === cat);

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Slot Management</h2>
          <p className="page-subtitle">View and manage daily slot configuration</p>
        </div>
        <div style={{display:'flex', gap: 12, alignItems:'center'}}>
          <input type="date" className="form-input" style={{width:180}}
            value={selectedDate} onChange={e => setSelectedDate(e.target.value)} />
          {(user?.role === 'planner' || user?.role === 'coordinator') && (
            <button className="btn btn-primary" onClick={generateSlots} disabled={generating}>
              {generating ? 'Generating...' : '⚙️ Generate Slots'}
            </button>
          )}
        </div>
      </div>

      {summary && (
        <div className="stats-grid" style={{marginBottom: 24}}>
          <div className="stat-card" style={{color:'var(--accent-blue)'}}>
            <div className="stat-value">{summary.total}</div>
            <div className="stat-label">Total Slots</div>
          </div>
          <div className="stat-card" style={{color:'var(--accent-emerald)'}}>
            <div className="stat-value">{summary.available}</div>
            <div className="stat-label">Available</div>
          </div>
          <div className="stat-card" style={{color:'var(--accent-purple)'}}>
            <div className="stat-value">{summary.booked}</div>
            <div className="stat-label">Booked</div>
          </div>
          <div className="stat-card" style={{color:'var(--accent-cyan)'}}>
            <div className="stat-value">{summary.competition + summary.auction}</div>
            <div className="stat-label">Competition / Auction</div>
          </div>
        </div>
      )}

      {loading ? <div className="loading-page"><div className="spinner" /></div> : (
        <div className="section-grid">
          {categories.map(cat => {
            const catSlots = getSlotsByCategory(cat);
            const nb = catSlots.filter(s => s.direction === 'northbound');
            const sb = catSlots.filter(s => s.direction === 'southbound');
            return (
              <div key={cat} className="card">
                <div className="card-header">
                  <div>
                    <div className="card-title">{catLabels[cat]}</div>
                    <div className="card-subtitle">{catSlots.length} slots total</div>
                  </div>
                </div>
                {['Northbound', 'Southbound'].map((dir, idx) => {
                  const dirSlots = idx === 0 ? nb : sb;
                  return (
                    <div key={dir} style={{marginBottom: 16}}>
                      <div style={{fontSize:12,fontWeight:700,color:'var(--text-muted)',marginBottom:8}}>
                        {dir === 'Northbound' ? '⬆️' : '⬇️'} {dir} ({dirSlots.length})
                      </div>
                      <div className="slot-grid">
                        {dirSlots.map(s => (
                          <div key={s.id} className={`slot-cell ${s.status}`}
                            title={`${s.period} | ${s.status}${s.is_auction_slot ? ' (Auction)' : ''}${s.is_conditioned ? ' (Cond.)' : ''}`}>
                            #{s.slot_number}<br/>
                            <span style={{fontSize:9}}>{s.period.replace('period_','P').replace('special','Sp')}</span><br/>
                            <span style={{fontSize:9}}>{s.status}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}

      {slots.length === 0 && !loading && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">🎰</div>
            <p>No slots found for this date. Click "Generate Slots" to create the daily configuration.</p>
          </div>
        </div>
      )}
    </div>
  );
}
