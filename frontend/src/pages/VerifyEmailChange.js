import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle2, XCircle, Loader2, ArrowRight } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Landing page for the emailed verification link.
 * URL: /verify-email-change?token=…
 * Consumes the token once and either confirms the change or shows a
 * clean error state.
 */
export default function VerifyEmailChange() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [status, setStatus] = useState('loading'); // loading | ok | error
  const [message, setMessage] = useState('');

  useEffect(() => {
    document.title = 'Confirm email · Unveiled Threads';
    const token = params.get('token');
    if (!token) {
      setStatus('error');
      setMessage('Missing verification token in the link.');
      return;
    }
    (async () => {
      try {
        const r = await axios.post(
          `${API}/api/auth/change-email/confirm`,
          { token },
          { withCredentials: true }
        );
        setStatus('ok');
        setMessage(r.data?.message || 'Email updated. Please sign in with your new email.');
      } catch (err) {
        setStatus('error');
        const detail = err.response?.data?.detail;
        setMessage(typeof detail === 'string' ? detail : 'This link is invalid or has expired.');
      }
    })();
  }, [params]);

  return (
    <div className="min-h-screen bg-[#050505] flex items-center justify-center px-6" data-testid="verify-email-change-page">
      <div className="max-w-md w-full border border-white/10 bg-[#0F0F0F] p-8">
        <h1 className="text-2xl font-black uppercase tracking-tighter text-white mb-3"
            style={{ fontFamily: 'Clash Display, sans-serif' }}>
          Confirm email change
        </h1>
        {status === 'loading' && (
          <div className="flex items-center gap-3 text-[#9CA3AF]" data-testid="verify-loading">
            <Loader2 className="w-5 h-5 animate-spin text-[#39FF14]" />
            Verifying your link…
          </div>
        )}
        {status === 'ok' && (
          <div data-testid="verify-ok">
            <div className="flex items-start gap-3 text-[#39FF14] mb-4">
              <CheckCircle2 className="w-6 h-6 flex-shrink-0" />
              <p className="text-white/90 leading-relaxed">{message}</p>
            </div>
            <button
              onClick={() => navigate('/login')}
              className="bg-[#39FF14] text-black hover:bg-[#39FF14]/90 rounded-none font-bold uppercase tracking-wider text-sm px-5 py-2.5 inline-flex items-center gap-2"
              data-testid="verify-goto-login"
            >
              Sign in <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
        {status === 'error' && (
          <div data-testid="verify-error">
            <div className="flex items-start gap-3 text-red-400 mb-4">
              <XCircle className="w-6 h-6 flex-shrink-0" />
              <p className="text-white/90 leading-relaxed">{message}</p>
            </div>
            <Link
              to="/account"
              className="border border-white/20 text-white hover:border-[#39FF14] hover:text-[#39FF14] rounded-none font-bold uppercase tracking-wider text-sm px-5 py-2.5 inline-flex items-center gap-2"
              data-testid="verify-goto-account"
            >
              Back to account <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
