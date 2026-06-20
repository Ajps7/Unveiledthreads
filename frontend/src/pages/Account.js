import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import Header from '../components/Header';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import axios from 'axios';
import { ArrowLeft, Download, Trash2, ShieldAlert, Mail, User as UserIcon } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Account() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [exporting, setExporting] = useState(false);
  const [showDelete, setShowDelete] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmText, setConfirmText] = useState('');
  const [deleting, setDeleting] = useState(false);

  if (!user) {
    navigate('/login');
    return null;
  }

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await axios.get(`${API}/api/account/export`, {
        withCredentials: true,
        responseType: 'blob',
      });
      const blob = new Blob([res.data], { type: 'application/json' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `unveiled-threads-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success('Your data export has been downloaded.');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to export data. Try again later.');
    } finally {
      setExporting(false);
    }
  };

  const handleDelete = async () => {
    if (confirmText !== 'DELETE') {
      toast.error("You must type DELETE (in caps) to confirm.");
      return;
    }
    if (!password) {
      toast.error('Enter your password to confirm deletion.');
      return;
    }
    setDeleting(true);
    try {
      await axios.post(
        `${API}/api/account/delete`,
        { password, confirm: confirmText },
        { withCredentials: true }
      );
      toast.success('Your account has been permanently deleted.');
      // Force a full reload to the home page so the AuthContext re-checks and the user is logged out
      setTimeout(() => { window.location.href = '/'; }, 1200);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Could not delete account.');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505]" data-testid="account-page">
      <Header />
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-12">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to home
        </Link>

        <h1
          className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-2 text-white"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
          data-testid="account-title"
        >
          ACCOUNT &amp; PRIVACY
        </h1>
        <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-10">
          Manage your data — UK GDPR rights
        </p>

        {/* Account info */}
        <div className="border border-white/10 bg-[#0F0F0F] p-6 mb-8">
          <div className="flex items-center gap-3 mb-4">
            <UserIcon className="w-5 h-5 text-[#39FF14]" />
            <h2 className="text-lg font-bold text-white uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Your account
            </h2>
          </div>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between border-b border-white/5 pb-2">
              <dt className="text-[#9CA3AF]">Name</dt>
              <dd className="text-white" data-testid="account-name">{user.name}</dd>
            </div>
            <div className="flex justify-between border-b border-white/5 pb-2">
              <dt className="text-[#9CA3AF]">Email</dt>
              <dd className="text-white" data-testid="account-email">{user.email}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[#9CA3AF]">Role</dt>
              <dd className="text-[#39FF14] uppercase tracking-wider text-xs" data-testid="account-role">{user.role}</dd>
            </div>
          </dl>
        </div>

        {/* Export */}
        <div className="border border-white/10 bg-[#0F0F0F] p-6 mb-8">
          <div className="flex items-center gap-3 mb-3">
            <Download className="w-5 h-5 text-[#39FF14]" />
            <h2 className="text-lg font-bold text-white uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Export your data
            </h2>
          </div>
          <p className="text-sm text-[#C0C0C0] leading-relaxed mb-4">
            Download a JSON file containing every record we hold about you — orders, messages, listings,
            wishlist, and more. This satisfies your{' '}
            <span className="text-white">right to data portability (UK GDPR Article 20)</span>.
          </p>
          <p className="text-xs text-[#9CA3AF] mb-4">
            Note: payment / KYC data is held by Stripe, not us — request that copy from your Stripe dashboard.
          </p>
          <Button
            onClick={handleExport}
            disabled={exporting}
            className="bg-[#39FF14] text-black hover:bg-[#39FF14]/90 rounded-none font-bold uppercase tracking-wider text-sm"
            data-testid="export-data-button"
          >
            <Download className="w-4 h-4 mr-2" />
            {exporting ? 'Preparing…' : 'Download my data'}
          </Button>
        </div>

        {/* Other rights */}
        <div className="border border-white/10 bg-[#0F0F0F] p-6 mb-8">
          <div className="flex items-center gap-3 mb-3">
            <Mail className="w-5 h-5 text-[#39FF14]" />
            <h2 className="text-lg font-bold text-white uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Other GDPR requests
            </h2>
          </div>
          <p className="text-sm text-[#C0C0C0] leading-relaxed mb-3">
            For corrections, objections, restricted processing or any other privacy request, email us at{' '}
            <a href="mailto:privacy@unveiledthreads.co.uk" className="text-[#39FF14] hover:underline">
              privacy@unveiledthreads.co.uk
            </a>. We respond within 30 days.
          </p>
          <Link to="/privacy" className="text-xs text-[#39FF14] hover:underline uppercase tracking-wider" data-testid="account-privacy-link">
            Read our full Privacy Policy →
          </Link>
          <p className="text-[10px] text-[#6B7280] mt-4 pt-3 border-t border-white/5" data-testid="account-ico-reg">
            Unveiled Threads is registered with the UK ICO · Reg No. <span className="text-[#9CA3AF]">ZC176765</span>
          </p>
        </div>

        {/* Danger zone */}
        <div className="border border-red-500/40 bg-red-500/5 p-6 mb-8" data-testid="delete-zone">
          <div className="flex items-center gap-3 mb-3">
            <ShieldAlert className="w-5 h-5 text-red-400" />
            <h2 className="text-lg font-bold text-red-200 uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Delete account
            </h2>
          </div>
          <p className="text-sm text-red-100/80 leading-relaxed mb-2">
            Permanently delete your account and all personal data we hold about you. This is your{' '}
            <span className="text-white">right to erasure (UK GDPR Article 17)</span>.
          </p>
          <ul className="text-xs text-red-100/70 list-disc list-inside mb-4 space-y-1">
            <li>This cannot be undone.</li>
            <li>Your listings, messages, posts, wishlist and notifications will be wiped.</li>
            <li>Past orders are kept but anonymised (we're legally required to hold tax records for 6 years).</li>
            <li>If you sell on the platform, contact Stripe separately to close your connected account.</li>
          </ul>

          {!showDelete ? (
            <Button
              variant="outline"
              onClick={() => setShowDelete(true)}
              className="border-red-500/50 text-red-300 hover:bg-red-500/10 hover:text-red-200 rounded-none font-bold uppercase tracking-wider text-sm"
              data-testid="show-delete-button"
            >
              <Trash2 className="w-4 h-4 mr-2" />
              I want to delete my account
            </Button>
          ) : (
            <div className="space-y-4 mt-4 border-t border-red-500/30 pt-4" data-testid="delete-confirm-form">
              <div>
                <Label htmlFor="del-password" className="text-xs uppercase tracking-wider text-red-200 mb-2 block">
                  Confirm your password
                </Label>
                <Input
                  id="del-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="bg-black border-red-500/30 text-white rounded-none focus:border-red-500"
                  data-testid="delete-password-input"
                />
              </div>
              <div>
                <Label htmlFor="del-confirm" className="text-xs uppercase tracking-wider text-red-200 mb-2 block">
                  Type <span className="text-white font-mono">DELETE</span> to confirm
                </Label>
                <Input
                  id="del-confirm"
                  type="text"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  placeholder="DELETE"
                  className="bg-black border-red-500/30 text-white rounded-none focus:border-red-500 font-mono"
                  data-testid="delete-confirm-input"
                />
              </div>
              <div className="flex gap-3">
                <Button
                  onClick={handleDelete}
                  disabled={deleting || confirmText !== 'DELETE' || !password}
                  className="bg-red-500 text-white hover:bg-red-600 rounded-none font-bold uppercase tracking-wider text-sm disabled:opacity-40"
                  data-testid="confirm-delete-button"
                >
                  <Trash2 className="w-4 h-4 mr-2" />
                  {deleting ? 'Deleting…' : 'Permanently delete'}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => { setShowDelete(false); setPassword(''); setConfirmText(''); }}
                  className="text-[#C0C0C0] hover:text-white hover:bg-white/5 rounded-none uppercase tracking-wider text-sm"
                  data-testid="cancel-delete-button"
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
