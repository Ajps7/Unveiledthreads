import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Button } from '../components/ui/button';
import Header from '../components/Header';
import ImageUpload from '../components/ImageUpload';
import {
  MessageCircle, ThumbsUp, Send, Image, Users, TrendingUp, Clock, Trash2, Tag, Loader2
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function TimeAgo({ date }) {
  const seconds = Math.floor((Date.now() - new Date(date).getTime()) / 1000);
  if (seconds < 60) return <span>{seconds}s ago</span>;
  if (seconds < 3600) return <span>{Math.floor(seconds / 60)}m ago</span>;
  if (seconds < 86400) return <span>{Math.floor(seconds / 3600)}h ago</span>;
  return <span>{Math.floor(seconds / 86400)}d ago</span>;
}

function PostCard({ post, user, onLike, onDelete, onOpenComments }) {
  const isLiked = user && post.likes?.includes(user.id);
  const isOwn = user && post.user_id === user.id;
  const isAdmin = user && user.role === 'admin';

  return (
    <div className="border border-white/10 bg-[#0A0A0A]" data-testid={`post-${post.id}`}>
      {/* Header */}
      <div className="flex items-center gap-3 p-4 pb-0">
        <div className="w-10 h-10 rounded-full bg-[#1A1A1A] border border-white/10 flex items-center justify-center text-[#39FF14] font-bold flex-shrink-0" style={{ fontFamily: 'Clash Display, sans-serif' }}>
          {post.user_name?.charAt(0) || '?'}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-white font-medium text-sm">{post.user_name}</span>
            {post.brand_name && (
              <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 bg-[#39FF14]/10 text-[#39FF14] border border-[#39FF14]/30">
                Brand
              </span>
            )}
          </div>
          <span className="text-[#9CA3AF] text-xs"><TimeAgo date={post.created_at} /></span>
        </div>
        {(isOwn || isAdmin) && (
          <button onClick={() => onDelete(post.id)} className="text-[#9CA3AF] hover:text-red-400 transition-colors p-1" data-testid={`delete-post-${post.id}`}>
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Content */}
      <div className="px-4 py-3">
        <p className="text-white text-sm leading-relaxed whitespace-pre-wrap">{post.content}</p>
        {post.brand_tag && (
          <Link to={`/brands?search=${post.brand_tag}`} className="inline-flex items-center gap-1 mt-2 text-xs text-[#39FF14] hover:underline">
            <Tag className="w-3 h-3" /> {post.brand_tag}
          </Link>
        )}
      </div>

      {/* Image */}
      {post.image_url && (
        <div className="px-4 pb-3">
          <div className="aspect-video overflow-hidden border border-white/10 bg-[#0F0F0F]">
            <img
              src={post.image_url.startsWith('/api/') ? `${API}${post.image_url}` : post.image_url}
              alt=""
              className="w-full h-full object-cover"
            />
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-6 px-4 py-3 border-t border-white/5">
        <button
          onClick={() => onLike(post.id)}
          className={`flex items-center gap-1.5 text-sm transition-colors ${isLiked ? 'text-[#39FF14]' : 'text-[#9CA3AF] hover:text-white'}`}
          data-testid={`like-post-${post.id}`}
        >
          <ThumbsUp className={`w-4 h-4 ${isLiked ? 'fill-current' : ''}`} />
          <span>{post.like_count || 0}</span>
        </button>
        <button
          onClick={() => onOpenComments(post)}
          className="flex items-center gap-1.5 text-sm text-[#9CA3AF] hover:text-white transition-colors"
          data-testid={`comments-post-${post.id}`}
        >
          <MessageCircle className="w-4 h-4" />
          <span>{post.comment_count || 0}</span>
        </button>
      </div>
    </div>
  );
}

function CommentsPanel({ post, user, onClose }) {
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchComments = useCallback(async () => {
    try {
      const res = await axios.get(`${API}/api/community/posts/${post.id}/comments`);
      setComments(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [post.id]);

  useEffect(() => {
    fetchComments();
  }, [fetchComments]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!newComment.trim()) return;
    setError('');
    setSending(true);
    try {
      const res = await axios.post(`${API}/api/community/posts/${post.id}/comments`, { content: newComment.trim() }, { withCredentials: true });
      setComments([...comments, res.data]);
      setNewComment('');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="border border-white/10 bg-[#0F0F0F]">
      <div className="flex items-center justify-between p-4 border-b border-white/5">
        <h3 className="text-sm font-bold text-white uppercase">Comments on {post.user_name}'s post</h3>
        <button onClick={onClose} className="text-[#9CA3AF] hover:text-white text-sm">Close</button>
      </div>

      <div className="max-h-[300px] overflow-y-auto p-4 space-y-3">
        {loading ? (
          <Loader2 className="w-5 h-5 text-[#39FF14] animate-spin mx-auto" />
        ) : comments.length === 0 ? (
          <p className="text-[#9CA3AF] text-sm text-center py-4">No comments yet. Start the conversation.</p>
        ) : (
          comments.map((c) => (
            <div key={c.id} className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-[#1A1A1A] border border-white/10 flex items-center justify-center text-xs text-[#39FF14] font-bold flex-shrink-0">
                {c.user_name?.charAt(0)}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-white text-xs font-medium">{c.user_name}</span>
                  {c.brand_name && <span className="text-[8px] uppercase text-[#39FF14] bg-[#39FF14]/10 px-1">Brand</span>}
                  <span className="text-[#9CA3AF] text-[10px]"><TimeAgo date={c.created_at} /></span>
                </div>
                <p className="text-[#C0C0C0] text-sm mt-0.5">{c.content}</p>
              </div>
            </div>
          ))
        )}
      </div>

      {error && <p className="px-4 text-red-400 text-xs">{error}</p>}

      {user ? (
        <form onSubmit={handleSend} className="flex gap-2 p-4 border-t border-white/5">
          <Input
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            className="input-brutalist flex-1 text-sm"
            placeholder="Add a comment..."
            data-testid="community-comment-input"
          />
          <Button type="submit" className="btn-primary px-3" disabled={sending || !newComment.trim()}>
            <Send className="w-4 h-4" />
          </Button>
        </form>
      ) : (
        <div className="p-4 border-t border-white/5 text-center">
          <Link to="/login" className="text-[#39FF14] text-sm hover:underline">Login to comment</Link>
        </div>
      )}
    </div>
  );
}

export default function Community() {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('latest');
  const [newPost, setNewPost] = useState('');
  const [postImage, setPostImage] = useState('');
  const [brandTag, setBrandTag] = useState('');
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState('');
  const [showComments, setShowComments] = useState(null);
  const [brands, setBrands] = useState([]);

  const fetchPosts = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${API}/api/community/posts?sort=${sortBy}`);
      setPosts(res.data);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  }, [sortBy]);

  useEffect(() => {
    fetchPosts();
    fetchBrands();
  }, [fetchPosts]);

  const fetchBrands = async () => {
    try {
      const res = await axios.get(`${API}/api/brands`);
      setBrands(res.data);
    } catch (e) { console.debug('Brands fetch failed (non-critical):', e); }
  };

  const handlePost = async (e) => {
    e.preventDefault();
    if (!newPost.trim()) return;
    setError('');
    setPosting(true);
    try {
      await axios.post(`${API}/api/community/posts`, {
        content: newPost.trim(),
        brand_tag: brandTag || null,
        image_url: postImage || null,
      }, { withCredentials: true });
      setNewPost('');
      setPostImage('');
      setBrandTag('');
      fetchPosts();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to post');
    } finally {
      setPosting(false);
    }
  };

  const handleLike = async (postId) => {
    if (!user) return;
    try {
      const res = await axios.post(`${API}/api/community/posts/${postId}/like`, {}, { withCredentials: true });
      setPosts(posts.map(p => p.id === postId ? {
        ...p,
        likes: res.data.liked ? [...(p.likes || []), user.id] : (p.likes || []).filter(id => id !== user.id),
        like_count: res.data.like_count
      } : p));
    } catch (e) { console.error(e); }
  };

  const handleDelete = async (postId) => {
    if (!window.confirm('Delete this post?')) return;
    try {
      await axios.delete(`${API}/api/community/posts/${postId}`, { withCredentials: true });
      setPosts(posts.filter(p => p.id !== postId));
      if (showComments?.id === postId) setShowComments(null);
    } catch (e) { console.error(e); }
  };

  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />

      <div className="max-w-3xl mx-auto px-6 md:px-12 py-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-2">
          <Users className="w-7 h-7 text-[#39FF14]" />
          <h1 className="text-2xl md:text-3xl font-black tracking-tighter uppercase text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="community-title">
            COMMUNITY
          </h1>
        </div>
        <p className="text-[#9CA3AF] mb-8">Share your thoughts on drops, brands, and streetwear culture</p>

        {/* Create Post */}
        {user ? (
          <div className="border border-white/10 bg-[#0A0A0A] p-4 mb-6">
            <form onSubmit={handlePost}>
              <Textarea
                value={newPost}
                onChange={(e) => setNewPost(e.target.value)}
                className="input-brutalist min-h-[80px] resize-none mb-3"
                placeholder="What's on your mind? Share your take on a brand, a new drop, or your latest fit..."
                data-testid="community-post-input"
              />

              {postImage && (
                <div className="relative mb-3 inline-block">
                  <img src={postImage.startsWith('/api/') ? `${API}${postImage}` : postImage} alt="Post" className="h-20 border border-white/10" />
                  <button type="button" onClick={() => setPostImage('')} className="absolute -top-2 -right-2 bg-black border border-white/10 text-white p-0.5"><Trash2 className="w-3 h-3" /></button>
                </div>
              )}

              {error && <p className="text-red-400 text-xs mb-3">{error}</p>}

              <div className="flex flex-wrap items-center gap-3">
                <ImageUpload
                  label=""
                  onUpload={(url) => setPostImage(url)}
                  className="inline-block"
                />

                <select
                  value={brandTag}
                  onChange={(e) => setBrandTag(e.target.value)}
                  className="bg-transparent border border-white/20 text-[#9CA3AF] text-xs px-3 py-2 outline-none focus:border-[#39FF14]"
                  data-testid="brand-tag-select"
                >
                  <option value="">Tag a brand (optional)</option>
                  {brands.map(b => <option key={b.id} value={b.brand_name}>{b.brand_name}</option>)}
                </select>

                <div className="flex-1" />

                <Button type="submit" className="btn-primary text-sm" disabled={posting || !newPost.trim()} data-testid="submit-post-button">
                  {posting ? <Loader2 className="w-4 h-4 animate-spin" /> : <><Send className="w-4 h-4 mr-1" /> Post</>}
                </Button>
              </div>
            </form>
          </div>
        ) : (
          <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6 text-center">
            <p className="text-[#9CA3AF] mb-3">Join the conversation</p>
            <Link to="/login"><Button className="btn-primary text-sm">Login to Post</Button></Link>
          </div>
        )}

        {/* Sort Tabs */}
        <div className="flex gap-4 mb-6 border-b border-white/10">
          <button
            onClick={() => setSortBy('latest')}
            className={`pb-3 text-sm uppercase tracking-wider transition-colors ${sortBy === 'latest' ? 'text-[#39FF14] border-b-2 border-[#39FF14]' : 'text-[#9CA3AF] hover:text-white'}`}
            data-testid="sort-latest"
          >
            <Clock className="w-4 h-4 inline mr-1" /> Latest
          </button>
          <button
            onClick={() => setSortBy('trending')}
            className={`pb-3 text-sm uppercase tracking-wider transition-colors ${sortBy === 'trending' ? 'text-[#39FF14] border-b-2 border-[#39FF14]' : 'text-[#9CA3AF] hover:text-white'}`}
            data-testid="sort-trending"
          >
            <TrendingUp className="w-4 h-4 inline mr-1" /> Trending
          </button>
        </div>

        {/* Posts */}
        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="w-8 h-8 text-[#39FF14] animate-spin" />
          </div>
        ) : posts.length === 0 ? (
          <div className="border border-white/10 bg-[#0A0A0A] p-12 text-center">
            <Users className="w-12 h-12 text-[#9CA3AF] mx-auto mb-4" />
            <p className="text-[#9CA3AF]">No posts yet. Be the first to share!</p>
          </div>
        ) : (
          <div className="space-y-4" data-testid="community-posts">
            {posts.map((post) => (
              <div key={post.id}>
                <PostCard
                  post={post}
                  user={user}
                  onLike={handleLike}
                  onDelete={handleDelete}
                  onOpenComments={(p) => setShowComments(showComments?.id === p.id ? null : p)}
                />
                {showComments?.id === post.id && (
                  <CommentsPanel post={post} user={user} onClose={() => setShowComments(null)} />
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
