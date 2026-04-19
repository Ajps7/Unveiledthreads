import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import { Bell, CheckCircle, ShoppingCart, Star, Truck, MessageSquare, Shield, ArrowLeft } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const ICON_MAP = {
  application_approved: Shield,
  application_rejected: Shield,
  order_received: ShoppingCart,
  order_shipped: Truck,
  shipping_update: Truck,
  new_review: Star,
  new_message: MessageSquare,
};

function NotificationItem({ notification, onMarkRead }) {
  const Icon = ICON_MAP[notification.type] || Bell;
  const isUnread = !notification.read;

  return (
    <div
      className={`p-4 border-b border-white/5 flex gap-4 items-start transition-colors ${isUnread ? 'bg-[#39FF14]/5' : ''}`}
      data-testid={`notification-${notification.id}`}
    >
      <div className={`w-10 h-10 flex items-center justify-center flex-shrink-0 ${isUnread ? 'text-[#39FF14]' : 'text-[#9CA3AF]'}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-medium ${isUnread ? 'text-white' : 'text-[#C0C0C0]'}`}>{notification.title}</p>
        <p className="text-xs text-[#9CA3AF] mt-1 line-clamp-2">{notification.message}</p>
        <p className="text-[10px] text-[#9CA3AF] mt-2">
          {new Date(notification.created_at).toLocaleString()}
        </p>
      </div>
      {isUnread && (
        <button
          onClick={() => onMarkRead(notification.id)}
          className="text-[#9CA3AF] hover:text-[#39FF14] transition-colors p-1 flex-shrink-0"
          data-testid={`mark-read-${notification.id}`}
        >
          <CheckCircle className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

export default function Notifications() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate('/login'); return; }
    fetchNotifications();
  }, [user, authLoading, navigate]);

  const fetchNotifications = async () => {
    try {
      const res = await axios.get(`${API}/api/notifications`, { withCredentials: true });
      setNotifications(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkRead = async (id) => {
    try {
      await axios.post(`${API}/api/notifications/${id}/read`, {}, { withCredentials: true });
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n));
    } catch (e) {
      console.error(e);
    }
  };

  const handleMarkAllRead = async () => {
    const unread = notifications.filter(n => !n.read);
    await Promise.all(unread.map(n => 
      axios.post(`${API}/api/notifications/${n.id}/read`, {}, { withCredentials: true }).catch(() => {})
    ));
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
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

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-8">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to home
        </Link>

        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Bell className="w-6 h-6 text-[#39FF14]" />
            <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="notifications-title">
              Notifications
            </h1>
            {unreadCount > 0 && (
              <span className="bg-[#39FF14] text-black text-xs font-bold px-2 py-0.5">{unreadCount} new</span>
            )}
          </div>
          {unreadCount > 0 && (
            <Button className="btn-secondary text-xs" onClick={handleMarkAllRead} data-testid="mark-all-read">
              Mark all read
            </Button>
          )}
        </div>

        {notifications.length === 0 ? (
          <div className="border border-white/10 bg-[#0A0A0A] p-16 text-center">
            <Bell className="w-12 h-12 text-[#9CA3AF] mx-auto mb-4" />
            <p className="text-[#9CA3AF]">No notifications yet</p>
          </div>
        ) : (
          <div className="border border-white/10 bg-[#0A0A0A] divide-y divide-white/5" data-testid="notifications-list">
            {notifications.map((notif) => (
              <NotificationItem key={notif.id} notification={notif} onMarkRead={handleMarkRead} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
