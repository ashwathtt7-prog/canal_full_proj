import { useState, useEffect } from 'react';
import { useAuth } from '../AuthContext';
import api from '../api';

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get('/dashboard/stats'),
      api.get('/dashboard/recent-activity'),
    ]).then(([s, a]) => {
      setStats(s.data);
      setActivity(a.data);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;

  const statCards = [
    { label: 'Total Slots', value: stats?.total_slots || 0, icon: '🎰', color: 'var(--accent-blue)' },
    { label: 'Available', value: stats?.available_slots || 0, icon: '✅', color: 'var(--accent-emerald)' },
    { label: 'Booked', value: stats?.booked_slots || 0, icon: '📦', color: 'var(--accent-purple)' },
    { label: 'Active Competitions', value: stats?.active_competitions || 0, icon: '🏆', color: 'var(--accent-cyan)' },
    { label: 'Active Auctions', value: stats?.active_auctions || 0, icon: '🔨', color: 'var(--accent-amber)' },
    { label: 'Pending Transactions', value: stats?.pending_transactions || 0, icon: '⏳', color: 'var(--accent-orange)' },
    { label: user?.role === 'customer' ? 'My Reservations' : 'Total Reservations', value: stats?.total_reservations || 0, icon: '📋', color: 'var(--accent-blue)' },
    { label: 'Total Revenue', value: `$${(stats?.total_revenue || 0).toLocaleString()}`, icon: '💰', color: 'var(--accent-emerald)' },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h2 className="page-title">Welcome, {user?.full_name}</h2>
          <p className="page-subtitle">
            {user?.role === 'planner' ? 'Manage slot configurations, auctions, and operational reviews'
              : user?.role === 'coordinator' ? 'Handle bookings, competitions, and pending transactions'
              : 'View your reservations and participate in auctions'}
          </p>
        </div>
      </div>

      <div className="stats-grid">
        {statCards.map((s, i) => (
          <div key={i} className="stat-card" style={{color: s.color}}>
            <div className="stat-icon" style={{background: `${s.color}15`}}>{s.icon}</div>
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="card-title">Recent Activity</div>
            <div className="card-subtitle">Latest transactions and billing events</div>
          </div>
        </div>
        {activity.length > 0 ? activity.map((a, i) => (
          <div key={i} className="activity-item">
            <div className="activity-icon" style={{
              background: a.type === 'billing' ? 'rgba(16,185,129,.12)' : 'rgba(59,130,246,.12)',
              color: a.type === 'billing' ? 'var(--accent-emerald)' : 'var(--accent-blue)'
            }}>
              {a.type === 'billing' ? '💰' : '📝'}
            </div>
            <div style={{flex: 1}}>
              <div className="activity-text">
                <strong>{a.customer_name}</strong> — {a.subtype?.replace(/_/g, ' ')}
                {a.total ? ` — $${a.total.toLocaleString()}` : ''}
              </div>
              <div className="activity-time">{new Date(a.timestamp).toLocaleString()}</div>
            </div>
            {a.status && <span className={`badge badge-${a.status}`}>{a.status}</span>}
          </div>
        )) : <div className="empty-state"><p>No recent activity</p></div>}
      </div>
    </div>
  );
}
