import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import { Package, Clock, CheckCircle, ArrowLeft } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

export default function MyOrders() {
  const { user, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading || !user) return;
    fetchOrders();
  }, [user, authLoading]);

  const fetchOrders = async () => {
    try {
      const response = await axios.get(`${API}/api/orders/my-orders`, { withCredentials: true });
      setOrders(response.data);
    } catch (error) {
      console.error('Error fetching orders:', error);
    } finally {
      setLoading(false);
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
          <p className="text-[#9CA3AF] mb-4">Please login to view your orders</p>
          <Link to="/login"><Button className="btn-primary">Login</Button></Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-4xl mx-auto px-6 md:px-12 py-8">
        <Link to="/products" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to products
        </Link>

        <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase mb-8 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="my-orders-title">
          MY ORDERS
        </h1>

        {orders.length === 0 ? (
          <div className="border border-white/10 bg-[#0A0A0A] p-12 text-center">
            <Package className="w-12 h-12 text-[#9CA3AF] mx-auto mb-4" />
            <p className="text-[#9CA3AF] mb-4">No orders yet</p>
            <Link to="/products"><Button className="btn-primary">Shop Now</Button></Link>
          </div>
        ) : (
          <div className="space-y-4" data-testid="orders-list">
            {orders.map((order) => (
              <div key={order.id} className="border border-white/10 bg-[#0A0A0A] p-4 flex flex-col md:flex-row md:items-center gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-white font-bold">{order.product_name}</h3>
                    <span className={`text-xs uppercase tracking-wider px-2 py-0.5 ${
                      order.status === 'paid' ? 'bg-green-500/10 text-green-400 border border-green-500/30' :
                      order.status === 'initiated' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30' :
                      'bg-[#9CA3AF]/10 text-[#9CA3AF] border border-[#9CA3AF]/30'
                    }`}>
                      {order.status === 'paid' ? 'Confirmed' : order.status}
                    </span>
                  </div>
                  <p className="text-sm text-[#9CA3AF]">
                    {order.brand_name} · Size: {order.size} · {new Date(order.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-white font-bold">£{order.total_charged?.toFixed(2) || order.price?.toFixed(2)}</p>
                  <p className="text-xs text-[#9CA3AF]">incl. platform fee</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
