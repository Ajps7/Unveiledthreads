import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { ArrowLeft, MapPin, ShoppingBag, Loader2, Star, Truck, MessageSquare, Send, ThumbsUp, Info } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import Header from '../components/Header';
import { calcBuyerFee, BUYER_PROTECTION_TOOLTIP } from '../lib/fees';

const API = process.env.REACT_APP_BACKEND_URL;

function StarRating({ rating, size = 16 }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={`w-[${size}px] h-[${size}px] ${star <= rating ? 'fill-[#39FF14] text-[#39FF14]' : 'text-[#27272A]'}`}
          style={{ width: size, height: size }}
        />
      ))}
    </div>
  );
}

function ReviewItem({ review }) {
  return (
    <div className="border-b border-white/5 py-4 last:border-0">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-white font-medium">{review.buyer_name}</span>
        <span className="text-xs text-[#9CA3AF]">{new Date(review.created_at).toLocaleDateString()}</span>
      </div>
      <div className="flex gap-6 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#9CA3AF]">Product</span>
          <StarRating rating={review.product_rating} size={12} />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[#9CA3AF]">Brand</span>
          <StarRating rating={review.brand_rating} size={12} />
        </div>
      </div>
      {review.comment && (
        <p className="text-sm text-[#9CA3AF]">{review.comment}</p>
      )}
    </div>
  );
}

export default function ProductDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const [product, setProduct] = useState(null);
  const [selectedSize, setSelectedSize] = useState('');
  const [loading, setLoading] = useState(true);
  const [purchasing, setPurchasing] = useState(false);
  const [reviews, setReviews] = useState({ reviews: [], count: 0, avg_product_rating: 0, avg_brand_rating: 0 });
  const [showFeeInfo, setShowFeeInfo] = useState(false);

  const fetchProduct = useCallback(async () => {
    try {
      const [prodRes, revRes] = await Promise.all([
        axios.get(`${API}/api/products/${id}`),
        axios.get(`${API}/api/reviews/product/${id}`).catch(() => ({ data: { reviews: [], count: 0, avg_product_rating: 0, avg_brand_rating: 0 } }))
      ]);
      setProduct(prodRes.data);
      setReviews(revRes.data);
      if (prodRes.data.sizes?.length > 0) setSelectedSize(prodRes.data.sizes[0]);
      // Track view
      axios.post(`${API}/api/analytics/view/${id}`, {}, { withCredentials: true }).catch(() => {});
    } catch (error) {
      console.error('Error fetching product:', error);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchProduct();
  }, [fetchProduct]);

  const handlePurchase = async () => {
    if (!user) { window.location.href = '/login'; return; }
    if (!selectedSize) return;
    setPurchasing(true);
    try {
      const response = await axios.post(
        `${API}/api/orders/checkout`,
        { product_id: id, size: selectedSize, origin_url: window.location.origin },
        { withCredentials: true }
      );
      window.location.href = response.data.url;
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to create checkout');
    } finally {
      setPurchasing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex items-center justify-center h-[60vh]">
          <div className="animate-spin w-8 h-8 border-2 border-[#39FF14] border-t-transparent rounded-full" />
        </div>
      </div>
    );
  }

  if (!product) {
    return (
      <div className="min-h-screen bg-[#050505]">
        <Header />
        <div className="flex flex-col items-center justify-center h-[60vh]">
          <p className="text-[#9CA3AF] mb-4">Product not found</p>
          <Link to="/products"><Button className="btn-secondary">Back to Products</Button></Link>
        </div>
      </div>
    );
  }

  const shippingCost = product.shipping_cost || 0;
  const platformFee = calcBuyerFee(product.price);
  const totalPrice = product.price + platformFee + shippingCost;

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-7xl mx-auto px-6 md:px-12 py-8">
        <Link to="/products" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to products
        </Link>

        <div className="grid lg:grid-cols-2 gap-12">
          {/* Images */}
          <div className="space-y-4">
            <div className="aspect-[3/4] overflow-hidden border border-white/10 bg-[#0F0F0F]">
              {product.images?.length > 0 ? (
                <img
                  src={product.images[0].startsWith('/api/') ? `${API}${product.images[0]}` : product.images[0]}
                  alt={product.name}
                  className="w-full h-full object-cover"
                  data-testid="product-main-image"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-[#9CA3AF]">No Image</div>
              )}
            </div>
            {product.images?.length > 1 && (
              <div className="grid grid-cols-4 gap-2">
                {product.images.slice(1).map((img, i) => (
                  <div key={img} className="aspect-square overflow-hidden border border-white/10 bg-[#0F0F0F]">
                    <img src={img.startsWith('/api/') ? `${API}${img}` : img} alt={`${product.name} ${i + 2}`} className="w-full h-full object-cover" />
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Info */}
          <div>
            {product.brand && (
              <Link to={`/brands/${product.brand.id}`} className="inline-flex items-center gap-2 text-[#39FF14] text-sm uppercase tracking-wider hover:underline mb-4" data-testid="product-brand-link">
                {product.brand.brand_name}
              </Link>
            )}

            <h1 className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-4 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="product-name">
              {product.name}
            </h1>

            {/* Rating */}
            {reviews.count > 0 && (
              <div className="flex items-center gap-3 mb-4">
                <StarRating rating={Math.round(reviews.avg_product_rating)} size={16} />
                <span className="text-sm text-[#9CA3AF]">{reviews.avg_product_rating}/5 ({reviews.count} review{reviews.count !== 1 ? 's' : ''})</span>
              </div>
            )}

            <p className="text-3xl font-bold text-[#C0C0C0] mb-1" data-testid="product-price">
              £{product.price.toFixed(2)}
              {product.is_dead_stock && product.original_price && product.original_price > product.price && (
                <>
                  <span className="ml-3 text-base text-[#6B7280] line-through font-normal" data-testid="product-original-price">
                    £{Number(product.original_price).toFixed(2)}
                  </span>
                  <span className="ml-3 text-xs uppercase tracking-wider px-2 py-1 bg-[#39FF14] text-black font-bold align-middle" data-testid="product-discount-badge">
                    -{product.discount_percent || 0}% · Dead Stock
                  </span>
                </>
              )}
            </p>

            {/* Price breakdown */}
            <div className="text-xs text-[#9CA3AF] mb-6 space-y-1">
              <p className="flex items-center gap-1.5" data-testid="buyer-protection-fee-line">
                + £{platformFee.toFixed(2)} Buyer Protection
                <button
                  type="button"
                  onClick={() => setShowFeeInfo(!showFeeInfo)}
                  aria-label="What is Buyer Protection?"
                  className="text-[#9CA3AF] hover:text-[#39FF14] transition-colors"
                  data-testid="buyer-protection-info-button"
                >
                  <Info className="w-3.5 h-3.5" />
                </button>
              </p>
              {showFeeInfo && (
                <p className="text-[11px] leading-relaxed bg-[#0F0F0F] border border-white/10 p-3 max-w-md" data-testid="buyer-protection-info-text">
                  {BUYER_PROTECTION_TOOLTIP}
                </p>
              )}
              {shippingCost > 0 && (
                <p className="flex items-center gap-1"><Truck className="w-3 h-3" /> + £{shippingCost.toFixed(2)} shipping</p>
              )}
              {shippingCost === 0 && (
                <p className="flex items-center gap-1 text-[#39FF14]"><Truck className="w-3 h-3" /> Free shipping</p>
              )}
              <p className="text-[#C0C0C0] font-medium">Total: £{totalPrice.toFixed(2)}</p>
            </div>

            <p className="text-[#9CA3AF] mb-8 leading-relaxed" data-testid="product-description">{product.description}</p>

            {/* Sizes */}
            {product.sizes?.length > 0 && (
              <div className="mb-8">
                <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-3">Size</label>
                <div className="flex flex-wrap gap-2">
                  {product.sizes.map((size) => (
                    <button
                      key={size}
                      onClick={() => setSelectedSize(size)}
                      className={`px-4 py-2 border transition-all ${selectedSize === size ? 'border-[#39FF14] bg-[#39FF14]/10 text-[#39FF14]' : 'border-white/20 text-white hover:border-white/40'}`}
                      data-testid={`size-${size}`}
                    >
                      {size}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <p className="text-sm text-[#9CA3AF] mb-6">
              {product.stock > 0 ? <span className="text-[#39FF14]">{product.stock} in stock</span> : <span className="text-red-400">Out of stock</span>}
            </p>

            {product.seller_payments_ready === false && (
              <div className="mb-4 border border-yellow-500/30 bg-yellow-500/5 p-3 text-xs text-yellow-200" data-testid="seller-not-ready-banner">
                <strong className="text-yellow-300">Coming soon to checkout.</strong> {product.brand?.brand_name || 'This brand'} is finishing their secure Stripe payout setup. Send them a message to be notified the moment it's live.
              </div>
            )}

            <div className="flex gap-4 mb-4">
              <Button
                className="btn-primary flex-1"
                disabled={product.stock === 0 || !selectedSize || purchasing || product.seller_payments_ready === false}
                onClick={handlePurchase}
                data-testid="buy-now-button"
              >
                {purchasing
                  ? <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> Processing...</>
                  : product.seller_payments_ready === false
                    ? <><ShoppingBag className="w-5 h-5 mr-2" /> Payments unavailable</>
                    : <><ShoppingBag className="w-5 h-5 mr-2" /> BUY NOW — £{totalPrice.toFixed(2)}</>}
              </Button>
            </div>
            {product.brand && user && (
              <Link to={`/messages?to=${product.brand.user_id}`}>
                <Button className="btn-secondary w-full mb-4" data-testid="message-brand-button">
                  <MessageSquare className="w-4 h-4 mr-2" /> Message {product.brand.brand_name}
                </Button>
              </Link>
            )}

            {/* Brand Card */}
            {product.brand && (
              <div className="border border-white/10 p-6 bg-[#0A0A0A]">
                <h3 className="text-sm uppercase tracking-wider text-[#C0C0C0] mb-4">About the Brand</h3>
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-full overflow-hidden bg-[#1A1A1A] border border-white/10 flex-shrink-0">
                    {product.brand.logo_url ? (
                      <img src={product.brand.logo_url.startsWith('/api/') ? `${API}${product.brand.logo_url}` : product.brand.logo_url} alt={product.brand.brand_name} className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-[#39FF14] font-bold">{product.brand.brand_name.charAt(0)}</div>
                    )}
                  </div>
                  <div>
                    <h4 className="text-white font-bold mb-1">{product.brand.brand_name}</h4>
                    <p className="text-[#9CA3AF] text-sm line-clamp-2">{product.brand.description}</p>
                    <div className="flex items-center gap-4 mt-2 text-xs text-[#C0C0C0]">
                      <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{product.brand.location}</span>
                    </div>
                  </div>
                </div>
                <Link to={`/brands/${product.brand.id}`}>
                  <Button className="btn-secondary w-full mt-4" data-testid="view-brand-button">View Brand</Button>
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Reviews Section */}
        <section className="mt-16 border-t border-white/10 pt-12">
          <h2 className="text-xl md:text-2xl font-bold uppercase tracking-tight text-white mb-8" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            Reviews {reviews.count > 0 && `(${reviews.count})`}
          </h2>

          {reviews.count > 0 ? (
            <div>
              <div className="flex gap-8 mb-8">
                <div className="border border-white/10 bg-[#0A0A0A] p-4 text-center">
                  <p className="text-2xl font-bold text-white">{reviews.avg_product_rating}</p>
                  <StarRating rating={Math.round(reviews.avg_product_rating)} size={14} />
                  <p className="text-xs text-[#9CA3AF] mt-1">Product</p>
                </div>
                <div className="border border-white/10 bg-[#0A0A0A] p-4 text-center">
                  <p className="text-2xl font-bold text-white">{reviews.avg_brand_rating}</p>
                  <StarRating rating={Math.round(reviews.avg_brand_rating)} size={14} />
                  <p className="text-xs text-[#9CA3AF] mt-1">Brand</p>
                </div>
              </div>
              <div className="space-y-0" data-testid="reviews-list">
                {reviews.reviews.map((review) => (
                  <ReviewItem key={review.id} review={review} />
                ))}
              </div>
            </div>
          ) : (
            <p className="text-[#9CA3AF]">No reviews yet. Be the first to review after purchasing!</p>
          )}
        </section>

        {/* Product Comments Section */}
        <ProductComments productId={id} user={user} />
      </div>
    </div>
  );
}

function ProductComments({ productId, user }) {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchComments = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/products/${productId}/comments`);
      setComments(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [productId]);

  useEffect(() => {
    fetchComments();
  }, [fetchComments]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    setError('');
    setSending(true);
    try {
      const res = await axios.post(`${API}/api/products/${productId}/comments`, { content: newComment.trim() }, { withCredentials: true });
      setComments([res.data, ...comments]);
      setNewComment('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to post comment');
    } finally {
      setSending(false);
    }
  };

  const handleLike = async (commentId) => {
    if (!user) return;
    try {
      const res = await axios.post(`${API}/api/products/${productId}/comments/${commentId}/like`, {}, { withCredentials: true });
      setComments(comments.map(c => c.id === commentId ? {
        ...c,
        likes: res.data.liked ? [...(c.likes || []), user.id] : (c.likes || []).filter(id => id !== user.id)
      } : c));
    } catch (e) { console.error(e); }
  };

  const handleDelete = async (commentId) => {
    try {
      await axios.delete(`${API}/api/products/${productId}/comments/${commentId}`, { withCredentials: true });
      setComments(comments.filter(c => c.id !== commentId));
    } catch (e) { console.error(e); }
  };

  return (
    <section className="mt-12 border-t border-white/10 pt-12">
      <h2 className="text-xl md:text-2xl font-bold uppercase tracking-tight text-white mb-6" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="product-comments-title">
        Discussion ({comments.length})
      </h2>

      {/* Add comment */}
      {user ? (
        <form onSubmit={handleSend} className="flex gap-3 mb-6">
          <div className="w-9 h-9 rounded-full bg-[#1A1A1A] border border-white/10 flex items-center justify-center text-xs text-[#39FF14] font-bold flex-shrink-0">
            {user.name?.charAt(0)}
          </div>
          <div className="flex-1">
            <Input
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              className="input-brutalist text-sm"
              placeholder="Share your thoughts on this piece..."
              data-testid="product-comment-input"
            />
            {error && <p className="text-red-400 text-xs mt-1">{error}</p>}
          </div>
          <Button type="submit" className="btn-primary px-4" disabled={sending || !newComment.trim()} data-testid="product-comment-submit">
            <Send className="w-4 h-4" />
          </Button>
        </form>
      ) : (
        <div className="mb-6 p-4 border border-white/10 bg-[#0A0A0A] text-center">
          <Link to="/login" className="text-[#39FF14] text-sm hover:underline">Login to join the discussion</Link>
        </div>
      )}

      {/* Comments list */}
      {loading ? (
        <Loader2 className="w-6 h-6 text-[#39FF14] animate-spin mx-auto" />
      ) : comments.length === 0 ? (
        <p className="text-[#9CA3AF] text-sm">No comments yet. Be the first to share your thoughts!</p>
      ) : (
        <div className="space-y-4" data-testid="product-comments-list">
          {comments.map((c) => {
            const isLiked = user && c.likes?.includes(user.id);
            const isOwn = user && c.user_id === user.id;
            const isAdmin = user && user.role === 'admin';

            return (
              <div key={c.id} className="flex gap-3" data-testid={`product-comment-${c.id}`}>
                <div className="w-9 h-9 rounded-full bg-[#1A1A1A] border border-white/10 flex items-center justify-center text-xs text-[#39FF14] font-bold flex-shrink-0">
                  {c.user_name?.charAt(0)}
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-white text-sm font-medium">{c.user_name}</span>
                    {c.brand_name && (
                      <span className="text-[8px] uppercase tracking-wider px-1.5 py-0.5 bg-[#39FF14]/10 text-[#39FF14] border border-[#39FF14]/30">Brand</span>
                    )}
                    <span className="text-[#9CA3AF] text-xs">{new Date(c.created_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-[#C0C0C0] text-sm">{c.content}</p>
                  <div className="flex items-center gap-4 mt-2">
                    <button
                      onClick={() => handleLike(c.id)}
                      className={`flex items-center gap-1 text-xs transition-colors ${isLiked ? 'text-[#39FF14]' : 'text-[#9CA3AF] hover:text-white'}`}
                    >
                      <ThumbsUp className={`w-3 h-3 ${isLiked ? 'fill-current' : ''}`} />
                      {c.likes?.length || 0}
                    </button>
                    {(isOwn || isAdmin) && (
                      <button onClick={() => handleDelete(c.id)} className="text-xs text-[#9CA3AF] hover:text-red-400 transition-colors">
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
