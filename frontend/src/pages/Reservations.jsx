import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import api from '../api';

export default function Reservations() {
  const { user } = useAuth();
  const [reservations, setReservations] = useState([]);
  const [vessels, setVessels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modal, setModal] = useState(null); // { type: 'create' | 'action', data: {} }
  const [form, setForm] = useState({});
  const [msg, setMsg] = useState('');

  const load = async () => {
    setLoading(true);
    const [r, v] = await Promise.all([api.get('/reservations/'), api.get('/reservations/vessels')]);
    setReservations(r.data);
    setVessels(v.data);
    setLoading(false);
  };
  useEffect(() => { load(); }, []);

  const createReservation = async () => {
    try {
      await api.post('/reservations/', form);
      setModal(null); setMsg('Reservation created!'); load();
      setTimeout(() => setMsg(''), 3000);
    } catch(e) { setMsg('Error: ' + (e.response?.data?.detail || e.message)); }
  };

  const submitAction = async (resId, actionType) => {
    try {
      const res = await api.post(`/reservations/${resId}/${actionType}`, form);
      setModal(null); setMsg(`${actionType} request submitted! Fee: $${res.data.fee || res.data.penalty || 0}`);
      load(); setTimeout(() => setMsg(''), 4000);
    } catch(e) { setMsg('Error: ' + JSON.stringify(e.response?.data?.detail || e.message)); }
  };

  const actionTypes = [
    { key: 'change-date', label: 'Change Date', icon: '📅', fields: [{ name: 'new_date', type: 'date', label: 'New Date' }] },
    { key: 'substitution', label: 'Substitution', icon: '🔄', fields: [{ name: 'new_vessel_id', type: 'select', label: 'New Vessel', options: 'vessels' }] },
    { key: 'cancel', label: 'Cancel', icon: '❌', fields: [{ name: 'reason', type: 'text', label: 'Reason' }] },
    { key: 'daylight', label: 'Daylight Transit', icon: '☀️', fields: [{ name: 'reason', type: 'text', label: 'Reason' }] },
    { key: 'sdtr', label: 'Same Date Transit', icon: '⏰', fields: [{ name: 'reason', type: 'text', label: 'Reason' }] },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">{user?.role === 'customer' ? 'My Reservations' : 'All Reservations'}</h2>
          <p className="page-subtitle">{reservations.length} reservations found</p>
        </div>
        {user?.role === 'customer' && (
          <button className="btn btn-primary" onClick={() => { setForm({}); setModal({ type: 'create' }); }}>
            ➕ New Booking
          </button>
        )}
      </div>

      {msg && <div style={{padding:'10px 16px',background:'rgba(59,130,246,.1)',border:'1px solid rgba(59,130,246,.2)',borderRadius:8,marginBottom:16,fontSize:13,color:'var(--accent-cyan)'}}>{msg}</div>}

      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead><tr>
              <th>Vessel</th><th>Customer</th><th>Transit Date</th><th>Direction</th>
              <th>Category</th><th>Origin</th><th>Status</th><th>Booking Fee</th><th>Actions</th>
            </tr></thead>
            <tbody>
              {loading ? <tr><td colSpan={9}><div className="spinner" /></td></tr> :
                reservations.map(r => (
                  <tr key={r.id}>
                    <td style={{fontWeight:600}}>{r.vessel_name || '—'}</td>
                    <td>{r.customer_name || '—'}</td>
                    <td>{r.transit_date}</td>
                    <td>{r.direction === 'northbound' ? '⬆️ N/B' : '⬇️ S/B'}</td>
                    <td><span className="badge badge-booked">{r.category}</span></td>
                    <td>{r.origin}</td>
                    <td><span className={`badge badge-${r.status}`}>{r.status}</span></td>
                    <td style={{fontWeight:700}}>${r.booking_fee?.toLocaleString()}</td>
                    <td>
                      {r.status === 'booked' && (
                        <div className="btn-group">
                          {actionTypes.map(at => (
                            <button key={at.key} className="btn btn-sm btn-secondary" title={at.label}
                              onClick={() => { setForm({}); setModal({ type: 'action', resId: r.id, action: at }); }}>
                              {at.icon}
                            </button>
                          ))}
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              }
              {!loading && reservations.length === 0 && (
                <tr><td colSpan={9}><div className="empty-state"><p>No reservations yet</p></div></td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Create Reservation Modal */}
      {modal?.type === 'create' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">New Booking Request</h3>
              <button className="modal-close" onClick={() => setModal(null)}>×</button>
            </div>
            <div className="form-group">
              <label className="form-label">Vessel</label>
              <select className="form-select" value={form.vessel_id || ''} onChange={e => setForm({...form, vessel_id: e.target.value})}>
                <option value="">Select vessel...</option>
                {vessels.map(v => <option key={v.id} value={v.id}>{v.name} ({v.category})</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Transit Date</label>
              <input className="form-input" type="date" value={form.transit_date || ''} onChange={e => setForm({...form, transit_date: e.target.value})} />
            </div>
            <div className="form-group">
              <label className="form-label">Direction</label>
              <select className="form-select" value={form.direction || ''} onChange={e => setForm({...form, direction: e.target.value})}>
                <option value="">Select...</option>
                <option value="northbound">Northbound</option>
                <option value="southbound">Southbound</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select className="form-select" value={form.category || ''} onChange={e => setForm({...form, category: e.target.value})}>
                <option value="">Select...</option>
                <option value="neopanamax">Neopanamax</option>
                <option value="supers">Supers</option>
                <option value="regular">Regular</option>
              </select>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={createReservation}>Submit Booking</button>
            </div>
          </div>
        </div>
      )}

      {/* Action Modal */}
      {modal?.type === 'action' && (
        <div className="modal-overlay" onClick={() => setModal(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">{modal.action.icon} {modal.action.label}</h3>
              <button className="modal-close" onClick={() => setModal(null)}>×</button>
            </div>
            {modal.action.fields.map(f => (
              <div className="form-group" key={f.name}>
                <label className="form-label">{f.label}</label>
                {f.type === 'select' ? (
                  <select className="form-select" value={form[f.name] || ''} onChange={e => setForm({...form, [f.name]: e.target.value})}>
                    <option value="">Select...</option>
                    {f.options === 'vessels' && vessels.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                  </select>
                ) : (
                  <input className="form-input" type={f.type} value={form[f.name] || ''} onChange={e => setForm({...form, [f.name]: e.target.value})} />
                )}
              </div>
            ))}
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setModal(null)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => submitAction(modal.resId, modal.action.key)}>Submit</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
