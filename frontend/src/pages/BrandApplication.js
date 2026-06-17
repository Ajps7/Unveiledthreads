import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Button } from '../components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { ArrowLeft, CheckCircle, AlertCircle } from 'lucide-react';
import Header from '../components/Header';

const API = process.env.REACT_APP_BACKEND_URL;

const CATEGORIES = [
  { id: 'hoodies', name: 'Hoodies' },
  { id: 't-shirts', name: 'T-Shirts' },
  { id: 'jackets', name: 'Jackets & Coats' },
  { id: 'trousers', name: 'Trousers & Cargos' },
  { id: 'shorts', name: 'Shorts' },
  { id: 'accessories', name: 'Accessories' },
  { id: 'footwear', name: 'Footwear' },
  { id: 'caps', name: 'Caps & Hats' },
];

const UK_LOCATIONS = [
  'London',
  'Manchester',
  'Birmingham',
  'Leeds',
  'Liverpool',
  'Bristol',
  'Sheffield',
  'Newcastle',
  'Nottingham',
  'Glasgow',
  'Edinburgh',
  'Other UK'
];

export default function BrandApplication() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [applyResult, setApplyResult] = useState(null);
  const [formData, setFormData] = useState({
    brand_name: '',
    description: '',
    instagram_handle: '',
    website: '',
    location: '',
    category: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!user) {
      setError('Please login to apply');
      setLoading(false);
      return;
    }

    try {
      const res = await axios.post(`${API}/api/brands/apply`, formData, { withCredentials: true });
      setApplyResult(res.data);
      setSuccess(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail.map(e => e.msg).join(', '));
      } else {
        setError('Failed to submit application');
      }
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    const autoApproved = applyResult?.auto_approved;
    const waitlisted = applyResult?.waitlisted;
    let title = 'APPLICATION SUBMITTED';
    let message = "Thanks for applying to Unveiled Threads. Our team will review your application within 24 hours and email you when it's been approved.";
    let ctaText = 'Back to Home';
    let ctaTo = '/';
    if (autoApproved) {
      title = "YOU'RE APPROVED";
      message = "Your brand has been approved instantly. Check your inbox — we've emailed you a one-click link to finish your secure Stripe payout setup so you can start selling today.";
      ctaText = 'Go to Brand Dashboard';
      ctaTo = '/brand/dashboard';
    } else if (waitlisted) {
      title = "YOU'RE ON THE WAITLIST";
      message = "We're capping the platform at a small number of sellers during our MVP phase to make sure every brand gets proper attention. We've saved your application — we'll email you the moment a slot opens up.";
    }
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="max-w-2xl mx-auto px-6 py-24 text-center">
          <CheckCircle className="w-16 h-16 text-[#39FF14] mx-auto mb-6" />
          <h1 
            className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-4 text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="apply-success-title"
          >
            {title}
          </h1>
          <p className="text-[#9CA3AF] mb-8" data-testid="apply-success-message">
            {message}
          </p>
          <Link to={ctaTo}>
            <Button className="btn-primary" data-testid="back-to-home-button">
              {ctaText}
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-3xl mx-auto px-6 py-12">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" />
          Back to home
        </Link>

        <div className="mb-12">
          <h1 
            className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-4 text-white"
            style={{ fontFamily: 'Clash Display, sans-serif' }}
            data-testid="apply-page-title"
          >
            SELL ON UNVEILED THREADS
          </h1>
          <p className="text-[#9CA3AF]">
            We built this platform for you — the new brand owner with big ideas and fresh designs. 
            Fill out the application below and let us introduce you to the UK streetwear community.
          </p>
        </div>

        {!authLoading && !user && (
          <div className="bg-[#39FF14]/10 border border-[#39FF14]/30 p-6 mb-8 flex items-start gap-4">
            <AlertCircle className="w-5 h-5 text-[#39FF14] flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-[#39FF14] font-medium mb-2">Login Required</p>
              <p className="text-[#9CA3AF] text-sm mb-4">
                You need to create an account or login before applying as a brand.
              </p>
              <div className="flex gap-4">
                <Link to="/login">
                  <Button className="btn-secondary text-sm" data-testid="login-to-apply">Login</Button>
                </Link>
                <Link to="/register">
                  <Button className="btn-primary text-sm" data-testid="register-to-apply">Create Account</Button>
                </Link>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 mb-6" data-testid="application-error">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Brand Name */}
          <div>
            <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
              Brand Name *
            </label>
            <Input
              type="text"
              value={formData.brand_name}
              onChange={(e) => setFormData({ ...formData, brand_name: e.target.value })}
              className="input-brutalist"
              placeholder="Your brand name"
              required
              data-testid="brand-name-input"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
              Brand Description *
            </label>
            <Textarea
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="input-brutalist min-h-[120px] resize-none"
              placeholder="Tell us about your brand, your story, and what makes you unique..."
              required
              data-testid="brand-description-input"
            />
          </div>

          {/* Location */}
          <div>
            <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
              Location (UK) *
            </label>
            <Select 
              value={formData.location} 
              onValueChange={(value) => setFormData({ ...formData, location: value })}
              required
            >
              <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white" data-testid="location-select">
                <SelectValue placeholder="Select your location" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                {UK_LOCATIONS.map((loc) => (
                  <SelectItem key={loc} value={loc} className="text-white hover:bg-white/10 rounded-none">
                    {loc}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
              Primary Category *
            </label>
            <Select 
              value={formData.category} 
              onValueChange={(value) => setFormData({ ...formData, category: value })}
              required
            >
              <SelectTrigger className="w-full bg-transparent border-white/20 rounded-none text-white" data-testid="category-select">
                <SelectValue placeholder="Select primary category" />
              </SelectTrigger>
              <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
                {CATEGORIES.map((cat) => (
                  <SelectItem key={cat.id} value={cat.id} className="text-white hover:bg-white/10 rounded-none">
                    {cat.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="pt-4">
            <Button
              type="submit"
              className="btn-primary w-full"
              disabled={loading || authLoading || !user}
              data-testid="submit-application-button"
            >
              {loading ? 'Submitting...' : 'Submit Application'}
            </Button>
          </div>

          <p className="text-xs text-[#9CA3AF] text-center">
            By submitting, you agree that your brand is UK-based, sells authentic streetwear products, and you accept our <Link to="/terms" target="_blank" className="text-[#39FF14] hover:underline">Terms & Conditions</Link>.
          </p>
        </form>
      </div>
    </div>
  );
}
