import { useState, useEffect } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Eye, EyeOff, Lock, CheckCircle, AlertTriangle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') || '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) setError('No reset token in URL. Please use the link from your email.');
  }, [token]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    try {
      await axios.post(`${API}/api/auth/reset-password`, { token, new_password: password });
      setDone(true);
      setTimeout(() => navigate('/login'), 3000);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') setError(detail);
      else setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center px-6">
        <div className="max-w-md w-full text-center">
          <CheckCircle className="w-16 h-16 text-[#39FF14] mx-auto mb-6" />
          <h1
            className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-4 text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="reset-success-title"
          >
            PASSWORD UPDATED
          </h1>
          <p className="text-[#9CA3AF] mb-8">
            You can now sign in with your new password. Taking you there now...
          </p>
          <Link to="/login">
            <Button className="btn-primary" data-testid="go-to-login-button">
              Sign In
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-6">
      <div className="max-w-md w-full">
        <h1
          className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-2 text-white"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
          data-testid="reset-page-title"
        >
          NEW PASSWORD
        </h1>
        <p className="text-[#9CA3AF] mb-8">
          Choose a strong password — at least 8 characters. Avoid anything you use elsewhere.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm flex items-start gap-2" data-testid="reset-error">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">New password</label>
            <div className="relative">
              <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
              <Input
                type={showPw ? 'text' : 'password'}
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="pl-9 pr-9 bg-[#0F0F0F] border-white/10 text-white"
                data-testid="reset-new-password-input"
              />
              <button
                type="button"
                onClick={() => setShowPw(!showPw)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-white"
              >
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">Confirm password</label>
            <div className="relative">
              <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
              <Input
                type={showPw ? 'text' : 'password'}
                required
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••"
                className="pl-9 bg-[#0F0F0F] border-white/10 text-white"
                data-testid="reset-confirm-password-input"
              />
            </div>
          </div>

          <Button
            type="submit"
            className="btn-primary w-full"
            disabled={loading || !token}
            data-testid="reset-submit-button"
          >
            {loading ? 'Updating...' : 'Set New Password'}
          </Button>
        </form>

        <p className="mt-8 text-[#9CA3AF] text-center text-sm">
          Remembered it?{' '}
          <Link to="/login" className="text-[#39FF14] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
