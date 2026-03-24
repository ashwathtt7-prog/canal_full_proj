import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import api from '../api';

export default function Transactions() {
  const { user } = useAuth();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');
  const [filter, setFilter] = useState('all');

  const load = async () => {
    setLoading(true);
    const endpoint = (user?.role === 'coordinator' || user?.role === 'planner') && filter === 'pending'
      ? '/transactions/pending' : '/transactions/';
    const r = await api.get(endpoint);
    setTransactions(r.data);
    setLoading(false);
  };
  useEffect(() => { load(); }, [filter]);

  const reviewAction = async (id, act) => {
    try {
      await api.post(`/transactions/${id}/${act}`, { notes: '' });
      setMsg(`Transaction ${act}d successfully!`);
      load();
      setTimeout(() => setMsg(''), 3000);
    } catch(e) { setMsg('Error: ' + (e.response?.data?.detail || e.message)); }
  };

  const typeIcons = {
    change_date: '📅', substitution: '🔄', swap: '🔀', tia: '⏩',
    last_minute: '⚡', sdtr: '⏰', cancellation: '❌', void: '🚫',
    daylight_transit: '☀️'
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">{user?.role === 'customer' ? 'My Transactions' : 'Transaction Management'}</h2>
          <p className="page-subtitle">{transactions.length} transactions</p>
        </div>
        {(user?.role === 'coordinator' || user?.role === 'planner') && (
          <div style={{display:'flex',gap:8}}>
            <button className={`btn btn-sm ${filter === 'all' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setFilter('all')}>All</button>
            <button className={`btn btn-sm ${filter === 'pending' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setFilter('pending')}>⏳ Pending Review</button>
          </div>
        )}
      </div>
      {msg && <div style={{padding:'10px 16px',background:'rgba(16,185,129,.1)',border:'1px solid rgba(16,185,129,.2)',borderRadius:8,marginBottom:16,fontSize:13,color:'var(--accent-emerald)'}}>{msg}</div>}

      <div className="card">
        <div className="table-wrapper">
          <table>
            <thead><tr>
              <th>Type</th><th>Vessel</th><th>Customer</th><th>Status</th>
              <th>Fees</th><th>Penalties</th><th>Form</th><th>Created</th>
              {(user?.role === 'coordinator' || user?.role === 'planner') && <th>Actions</th>}
            </tr></thead>
            <tbody>
              {loading ? <tr><td colSpan={9}><div className="spinner" /></td></tr> :
                transactions.map(tx => (
                  <tr key={tx.id}>
                    <td>
                      <span style={{fontSize:16,marginRight:6}}>{typeIcons[tx.type] || '📝'}</span>
                      <span style={{fontWeight:600}}>{tx.type?.replace(/_/g, ' ')}</span>
                    </td>
                    <td>{tx.vessel_name || '—'}</td>
                    <td>{tx.customer_name || '—'}</td>
                    <td><span className={`badge badge-${tx.status}`}>{tx.status?.replace(/_/g, ' ')}</span></td>
                    <td style={{fontWeight:600}}>${(tx.fees || 0).toLocaleString()}</td>
                    <td style={{fontWeight:600,color: tx.penalties > 0 ? 'var(--accent-rose)' : undefined}}>
                      ${(tx.penalties || 0).toLocaleString()}
                    </td>
                    <td>{tx.form_generated === 'yes' ? '✅' : '—'}</td>
                    <td style={{fontSize:12,color:'var(--text-muted)'}}>{new Date(tx.created_at).toLocaleString()}</td>
                    {(user?.role === 'coordinator' || user?.role === 'planner') && (
                      <td>
                        {(tx.status === 'pending' || tx.status === 'planner_review' || tx.status === 'under_review') && (
                          <div className="btn-group">
                            <button className="btn btn-sm btn-success" onClick={() => reviewAction(tx.id, 'approve')}>✓</button>
                            <button className="btn btn-sm btn-danger" onClick={() => reviewAction(tx.id, 'reject')}>✕</button>
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
