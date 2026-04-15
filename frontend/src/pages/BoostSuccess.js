import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import { CheckCircle, Loader2, XCircle } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function BoostSuccess() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [status, setStatus] = useState('checking');
  const [attempts, setAttempts] = useState(0);

  useEffect(() => {
    const sessionId = searchParams.get('session_id');
    if (!sessionId) {
      setStatus('error');
      return;
    }

    pollPaymentStatus(sessionId);
  }, [searchParams]);

  const pollPaymentStatus = async (sessionId, attemptNum = 0) => {
    const maxAttempts = 5;
    const pollInterval = 2000;

    if (attemptNum >= maxAttempts) {
      setStatus('timeout');
      return;
    }

    setAttempts(attemptNum + 1);

    try {
      const response = await axios.get(`${API}/api/boost/status/${sessionId}`, { withCredentials: true });
      
      if (response.data.payment_status === 'paid') {
        setStatus('success');
        return;
      } else if (response.data.status === 'expired') {
        setStatus('expired');
        return;
      }

      // Continue polling
      setTimeout(() => pollPaymentStatus(sessionId, attemptNum + 1), pollInterval);
    } catch (error) {
      console.error('Error checking payment status:', error);
      setStatus('error');
    }
  };

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-2xl mx-auto px-6 py-24 text-center">
        {status === 'checking' && (
          <>
            <Loader2 className="w-16 h-16 text-[#39FF14] animate-spin mx-auto mb-6" />
            <h1 
              className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
            >
              PROCESSING PAYMENT
            </h1>
            <p className="text-[#9CA3AF]">
              Please wait while we confirm your payment... (Attempt {attempts}/5)
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="w-16 h-16 text-[#39FF14] mx-auto mb-6" />
            <h1 
              className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
              data-testid="boost-success-title"
            >
              BOOST ACTIVATED!
            </h1>
            <p className="text-[#9CA3AF] mb-8">
              Your brand is now boosted and will appear in the featured section. 
              Get ready for increased visibility!
            </p>
            <Button 
              className="btn-primary" 
              onClick={() => navigate('/brand/dashboard')}
              data-testid="back-to-dashboard-button"
            >
              Back to Dashboard
            </Button>
          </>
        )}

        {status === 'expired' && (
          <>
            <XCircle className="w-16 h-16 text-red-400 mx-auto mb-6" />
            <h1 
              className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
            >
              SESSION EXPIRED
            </h1>
            <p className="text-[#9CA3AF] mb-8">
              Your payment session has expired. Please try again.
            </p>
            <Button 
              className="btn-primary" 
              onClick={() => navigate('/brand/dashboard')}
            >
              Back to Dashboard
            </Button>
          </>
        )}

        {status === 'timeout' && (
          <>
            <Loader2 className="w-16 h-16 text-yellow-400 mx-auto mb-6" />
            <h1 
              className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
            >
              STILL PROCESSING
            </h1>
            <p className="text-[#9CA3AF] mb-8">
              Payment is still being processed. Please check your dashboard in a few minutes.
            </p>
            <Button 
              className="btn-primary" 
              onClick={() => navigate('/brand/dashboard')}
            >
              Back to Dashboard
            </Button>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="w-16 h-16 text-red-400 mx-auto mb-6" />
            <h1 
              className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-4 text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
            >
              SOMETHING WENT WRONG
            </h1>
            <p className="text-[#9CA3AF] mb-8">
              There was an error processing your payment. Please contact support if the issue persists.
            </p>
            <Button 
              className="btn-primary" 
              onClick={() => navigate('/brand/dashboard')}
            >
              Back to Dashboard
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
