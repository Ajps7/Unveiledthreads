import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Eye, EyeOff, ArrowLeft } from 'lucide-react';

function formatApiErrorDetail(detail) {
  if (detail == null) return "Something went wrong. Please try again.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail))
    return detail.map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e))).filter(Boolean).join(" ");
  if (detail && typeof detail.msg === "string") return detail.msg;
  return String(detail);
}

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await login(email, password);
      navigate('/');
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex">
      {/* Left side - Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center px-8 md:px-16 lg:px-24">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-12 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to home
        </Link>

        <div className="max-w-md">
          <h1 className="text-4xl md:text-5xl font-black tracking-tighter uppercase mb-4 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            WELCOME BACK
          </h1>
          <p className="text-[#9CA3AF] mb-8">
            Sign in to your account to continue
          </p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 mb-6" data-testid="login-error">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
                Email
              </label>
              <Input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-brutalist"
                placeholder="your@email.com"
                required
                data-testid="login-email-input"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
                Password
              </label>
              <div className="relative">
                <Input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-brutalist pr-12"
                  placeholder="••••••••"
                  required
                  data-testid="login-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              className="btn-primary w-full"
              disabled={loading}
              data-testid="login-submit-button"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </form>

          <p className="mt-8 text-[#9CA3AF] text-center">
            Don't have an account?{' '}
            <Link to="/register" className="text-[#39FF14] hover:underline" data-testid="register-link">
              Create one
            </Link>
          </p>
        </div>
      </div>

      {/* Right side - Image */}
      <div className="hidden lg:block lg:w-1/2 relative">
        <div className="absolute inset-0 bg-gradient-to-r from-[#050505] to-transparent z-10" />
        <img
          src="https://images.pexels.com/photos/5319298/pexels-photo-5319298.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940"
          alt="Streetwear"
          className="w-full h-full object-cover"
        />
        <div className="absolute bottom-12 left-12 z-20">
          <p className="text-xs uppercase tracking-[0.2em] text-[#39FF14] mb-2">Unveiled Threads</p>
          <p className="text-2xl font-bold text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            INDEPENDENT BRANDS.<br />AUTHENTIC CULTURE.
          </p>
        </div>
      </div>
    </div>
  );
}
