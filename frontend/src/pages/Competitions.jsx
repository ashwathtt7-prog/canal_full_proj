import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import api from '../api';

export default function Competitions() {
  const { user } = useAuth();
  const [competitions, setCompetitions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [applications, setApplications] = useState([]);
  const [vessels, setVessels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');
  const [applyModal, setApplyModal] = useState(false);
  const [selectedVessel, setSelectedVessel] = useState('');

  const load = async () => {
    setLoading(true);
    const r = await api.get('/competitions/');
    setCompetitions(r.data);
    if (user?.role === 'customer') {
      const v = await api.get('/reservations/vessels');
      setVessels(v.data);
    }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const loadApps = async (id) => {
    try {
      const r = await api.get(`/competitions/${id}/applications`);
      setApplications(r.data);
    } catch(e) { setApplications([]); }
    setSelected(id);
  };

  const action = async (id, act, body = {}) => {
    try {
      await api.post(`/competitions/${id}/${act}`, body);
      setMsg(`Action "${act}" completed!`);
      load(); if(selected) loadApps(selected);
      setTimeout(() => setMsg(''), 3000);
    } catch(e) { setMsg('Error: ' + JSON.stringify(e.response?.data?.detail || e.message)); }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Special Competitions</h2>
          <p className="page-subtitle">{competitions.length} competitions</p>
        </div>
      </div>
      {msg && <div style={{padding:'10px 16px',background:'rgba(6,182,212,.1)',border:'1px solid rgba(6,182,212,.2)',borderRadius:8,marginBottom:16,fontSize:13,color:'var(--accent-cyan)'}}>{msg}</div>}

      <div className="section-grid" style={{gridTemplateColumns: selected ? '1fr 1fr' : '1fr'}}>
        <div className="card">
          <div className="card-header"><div className="card-title">Competition List</div></div>
          {loading ? <div className="spinner" /> :
            competitions.map(c => (
              <div key={c.id} className="vessel-card" onClick={() => loadApps(c.id)} style={{cursor:'pointer', borderColor: selected === c.id ? 'var(--accent-cyan)' : undefined}}>
                <div style={{display:'flex',justifyContent:'space-between',marginBottom:8}}>
                  <strong>{c.category?.toUpperCase()} — {c.direction}</strong>
                  <span className={`badge badge-${c.status}`}>{c.status}</span>
                </div>
                <div style={{fontSize:12,color:'var(--text-muted)'}}>
                  Transit: {c.transit_date} | Trigger: {c.trigger_reason} | Apps: {c.application_count}
                </div>
                {c.winner_name && <div style={{fontSize:12,color:'var(--accent-amber)',marginTop:4}}>🏆 Winner: {c.winner_name}</div>}
                <div className="btn-group" style={{marginTop:8}}>
                  {user?.role === 'coordinator' && c.status === 'pending' && <button className="btn btn-sm btn-success" onClick={(e)=>{e.stopPropagation();action(c.id,'validate')}}>✓ Validate</button>}
                  {user?.role === 'coordinator' && c.status === 'validated' && <button className="btn btn-sm btn-primary" onClick={(e)=>{e.stopPropagation();action(c.id,'open')}}>🔓 Open</button>}
                  {user?.role === 'customer' && c.status === 'open' && <button className="btn btn-sm btn-primary" onClick={(e)=>{e.stopPropagation();setApplyModal(c.id)}}>📝 Apply</button>}
                  {user?.role === 'coordinator' && c.status === 'closed' && <button className="btn btn-sm btn-success" onClick={(e)=>{e.stopPropagation();action(c.id,'publish')}}>📢 Publish</button>}
                </div>
              </div>
            ))
          }
        </div>

        {selected && (
          <div className="card">
            <div className="card-header">
              <div className="card-title">Applications</div>
              {user?.role === 'coordinator' && <div className="card-subtitle">Click to select winner</div>}
            </div>
            {applications.length === 0 ? <div className="empty-state"><p>No applications yet</p></div> :
              applications.map((a, i) => (
                <div key={a.id} className="vessel-card" style={{borderColor: i === 0 ? 'var(--accent-amber)' : undefined}}>
                  <div style={{display:'flex',justifyContent:'space-between',marginBottom:4}}>
                    <strong>{a.customer_name}</strong>
                    <span className={`badge badge-${a.status}`}>{a.status}</span>
                  </div>
                  <div style={{fontSize:12,color:'var(--text-muted)'}}>
                    Vessel: {a.vessel_name} | Rank: {a.ranking_score} | HML: {a.hml_validated}
                  </div>
                  {i === 0 && <div style={{fontSize:11,color:'var(--accent-amber)',marginTop:4}}>⭐ Recommended by system</div>}
                  {user?.role === 'coordinator' && a.status !== 'winner' && a.status !== 'rejected' && (
                    <button className="btn btn-sm btn-success" style={{marginTop:8}}
                      onClick={() => action(selected, 'select-winner', { application_id: a.id })}>
                      🏆 Select as Winner
                    </button>
                  )}
                </div>
              ))
            }
          </div>
        )}
      </div>

      {applyModal && (
        <div className="modal-overlay" onClick={() => setApplyModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Apply to Competition</h3>
              <button className="modal-close" onClick={() => setApplyModal(false)}>×</button>
            </div>
            <div className="form-group">
              <label className="form-label">Select Vessel</label>
              <select className="form-select" value={selectedVessel} onChange={e => setSelectedVessel(e.target.value)}>
                <option value="">Choose...</option>
                {vessels.map(v => <option key={v.id} value={v.id}>{v.name} ({v.category})</option>)}
              </select>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setApplyModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => { action(applyModal, 'apply', { vessel_id: selectedVessel }); setApplyModal(false); }}>Submit Application</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
