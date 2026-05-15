import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/dialog';
import Header from '../components/Header';
import { Package, ArrowLeft, Star, Truck, CheckCircle, Clock, MapPin, ExternalLink } from 'lucide-react';
import { getTrackingUrl } from '../lib/courierTracking';

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_STEPS = ['confirmed', 'processing', 'shipped', 'in_transit', 'out_for_delivery', 'delivered'];
const STATUS_LABELS = {
  confirmed: 'Confirmed',
  processing: 'Processing',
  shipped: 'Shipped',
  in_transit: 'In Transit',
  out_for_delivery: 'Out for Delivery',
  delivered: 'Delivered'
};

function ShippingTimeline({ shippingStatus, shippingUpdates = [] }) {
  const currentIdx = STATUS_STEPS.indexOf(shippingStatus || 'confirmed');

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-2">
        {STATUS_STEPS.map((step, i) => (
          <div key={step} className="flex flex-col items-center flex-1">
            <div className={`w-6 h-6 rounded-full flex items-center justify-center border-2 transition-all ${
              i <= currentIdx ? 'bg-[#39FF14] border-[#39FF14] text-black' : 'border-white/20 text-[#9CA3AF]'
            }`}>
              {i <= currentIdx ? <CheckCircle className="w-4 h-4" /> : <div className="w-2 h-2 rounded-full bg-current" />}
            </div>
            <p className={`text-[10px] mt-1 text-center ${i <= currentIdx ? 'text-[#39FF14]' : 'text-[#9CA3AF]'}`}>
              {STATUS_LABELS[step]}
            </p>
          </div>
        ))}
      </div>
      {/* Connecting line */}
      <div className="absolute top-3 left-3 right-3 h-0.5 bg-white/10 -z-10">
        <div
          className="h-full bg-[#39FF14] transition-all"
          style={{ width: `${(currentIdx / (STATUS_STEPS.length - 1)) * 100}%` }}
        />
      </div>
    </div>
  );
}

function StarPicker({ value, onChange, label }) {
  return (
    <div className="mb-4">
      <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">{label}</label>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className="p-1 transition-transform hover:scale-110"
          >
            <Star className={`w-6 h-6 ${star <= value ? 'fill-[#39FF14] text-[#39FF14]' : 'text-[#27272A] hover:text-[#9CA3AF]'}`} />
          </button>
        ))}
      </div>
    </div>
  );
}

