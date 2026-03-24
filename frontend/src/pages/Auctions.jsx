import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import api from '../api';

export default function Auctions() {
  const { user } = useAuth();
  const [auctions, setAuctions] = useState([]);
  const [monitor, setMonitor] = useState(null);
  const [vessels, setVessels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');
  const [bidModal, setBidModal] = useState(null);
  const [bidForm, setBidForm] = useState({ vessel_id: '', amount: '', alternate_date: '' });

  const load = async () => {
    setLoading(true);
    const r = await api.get('/auctions/');
    setAuctions(r.data);
    if (user?.role === 'customer') {
      const v = await api.get('/reservations/vessels');
      setVessels(v.data);
    }
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const loadMonitor = async (id) => {
    try {
      const r = await api.get(`/auctions/${id}/monitor`);
      setMonitor({ ...r.data, auction_id: id });
    } catch(e) {}
  };

  const action = async (id, act, body = {}) => {
    try {
      const r = await api.post(`/auctions/${id}/${act}`, body);
      setMsg(`${act}: ${r.data.message}`);
      load(); if(monitor?.auction_id === id) loadMonitor(id);
      setTimeout(() => setMsg(''), 4000);
    } catch(e) { setMsg('Error: ' + JSON.stringify(e.response?.data?.detail || e.message)); }
  };

  const submitBid = async () => {
    try {
      const payload = {
        vessel_id: bidForm.vessel_id,
        amount: parseInt(bidForm.amount) || 0,
        alternate_date: bidForm.alternate_date || null,
        notes: bidForm.notes || null,
      };
      await api.post(`/auctions/${bidModal}/bid`, payload);
      setMsg('Bid submitted successfully!');
      setBidModal(null); load(); loadMonitor(bidModal);
      setTimeout(() => setMsg(''), 3000);
    } catch(e) { setMsg('Error: ' + JSON.stringify(e.response?.data?.detail || e.message)); }
  };

  // Auto-refresh monitor every 10 seconds
  useEffect(() => {
    if (!monitor) return;
    const iv = setInterval(() => loadMonitor(monitor.auction_id), 10000);
    return () => clearInterval(iv);
  }, [monitor?.auction_id]);

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Auctions</h2>
          <p className="page-subtitle">{auctions.length} auctions</p>
        </div>
      </div>
      {msg && <div style={{padding:'10px 16px',background:'rgba(139,92,246,.1)',border:'1px solid rgba(139,92,246,.2)',borderRadius:8,marginBottom:16,fontSize:13,color:'var(--accent-purple)'}}>{msg}</div>}

      <div className="section-grid" style={{gridTemplateColumns: monitor ? '1fr 1.2fr' : '1fr'}}>
        <div className="card">
          <div className="card-header"><div className="card-title">Auction List</div></div>
          {loading ? <div className="spinner" /> :
            auctions.map(a => (
              <div key={a.id} className="vessel-card" onClick={() => loadMonitor(a.id)}
                style={{cursor:'pointer', borderColor: monitor?.auction_id === a.id ? 'var(--accent-purple)' : undefined}}>
                <div style={{display:'flex',justifyContent:'space-between',marginBottom:8}}>
                  <strong>{a.category?.toUpperCase()} — {a.direction}</strong>
                  <span className={`badge badge-${a.status}`}>{a.status}</span>
                </div>
                <div style={{fontSize:12,color:'var(--text-muted)'}}>
                  Transit: {a.transit_date} | Type: {a.auction_type} | Base: ${a.base_price?.toLocaleString()}
                </div>
                <div style={{fontSize:12,color:'var(--text-muted)',marginTop:2}}>
                  Bids: {a.total_bids} | Views: {a.total_views}
                  {a.winning_bid && ` | Winning: $${a.winning_bid.toLocaleString()}`}
                </div>
                {a.winner_name && <div style={{fontSize:12,color:'var(--accent-amber)',marginTop:4}}>🏆 {a.winner_name}</div>}
                <div className="btn-group" style={{marginTop:8}}>
                  {user?.role === 'planner' && a.status === 'proposed' && <button className="btn btn-sm btn-success" onClick={e=>{e.stopPropagation();action(a.id,'approve',{})}}>✓ Approve</button>}
                  {user?.role === 'coordinator' && a.status === 'approved' && <button className="btn btn-sm btn-primary" onClick={e=>{e.stopPropagation();action(a.id,'publish')}}>📢 Publish</button>}
                  {user?.role === 'customer' && a.status === 'bidding' && <button className="btn btn-sm btn-primary" onClick={e=>{e.stopPropagation();setBidForm({vessel_id:'',amount:'',alternate_date:''});setBidModal(a.id)}}>💰 Place Bid</button>}
                  {(user?.role === 'coordinator' || user?.role === 'planner') && a.status === 'bidding' && <button className="btn btn-sm btn-danger" onClick={e=>{e.stopPropagation();action(a.id,'close')}}>🔒 Close</button>}
                  {user?.role === 'coordinator' && a.status === 'closed' && <button className="btn btn-sm btn-success" onClick={e=>{e.stopPropagation();action(a.id,'award')}}>🏆 Award</button>}
                </div>
              </div>
            ))
          }
        </div>

        {monitor && (
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">📊 Auction Monitor</div>
                <div className="card-subtitle">Real-time updates every 10s</div>
              </div>
              <span className={`badge badge-${monitor.status}`}>{monitor.status}</span>
            </div>
            <div className="stats-grid" style={{gridTemplateColumns:'repeat(4,1fr)',marginBottom:16}}>
              <div className="stat-card" style={{color:'var(--accent-blue)',padding:12}}>
                <div className="stat-value" style={{fontSize:20}}>{monitor.total_bids}</div>
                <div className="stat-label">Total Bids</div>
              </div>
              <div className="stat-card" style={{color:'var(--accent-emerald)',padding:12}}>
                <div className="stat-value" style={{fontSize:20}}>${monitor.highest_bid?.toLocaleString()}</div>
                <div className="stat-label">Highest</div>
              </div>
              <div className="stat-card" style={{color:'var(--accent-amber)',padding:12}}>
                <div className="stat-value" style={{fontSize:20}}>${monitor.lowest_bid?.toLocaleString()}</div>
                <div className="stat-label">Lowest</div>
              </div>
              <div className="stat-card" style={{color:'var(--accent-purple)',padding:12}}>
                <div className="stat-value" style={{fontSize:20}}>{monitor.total_views}</div>
                <div className="stat-label">Views</div>
              </div>
            </div>
            {monitor.time_remaining && <div style={{fontSize:12,color:'var(--accent-amber)',marginBottom:12}}>⏰ Time remaining: {monitor.time_remaining}</div>}
            <div style={{fontSize:13,fontWeight:700,marginBottom:8}}>Bid Rankings</div>
            {monitor.bids?.map((b, i) => (
              <div key={b.id} className="vessel-card" style={{borderColor: i === 0 ? 'var(--accent-emerald)' : undefined}}>
                <div style={{display:'flex',justifyContent:'space-between'}}>
                  <span style={{fontWeight:700,color: i === 0 ? 'var(--accent-emerald)' : 'var(--text-primary)'}}>
                    {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i+1}`} ${b.amount?.toLocaleString()}
                  </span>
                  <span className={`badge badge-${b.status}`}>{b.status}</span>
                </div>
                <div style={{fontSize:12,color:'var(--text-muted)',marginTop:4}}>
                  {b.customer_name} — {b.vessel_name}
                </div>
              </div>
            ))}
            {(!monitor.bids || monitor.bids.length === 0) && <div className="empty-state"><p>No bids yet</p></div>}
          </div>
        )}
      </div>

      {bidModal && (
        <div className="modal-overlay" onClick={() => setBidModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">💰 Place Bid</h3>
              <button className="modal-close" onClick={() => setBidModal(null)}>×</button>
            </div>
            <div className="form-group">
              <label className="form-label">Vessel</label>
              <select className="form-select" value={bidForm.vessel_id} onChange={e => setBidForm({...bidForm, vessel_id: e.target.value})}>
                <option value="">Select...</option>
                {vessels.map(v => <option key={v.id} value={v.id}>{v.name} ({v.category})</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Bid Amount (USD)</label>
              <input className="form-input" type="number" placeholder="Enter amount..." value={bidForm.amount} onChange={e => setBidForm({...bidForm, amount: e.target.value})} />
            </div>
            <div className="form-group">
              <label className="form-label">Alternate Date (optional)</label>
              <input className="form-input" type="date" value={bidForm.alternate_date} onChange={e => setBidForm({...bidForm, alternate_date: e.target.value})} />
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setBidModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={submitBid}>Submit Bid</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
