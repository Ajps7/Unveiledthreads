import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import Header from '../components/Header';
import { BarChart3, Eye, ShoppingCart, PoundSterling, TrendingUp, ArrowLeft, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function MiniBarChart({ data, dataKey, color = '#39FF14', height = 120 }) {
  if (!data || data.length === 0) return <p className="text-[#9CA3AF] text-sm">No data yet</p>;

  const maxVal = Math.max(...data.map(d => d[dataKey]), 1);

  return (
    <div className="flex items-end gap-1" style={{ height }}>
      {data.map((item, i) => {
        const barH = (item[dataKey] / maxVal) * height;
        return (
          <div key={i} className="flex-1 flex flex-col items-center group relative">
            <div
              className="w-full min-w-[4px] transition-all hover:opacity-80"
              style={{ height: Math.max(barH, 2), backgroundColor: color }}
            />
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-[#0F0F0F] border border-white/10 px-2 py-1 text-xs text-white opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
              {item.date?.slice(5)}: {item[dataKey]}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function BrandAnalytics() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('30');

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate('/login'); return; }
    if (user.role !== 'brand' && user.role !== 'admin') { navigate('/'); return; }
    fetchAnalytics();
  }, [user, authLoading, period, navigate]);

  const fetchAnalytics = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/api/analytics/brand?days=${period}`, { withCredentials: true });
      setAnalytics(response.data);
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <Loader2 className="w-8 h-8 text-[#39FF14] animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-7xl mx-auto px-6 md:px-12 py-8">
        <Link to="/brand/dashboard" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to dashboard
        </Link>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div className="flex items-center gap-3">
            <BarChart3 className="w-7 h-7 text-[#39FF14]" />
            <h1
              className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
              data-testid="analytics-title"
            >
              Brand Analytics
            </h1>
          </div>

          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-[160px] bg-transparent border-white/20 rounded-none text-white" data-testid="period-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
              <SelectItem value="7" className="text-white hover:bg-white/10 rounded-none">Last 7 days</SelectItem>
              <SelectItem value="30" className="text-white hover:bg-white/10 rounded-none">Last 30 days</SelectItem>
              <SelectItem value="90" className="text-white hover:bg-white/10 rounded-none">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {analytics && (
          <>
            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <div className="flex items-center gap-2 mb-3">
                  <Eye className="w-5 h-5 text-[#39FF14]" />
                  <p className="text-xs text-[#9CA3AF] uppercase tracking-wider">Views</p>
                </div>
                <p className="text-3xl font-bold text-white" data-testid="metric-views">{analytics.total_views}</p>
              </div>
              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <div className="flex items-center gap-2 mb-3">
                  <ShoppingCart className="w-5 h-5 text-[#39FF14]" />
                  <p className="text-xs text-[#9CA3AF] uppercase tracking-wider">Orders</p>
                </div>
                <p className="text-3xl font-bold text-white" data-testid="metric-orders">{analytics.total_orders}</p>
              </div>
              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <div className="flex items-center gap-2 mb-3">
                  <PoundSterling className="w-5 h-5 text-[#39FF14]" />
                  <p className="text-xs text-[#9CA3AF] uppercase tracking-wider">Revenue</p>
                </div>
                <p className="text-3xl font-bold text-white" data-testid="metric-revenue">£{analytics.total_revenue.toFixed(2)}</p>
              </div>
              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="w-5 h-5 text-[#39FF14]" />
                  <p className="text-xs text-[#9CA3AF] uppercase tracking-wider">Conversion</p>
                </div>
                <p className="text-3xl font-bold text-white" data-testid="metric-conversion">{analytics.conversion_rate}%</p>
              </div>
            </div>

            {/* Charts */}
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <h3 className="text-sm uppercase tracking-wider text-[#C0C0C0] mb-4">Views Over Time</h3>
                <MiniBarChart data={analytics.daily_views} dataKey="views" color="#39FF14" />
                {analytics.daily_views.length > 0 && (
                  <div className="flex justify-between mt-2 text-[10px] text-[#9CA3AF]">
                    <span>{analytics.daily_views[0]?.date?.slice(5)}</span>
                    <span>{analytics.daily_views[analytics.daily_views.length - 1]?.date?.slice(5)}</span>
                  </div>
                )}
              </div>
              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <h3 className="text-sm uppercase tracking-wider text-[#C0C0C0] mb-4">Revenue Over Time</h3>
                <MiniBarChart data={analytics.daily_revenue} dataKey="revenue" color="#C0C0C0" />
                {analytics.daily_revenue.length > 0 && (
                  <div className="flex justify-between mt-2 text-[10px] text-[#9CA3AF]">
                    <span>{analytics.daily_revenue[0]?.date?.slice(5)}</span>
                    <span>{analytics.daily_revenue[analytics.daily_revenue.length - 1]?.date?.slice(5)}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Top Products */}
            <div className="grid md:grid-cols-2 gap-6">
              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <h3 className="text-sm uppercase tracking-wider text-[#C0C0C0] mb-4">Top Selling Products</h3>
                {analytics.top_products.length > 0 ? (
                  <div className="space-y-3">
                    {analytics.top_products.map((p, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                        <div>
                          <span className="text-[#39FF14] text-xs mr-2">#{i + 1}</span>
                          <span className="text-white text-sm">{p.name}</span>
                        </div>
                        <div className="text-right">
                          <p className="text-white font-bold text-sm">£{p.revenue.toFixed(2)}</p>
                          <p className="text-[#9CA3AF] text-xs">{p.orders} orders</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#9CA3AF] text-sm">No sales yet</p>
                )}
              </div>

              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <h3 className="text-sm uppercase tracking-wider text-[#C0C0C0] mb-4">Most Viewed Products</h3>
                {analytics.top_viewed.length > 0 ? (
                  <div className="space-y-3">
                    {analytics.top_viewed.map((p, i) => (
                      <div key={i} className="flex items-center justify-between py-2 border-b border-white/5 last:border-0">
                        <div>
                          <span className="text-[#C0C0C0] text-xs mr-2">#{i + 1}</span>
                          <span className="text-white text-sm">{p.name}</span>
                        </div>
                        <div className="flex items-center gap-1 text-[#9CA3AF] text-sm">
                          <Eye className="w-3 h-3" />
                          {p.views}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-[#9CA3AF] text-sm">No views yet</p>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
