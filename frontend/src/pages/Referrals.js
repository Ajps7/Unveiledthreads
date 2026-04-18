import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import Header from '../components/Header';
import { Share2, Copy, CheckCircle, Gift, Users, PoundSterling } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Referrals() {
  const { user, loading: authLoading } = useAuth();
  const [shareLinks, setShareLinks] = useState(null);
  const [credits, setCredits] = useState(null);
  const [codeInput, setCodeInput] = useState('');
  const [applying, setApplying] = useState(false);
  const [applyResult, setApplyResult] = useState('');
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchData();
  }, [user, authLoading]);

  const fetchData = async () => {
    try {
      const [linksRes, creditsRes] = await Promise.all([
        axios.get(`${API}/api/referral/share-links`, { withCredentials: true }),
        axios.get(`${API}/api/referral/credits`, { withCredentials: true })
      ]);
      setShareLinks(linksRes.data);
      setCredits(creditsRes.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCopyLink = () => {
    if (shareLinks?.link) {
      navigator.clipboard.writeText(shareLinks.link);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleApplyCode = async (e) => {
    e.preventDefault();
    if (!codeInput.trim()) return;
    setApplying(true);
    setApplyResult('');
    try {
      const res = await axios.post(`${API}/api/referral/apply`, { code: codeInput.trim() }, { withCredentials: true });
      setApplyResult(res.data.message);
      setCodeInput('');
    } catch (err) {
      setApplyResult(err.response?.data?.detail || 'Failed to apply code');
    } finally {
      setApplying(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <div className="animate-spin w-8 h-8 border-2 border-[#39FF14] border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="text-center py-24">
          <p className="text-[#9CA3AF] mb-4">Please login to access referrals</p>
          <Link to="/login"><Button className="btn-primary">Login</Button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-12">
        <div className="flex items-center gap-3 mb-8">
          <Gift className="w-7 h-7 text-[#39FF14]" />
          <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="referrals-title">
            REFER & EARN
          </h1>
        </div>

        <p className="text-[#9CA3AF] mb-10 max-w-xl">
          Share Unveiled Threads with your mates. When someone uses your referral code and makes their first purchase, you earn £5 credit towards your next order.
        </p>

        {/* Credits */}
        {credits && (
          <div className="grid grid-cols-3 gap-4 mb-10">
            <div className="border border-white/10 p-5 bg-[#0A0A0A] text-center">
              <PoundSterling className="w-5 h-5 text-[#39FF14] mx-auto mb-2" />
              <p className="text-2xl font-bold text-white">£{credits.credits_available.toFixed(2)}</p>
              <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mt-1">Available</p>
            </div>
            <div className="border border-white/10 p-5 bg-[#0A0A0A] text-center">
              <Users className="w-5 h-5 text-[#C0C0C0] mx-auto mb-2" />
              <p className="text-2xl font-bold text-white">{credits.referred_count}</p>
              <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mt-1">Referred</p>
            </div>
            <div className="border border-white/10 p-5 bg-[#0A0A0A] text-center">
              <Gift className="w-5 h-5 text-[#C0C0C0] mx-auto mb-2" />
              <p className="text-2xl font-bold text-white">£{credits.credits_earned.toFixed(2)}</p>
              <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mt-1">Total Earned</p>
            </div>
          </div>
        )}

        {/* Share Section */}
        {shareLinks && (
          <div className="border border-[#39FF14]/30 bg-[#39FF14]/5 p-6 mb-10">
            <h3 className="text-lg font-bold text-white mb-4 uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Your Referral Code
            </h3>
            <div className="flex items-center gap-3 mb-6">
              <div className="flex-1 bg-[#0A0A0A] border border-white/10 px-4 py-3 font-mono text-[#39FF14] text-lg tracking-wider" data-testid="referral-code">
                {shareLinks.code}
              </div>
              <Button className="btn-primary px-4" onClick={handleCopyLink} data-testid="copy-link-button">
                {copied ? <CheckCircle className="w-5 h-5" /> : <Copy className="w-5 h-5" />}
              </Button>
            </div>

            <div className="flex flex-wrap gap-3">
              <a href={shareLinks.twitter} target="_blank" rel="noopener noreferrer">
                <Button className="btn-secondary text-sm" data-testid="share-twitter">
                  <Share2 className="w-4 h-4 mr-2" /> Share on X
                </Button>
              </a>
              <a href={shareLinks.whatsapp} target="_blank" rel="noopener noreferrer">
                <Button className="btn-secondary text-sm" data-testid="share-whatsapp">
                  <Share2 className="w-4 h-4 mr-2" /> WhatsApp
                </Button>
              </a>
              <Button className="btn-secondary text-sm" onClick={handleCopyLink} data-testid="copy-link-button-2">
                <Copy className="w-4 h-4 mr-2" /> {copied ? 'Copied!' : 'Copy Link'}
              </Button>
            </div>
          </div>
        )}

        {/* Apply Code */}
        <div className="border border-white/10 bg-[#0A0A0A] p-6">
          <h3 className="text-lg font-bold text-white mb-4 uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            Have a Referral Code?
          </h3>
          <form onSubmit={handleApplyCode} className="flex gap-3">
            <Input
              value={codeInput}
              onChange={(e) => setCodeInput(e.target.value)}
              className="input-brutalist flex-1"
              placeholder="Enter referral code"
              data-testid="referral-code-input"
            />
            <Button type="submit" className="btn-primary" disabled={applying} data-testid="apply-code-button">
              {applying ? 'Applying...' : 'Apply'}
            </Button>
          </form>
          {applyResult && (
            <p className={`mt-3 text-sm ${applyResult.includes('£') ? 'text-[#39FF14]' : 'text-red-400'}`} data-testid="apply-result">
              {applyResult}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
