import { useState, useEffect } from 'react';
import api from '../api';

export default function SlotHistory() {
  const [slots, setSlots] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [date, setDate] = useState(new Date(Date.now() + 2*86400000).toISOString().split('T')[0]);

  const loadSlots = async () => {
    setLoading(true);
    const r = await api.get(`/slots/?transit_date=${date}&status=booked`);
    setSlots(r.data);
    setLoading(false);
  };
  useEffect(() => { loadSlots(); }, [date]);

  const loadHistory = async (slotId) => {
    setSelectedSlot(slotId);
    const r = await api.get(`/slots/${slotId}/history`);
    setHistory(r.data);
  };

  const totalRevenue = history.reduce((sum, h) => sum + h.total, 0);
  const eventColors = {
    booking: 'var(--accent-blue)', substitution: 'var(--accent-purple)',
    swap: 'var(--accent-cyan)', cancellation: 'var(--accent-rose)',
    auction_win: 'var(--accent-amber)', void: 'var(--text-muted)',
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Slot Ownership & Price History</h2>
          <p className="page-subtitle">Track slot value evolution and ownership changes</p>
        </div>
        <input type="date" className="form-input" style={{width:180}} value={date} onChange={e => setDate(e.target.value)} />
      </div>

      <div className="section-grid" style={{gridTemplateColumns: selectedSlot ? '1fr 1.3fr' : '1fr'}}>
        <div className="card">
          <div className="card-header"><div className="card-title">Booked Slots</div></div>
          {loading ? <div className="spinner" /> :
            slots.length === 0 ? <div className="empty-state"><p>No booked slots for this date</p></div> :
            slots.map(s => (
              <div key={s.id} className="vessel-card" onClick={() => loadHistory(s.id)}
                style={{cursor:'pointer', borderColor: selectedSlot === s.id ? 'var(--accent-cyan)' : undefined}}>
                <div style={{display:'flex',justifyContent:'space-between'}}>
                  <strong>Slot #{s.slot_number} — {s.category?.toUpperCase()}</strong>
                  <span style={{fontWeight:700,color:'var(--accent-emerald)'}}>${s.current_price?.toLocaleString()}</span>
                </div>
                <div style={{fontSize:12,color:'var(--text-muted)',marginTop:4}}>
                  {s.direction} | {s.period?.replace(/_/g, ' ')} {s.is_auction_slot ? '(Auction)' : ''}
                </div>
              </div>
            ))
          }
        </div>

        {selectedSlot && (
          <div className="card">
            <div className="card-header">
              <div>
                <div className="card-title">📈 Price History Timeline</div>
                <div className="card-subtitle">
                  Total Revenue: <span style={{color:'var(--accent-emerald)',fontWeight:800,fontSize:16}}>${totalRevenue.toLocaleString()}</span>
                </div>
              </div>
            </div>
            {history.length === 0 ? <div className="empty-state"><p>No history for this slot</p></div> : (
              <div className="timeline">
                {history.map((h, i) => (
                  <div key={h.id} className="timeline-item">
                    <div style={{position:'absolute',left:-24,top:6,width:12,height:12,borderRadius:'50%',background:eventColors[h.event_type] || 'var(--accent-blue)',border:'2px solid var(--bg-card)'}} />
                    <div className="time">{new Date(h.timestamp).toLocaleString()}</div>
                    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:4}}>
                      <span className={`badge badge-${h.event_type === 'cancellation' ? 'cancelled' : h.event_type === 'void' ? 'voided' : 'booked'}`}>
                        {h.event_type?.replace(/_/g, ' ')}
                      </span>
                      <span className="amount">${h.total?.toLocaleString()}</span>
                    </div>
                    <div className="event">{h.description}</div>
                    <div style={{fontSize:11,color:'var(--text-muted)',marginTop:4}}>
                      {h.customer_name && `Customer: ${h.customer_name}`}
                      {h.vessel_name && ` | Vessel: ${h.vessel_name}`}
                    </div>
                    {h.fees > 0 && <div style={{fontSize:11,color:'var(--accent-amber)'}}>Fees: ${h.fees.toLocaleString()}</div>}
                    {h.penalties > 0 && <div style={{fontSize:11,color:'var(--accent-rose)'}}>Penalties: ${h.penalties.toLocaleString()}</div>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
