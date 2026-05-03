import { Link } from 'react-router-dom';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import { Gift, ArrowLeft } from 'lucide-react';

export default function Referrals() {
  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-2xl mx-auto px-6 md:px-12 py-24 text-center">
        <Gift className="w-16 h-16 text-[#39FF14] mx-auto mb-6" />
        <h1
          className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-4 text-white"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
          data-testid="referrals-title"
        >
          REFER & EARN
        </h1>
        <div className="inline-block bg-[#39FF14]/10 border border-[#39FF14]/30 px-6 py-2 mb-6">
          <span className="text-[#39FF14] text-sm font-bold uppercase tracking-wider">Coming Soon</span>
        </div>
        <p className="text-[#9CA3AF] mb-10 max-w-md mx-auto">
          We're building a referral programme that rewards you for sharing Unveiled Threads with your mates. Stay tuned.
        </p>
        <Link to="/">
          <Button className="btn-secondary">
            <ArrowLeft className="w-4 h-4 mr-2" /> Back to Home
          </Button>
        </Link>
      </div>
    </div>
  );
}
