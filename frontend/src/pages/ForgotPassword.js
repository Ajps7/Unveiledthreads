import { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { ArrowLeft, Mail, CheckCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await axios.post(`${API}/api/auth/forgot-password`, { email });
      setSubmitted(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') setError(detail);
      else setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center px-6">
        <div className="max-w-md w-full text-center">
          <CheckCircle className="w-16 h-16 text-[#39FF14] mx-auto mb-6" />
          <h1
            className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-4 text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="forgot-success-title"
          >
            CHECK YOUR INBOX
          </h1>
          <p className="text-[#9CA3AF] mb-8">
            If an account exists for <strong className="text-white">{email}</strong>, we've sent you a password reset link. It will expire in 1 hour.
          </p>
          <p className="text-xs text-[#9CA3AF] mb-8">
            Don't see it? Check your spam folder, or try requesting another link.
          </p>
          <Link to="/login">
            <Button className="btn-primary" data-testid="back-to-login-button">
              Back to Sign In
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-6">
      <div className="max-w-md w-full">
        <Link to="/login" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to Sign In
        </Link>

        <h1
          className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-2 text-white"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
          data-testid="forgot-page-title"
        >
          FORGOT PASSWORD
        </h1>
        <p className="text-[#9CA3AF] mb-8">
          Enter your email and we'll send you a link to reset your password.
        </p>

        {error && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/30 text-red-400 text-sm" data-testid="forgot-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className="block text-xs uppercase tracking-wider text-[#C0C0C0] mb-2">Email</label>
            <div className="relative">
              <Mail className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#9CA3AF]" />
              <Input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="pl-9 bg-[#0F0F0F] border-white/10 text-white"
                data-testid="forgot-email-input"
              />
            </div>
          </div>

          <Button
            type="submit"
            className="btn-primary w-full"
            disabled={loading}
            data-testid="forgot-submit-button"
          >
            {loading ? 'Sending...' : 'Send Reset Link'}
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
