import { useState } from 'react';
import { useAuth } from '../AuthContext';

const DEMO_ACCOUNTS = {
  planner: { email: 'planner@panama-canal.com', password: 'planner123' },
  coordinator: { email: 'coordinator@panama-canal.com', password: 'coordinator123' },
  customer: { email: 'customer1@oceanline.com', password: 'customer123' },
};

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [selectedRole, setSelectedRole] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRoleSelect = (role) => {
    setSelectedRole(role);
    setEmail(DEMO_ACCOUNTS[role].email);
    setPassword(DEMO_ACCOUNTS[role].password);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await login(email, password);
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    }
    setLoading(false);
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">P</div>
          <h1>Panama Canal</h1>
          <p>Enhanced Booking System</p>
        </div>

        <div className="role-selector">
          {['planner', 'coordinator', 'customer'].map(role => (
            <button key={role} className={`role-btn ${selectedRole === role ? 'active' : ''}`}
              onClick={() => handleRoleSelect(role)}>
              {role === 'planner' ? '📋' : role === 'coordinator' ? '🎯' : '🚢'}<br/>
              {role.charAt(0).toUpperCase() + role.slice(1)}
            </button>
          ))}
        </div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input className="form-input" type="email" value={email}
              onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input className="form-input" type="password" value={password}
              onChange={e => setPassword(e.target.value)} required />
          </div>
          <button className="login-btn" type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