export default function MyOrders() {
  const { user, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [reviewOrder, setReviewOrder] = useState(null);
  const [reviewForm, setReviewForm] = useState({ product_rating: 5, brand_rating: 5, comment: '' });
  const [submittingReview, setSubmittingReview] = useState(false);
  const [expandedOrder, setExpandedOrder] = useState(null);

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

  const handleReviewSubmit = async (e) => {
    e.preventDefault();
    if (!reviewOrder) return;
    setSubmittingReview(true);
    try {
      await axios.post(`${API}/api/reviews`, {
        order_id: reviewOrder.id,
        product_rating: reviewForm.product_rating,
        brand_rating: reviewForm.brand_rating,
        comment: reviewForm.comment || null
      }, { withCredentials: true });
      setReviewOpen(false);
      setReviewForm({ product_rating: 5, brand_rating: 5, comment: '' });
      fetchOrders();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setSubmittingReview(false);
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
              <div key={order.id} className="border border-white/10 bg-[#0A0A0A]">
                {/* Order Header */}
                <div
                  className="p-4 flex flex-col md:flex-row md:items-center gap-4 cursor-pointer hover:bg-white/5 transition-colors"
                  onClick={() => setExpandedOrder(expandedOrder === order.id ? null : order.id)}
                  data-testid={`order-${order.id}`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-1">
                      <h3 className="text-white font-bold">{order.product_name}</h3>
                      <span className={`text-xs uppercase tracking-wider px-2 py-0.5 ${
                        order.status === 'paid' ? 'bg-green-500/10 text-green-400 border border-green-500/30' :
                        order.status === 'initiated' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30' :
                        'bg-[#9CA3AF]/10 text-[#9CA3AF] border border-[#9CA3AF]/30'
                      }`}>
                        {order.status === 'paid' ? 'Paid' : order.status}
                      </span>
                    </div>
                    <p className="text-sm text-[#9CA3AF]">
                      {order.brand_name} · Size: {order.size} · {new Date(order.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="text-right flex items-center gap-4">
                    <div>
                      <p className="text-white font-bold">£{order.total_charged?.toFixed(2) || order.price?.toFixed(2)}</p>
                      <p className="text-xs text-[#9CA3AF]">incl. fees & shipping</p>
                    </div>
                    {order.status === 'paid' && !order.reviewed && (
                      <Button
                        className="btn-primary text-xs py-1 px-3"
                        onClick={(e) => {
                          e.stopPropagation();
                          setReviewOrder(order);
                          setReviewOpen(true);
                        }}
                        data-testid={`review-btn-${order.id}`}
                      >
                        <Star className="w-3 h-3 mr-1" /> Review
                      </Button>
                    )}
                    {order.reviewed && (
                      <span className="text-xs text-[#39FF14]">Reviewed</span>
                    )}
                  </div>
                </div>

                {/* Expanded - Shipping Timeline */}
                {expandedOrder === order.id && order.status === 'paid' && (
                  <div className="px-4 pb-4 border-t border-white/5 pt-4">
                    <div className="flex items-center gap-2 mb-4">
                      <Truck className="w-5 h-5 text-[#39FF14]" />
                      <h4 className="text-sm font-bold text-white uppercase">Shipping Status</h4>
                    </div>

                    <ShippingTimeline
                      shippingStatus={order.shipping_status || 'confirmed'}
                      shippingUpdates={order.shipping_updates || []}
                    />

                    {order.tracking_number && (
                      <div className="mt-4 p-3 bg-[#0F0F0F] border border-white/5">
                        <p className="text-xs text-[#9CA3AF] mb-1">Tracking Number</p>
                        <p className="text-white font-mono text-sm">{order.tracking_number}</p>
                        <p className="text-xs text-[#9CA3AF] mt-1">via {order.courier}</p>
                        {(() => {
                          const url = getTrackingUrl(order.courier, order.tracking_number);
                          if (!url) return null;
                          return (
                            <a
                              href={url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-1 mt-2 text-xs text-[#39FF14] hover:underline font-bold uppercase tracking-wider"
                              data-testid={`track-on-courier-${order.id}`}
                            >
                              Track on {order.courier} <ExternalLink className="w-3 h-3" />
                            </a>
                          );
                        })()}
                      </div>
                    )}

                    {!order.tracking_number && (
                      <p className="text-sm text-[#9CA3AF] mt-4 flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        Waiting for the brand to ship your order
                      </p>
                    )}

                    {/* Shipping updates timeline */}
                    {order.shipping_updates?.length > 0 && (
                      <div className="mt-4 space-y-2">
                        {order.shipping_updates.map((update, i) => (
                          <div key={i} className="flex gap-3 text-sm">
                            <span className="text-[#9CA3AF] text-xs w-24 flex-shrink-0">
                              {new Date(update.timestamp).toLocaleDateString()}
                            </span>
                            <span className="text-white">{update.message}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Review Dialog */}
      <Dialog open={reviewOpen} onOpenChange={setReviewOpen}>
        <DialogContent className="bg-[#0F0F0F] border-white/10 rounded-none max-w-md">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold text-white uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
              Leave a Review
            </DialogTitle>
          </DialogHeader>
          {reviewOrder && (
            <form onSubmit={handleReviewSubmit} className="space-y-4 mt-4">
              <p className="text-sm text-[#9CA3AF]">
                Reviewing: <span className="text-white">{reviewOrder.product_name}</span> from <span className="text-[#39FF14]">{reviewOrder.brand_name}</span>
              </p>

              <StarPicker
                value={reviewForm.product_rating}
                onChange={(val) => setReviewForm({ ...reviewForm, product_rating: val })}
                label="Product Rating"
              />

              <StarPicker
                value={reviewForm.brand_rating}
                onChange={(val) => setReviewForm({ ...reviewForm, brand_rating: val })}
                label="Brand Experience"
              />

              <div>
                <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-2">Comment (optional)</label>
                <Textarea
                  value={reviewForm.comment}
                  onChange={(e) => setReviewForm({ ...reviewForm, comment: e.target.value })}
                  className="input-brutalist min-h-[80px] resize-none"
                  placeholder="Share your experience..."
                  data-testid="review-comment-input"
                />
              </div>

              <Button type="submit" className="btn-primary w-full" disabled={submittingReview} data-testid="submit-review-button">
                {submittingReview ? 'Submitting...' : 'Submit Review'}
              </Button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
