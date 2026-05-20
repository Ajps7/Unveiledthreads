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

export default function Register() {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (password !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (password.length < 6) {
      setError('Password must be at least 6 characters');
      return;
    }

    setLoading(true);

    try {
      await register(email, password, name);
      navigate('/');
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] flex">
      {/* Left side - Image */}
      <div className="hidden lg:block lg:w-1/2 relative">
        <div className="absolute inset-0 bg-gradient-to-l from-[#050505] to-transparent z-10" />
        <img
          src="https://images.unsplash.com/photo-1615545362149-85299994b09b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NTY2NzF8MHwxfHNlYXJjaHwzfHxzdHJlZXR3ZWFyJTIwZmFzaGlvbiUyMG1vZGVsfGVufDB8fHx8MTc3NjExNDAyNnww&ixlib=rb-4.1.0&q=85"
          alt="Streetwear"
          className="w-full h-full object-cover"
        />
        <div className="absolute bottom-12 right-12 z-20 text-right">
          <p className="text-xs uppercase tracking-[0.2em] text-[#39FF14] mb-2">Join The Movement</p>
          <p className="text-2xl font-bold text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            WHERE NEW BRANDS<br />FIND THEIR AUDIENCE
          </p>
        </div>
      </div>

      {/* Right side - Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center px-8 md:px-16 lg:px-24">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-12 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to home
        </Link>

        <div className="max-w-md">
          <h1 className="text-4xl md:text-5xl font-black tracking-tighter uppercase mb-4 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            CREATE ACCOUNT
          </h1>
          <p className="text-[#9CA3AF] mb-8">
            Join Unveiled Threads and discover independent brands
          </p>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 mb-6" data-testid="register-error">
              <div>{error}</div>
              {typeof error === 'string' && error.toLowerCase().includes('already exists') && (
                <div className="mt-2 flex gap-3 text-xs">
                  <Link to="/login" className="text-[#39FF14] hover:underline uppercase tracking-wider" data-testid="error-login-link">
                    Sign in instead
                  </Link>
                  <Link to="/forgot-password" className="text-[#39FF14] hover:underline uppercase tracking-wider" data-testid="error-forgot-link">
                    Forgot password?
                  </Link>
                </div>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
                Full Name
              </label>
              <Input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-brutalist"
                placeholder="John Doe"
                required
                data-testid="register-name-input"
              />
            </div>

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
                data-testid="register-email-input"
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
                  data-testid="register-password-input"
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

            <div>
              <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
                Confirm Password
              </label>
              <Input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="input-brutalist"
                placeholder="••••••••"
                required
                data-testid="register-confirm-password-input"
              />
            </div>

            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                required
                className="accent-[#39FF14] mt-1"
                data-testid="terms-checkbox"
              />
              <span className="text-xs text-[#9CA3AF]">
                I agree to the <Link to="/terms" target="_blank" className="text-[#39FF14] hover:underline">Terms & Conditions</Link> of Unveiled Threads
              </span>
            </label>

            <Button
              type="submit"
              className="btn-primary w-full"
              disabled={loading}
              data-testid="register-submit-button"
            >
              {loading ? 'Creating account...' : 'Create Account'}
            </Button>
          </form>

          <p className="mt-8 text-[#9CA3AF] text-center">
            Already have an account?{' '}
            <Link to="/login" className="text-[#39FF14] hover:underline" data-testid="login-link">
              Sign in
            </Link>
          </p>

          <p className="mt-6 text-xs text-[#9CA3AF] text-center">
            Want to sell on Unveiled Threads?{' '}
            <Link to="/apply" className="text-[#C0C0C0] hover:text-white transition-colors">
              Apply as a brand
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
