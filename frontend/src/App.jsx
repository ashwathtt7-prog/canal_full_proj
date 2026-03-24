import { Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { useState, useEffect } from 'react';
import api from './api';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Slots from './pages/Slots';
import Reservations from './pages/Reservations';
import Competitions from './pages/Competitions';
import Auctions from './pages/Auctions';
import Transactions from './pages/Transactions';
import SlotHistory from './pages/SlotHistory';
import MockSystems from './pages/MockSystems';

const NAV_ITEMS = {
  planner: [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/slots', label: 'Slot Management', icon: '🎰' },
    { path: '/reservations', label: 'Reservations', icon: '📋' },
    { path: '/transactions', label: 'Pending Reviews', icon: '⏳' },
    { path: '/competitions', label: 'Competitions', icon: '🏆' },
    { path: '/auctions', label: 'Auctions', icon: '🔨' },
    { path: '/slot-history', label: 'Slot History', icon: '📈' },
    { path: '/mock-systems', label: 'VUMPA / EVTMS', icon: '🛰️' },
  ],
  coordinator: [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/slots', label: 'Slot Management', icon: '🎰' },
    { path: '/reservations', label: 'Reservations', icon: '📋' },
    { path: '/transactions', label: 'Pending Transactions', icon: '⏳' },
    { path: '/competitions', label: 'Competitions', icon: '🏆' },
    { path: '/auctions', label: 'Auctions', icon: '🔨' },
    { path: '/slot-history', label: 'Slot History', icon: '📈' },
    { path: '/mock-systems', label: 'VUMPA / EVTMS', icon: '🛰️' },
  ],
  customer: [
    { path: '/dashboard', label: 'Dashboard', icon: '📊' },
    { path: '/slots', label: 'Slot Availability', icon: '🎰' },
    { path: '/reservations', label: 'My Reservations', icon: '📋' },
    { path: '/transactions', label: 'My Transactions', icon: '📝' },
    { path: '/competitions', label: 'Competitions', icon: '🏆' },
    { path: '/auctions', label: 'Auctions', icon: '🔨' },
  ],
};

function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [notifCount, setNotifCount] = useState(0);
  const [showNotifs, setShowNotifs] = useState(false);
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    api.get('/notifications/count').then(r => setNotifCount(r.data.unread_count)).catch(() => {});
    const iv = setInterval(() => {
      api.get('/notifications/count').then(r => setNotifCount(r.data.unread_count)).catch(() => {});
    }, 15000);
    return () => clearInterval(iv);
  }, []);

  const loadNotifs = async () => {
    const r = await api.get('/notifications');
    setNotifications(r.data);
    setShowNotifs(!showNotifs);
  };

  const markRead = async (id) => {
    await api.post(`/notifications/${id}/read`);
    setNotifications(prev => prev.map(n => n.id === id ? {...n, is_read: true} : n));
    setNotifCount(prev => Math.max(0, prev - 1));
  };

  const navItems = NAV_ITEMS[user?.role] || [];

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-icon">P</div>
          <div>
            <h2>Panama Canal</h2>
            <span>Booking System</span>
          </div>
        </div>
        <nav className="sidebar-nav">
          <div className="nav-section">
            <div className="nav-section-title">Navigation</div>
            {navItems.map(item => (
              <Link to={item.path} key={item.path}
                className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}>
                <span className="icon">{item.icon}</span> {item.label}
              </Link>
            ))}
          </div>
        </nav>
        <div className="sidebar-footer">
          <div className="avatar">{user?.full_name?.charAt(0) || '?'}</div>
          <div className="user-info">
            <div className="name">{user?.full_name}</div>
            <div className="role">{user?.role}</div>
          </div>
        </div>
      </aside>

      <div className="main-content">
        <header className="topbar">
          <h1>{navItems.find(i => i.path === location.pathname)?.label || 'Panama Canal'}</h1>
          <div className="topbar-actions">
            <div className="notif-badge" onClick={loadNotifs}>
              🔔 {notifCount > 0 && <span className="count">{notifCount}</span>}
            </div>
            <button className="btn-logout" onClick={() => { logout(); navigate('/login'); }}>
              Logout
            </button>
          </div>
        </header>
        <div className="page-content">
          <Routes>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/slots" element={<Slots />} />
            <Route path="/reservations" element={<Reservations />} />
            <Route path="/transactions" element={<Transactions />} />
            <Route path="/competitions" element={<Competitions />} />
            <Route path="/auctions" element={<Auctions />} />
            <Route path="/slot-history" element={<SlotHistory />} />
            <Route path="/mock-systems" element={<MockSystems />} />
            <Route path="*" element={<Navigate to="/dashboard" />} />
          </Routes>
        </div>
      </div>

      {showNotifs && (
        <div className="notif-panel">
          <div style={{display:'flex',justifyContent:'space-between',marginBottom:16}}>
            <h3>Notifications</h3>
            <button className="btn btn-sm btn-secondary" onClick={() => {
              api.post('/notifications/read-all').then(() => { setNotifCount(0); loadNotifs(); });
            }}>Mark all read</button>
          </div>
          {notifications.map(n => (
            <div key={n.id} className={`notif-item ${!n.is_read ? 'unread' : ''}`}
              onClick={() => { markRead(n.id); if(n.link) navigate(n.link); setShowNotifs(false); }}>
              <div className="notif-title">{n.title}</div>
              <div className="notif-message">{n.message}</div>
              <div className="notif-time">{new Date(n.created_at).toLocaleString()}</div>
            </div>
          ))}
          {notifications.length === 0 && <div className="empty-state"><p>No notifications</p></div>}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const { user, loading } = useAuth();

  if (loading) return <div className="loading-page"><div className="spinner" /></div>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <Login />} />
      <Route path="/*" element={user ? <Layout /> : <Navigate to="/login" />} />
    </Routes>
  );
}
