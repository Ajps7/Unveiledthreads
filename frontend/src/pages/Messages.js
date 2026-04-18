import { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import Header from '../components/Header';
import { MessageSquare, Send, ArrowLeft, AlertTriangle, Loader2 } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

function ConversationList({ conversations, activeId, onSelect }) {
  if (conversations.length === 0) {
    return (
      <div className="p-8 text-center">
        <MessageSquare className="w-10 h-10 text-[#9CA3AF] mx-auto mb-3" />
        <p className="text-[#9CA3AF] text-sm">No conversations yet</p>
      </div>
    );
  }

  return (
    <div className="divide-y divide-white/5">
      {conversations.map((convo) => (
        <button
          key={convo.id}
          onClick={() => onSelect(convo)}
          className={`w-full text-left p-4 hover:bg-white/5 transition-colors ${activeId === convo.id ? 'bg-white/5 border-l-2 border-[#39FF14]' : ''}`}
          data-testid={`conversation-${convo.id}`}
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#1A1A1A] border border-white/10 flex items-center justify-center text-[#39FF14] font-bold flex-shrink-0">
              {(convo.other_brand_name || convo.other_user?.name || '?').charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-white font-medium text-sm truncate">
                {convo.other_brand_name || convo.other_user?.name || 'User'}
              </p>
              <p className="text-[#9CA3AF] text-xs truncate">{convo.last_message}</p>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}

function MessageBubble({ message, isOwn }) {
  return (
    <div className={`flex ${isOwn ? 'justify-end' : 'justify-start'} mb-3`}>
      <div className={`max-w-[75%] px-4 py-2.5 ${
        isOwn
          ? 'bg-[#39FF14]/10 border border-[#39FF14]/20 text-white'
          : 'bg-[#0F0F0F] border border-white/10 text-white'
      }`}>
        {!isOwn && (
          <p className="text-xs text-[#39FF14] mb-1 font-medium">{message.sender_name}</p>
        )}
        <p className="text-sm leading-relaxed">{message.content}</p>
        <p className="text-[10px] text-[#9CA3AF] mt-1 text-right">
          {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
    </div>
  );
}

export default function Messages() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [conversations, setConversations] = useState([]);
  const [activeConvo, setActiveConvo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const messagesEndRef = useRef(null);
  const pollRef = useRef(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) { navigate('/login'); return; }
    fetchConversations();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [user, authLoading, navigate]);

  useEffect(() => {
    if (activeConvo) {
      fetchMessages(activeConvo.id);
      // Poll for new messages every 5s
      if (pollRef.current) clearInterval(pollRef.current);
      pollRef.current = setInterval(() => fetchMessages(activeConvo.id), 5000);
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [activeConvo]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchConversations = async () => {
    try {
      const res = await axios.get(`${API}/api/conversations`, { withCredentials: true });
      setConversations(res.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchMessages = async (convoId) => {
    try {
      const res = await axios.get(`${API}/api/conversations/${convoId}/messages`, { withCredentials: true });
      setMessages(res.data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeConvo) return;
    setError('');
    setSending(true);

    const recipientId = activeConvo.participant_1 === user.id ? activeConvo.participant_2 : activeConvo.participant_1;

    try {
      await axios.post(`${API}/api/messages/send`, {
        recipient_id: recipientId,
        content: newMessage.trim()
      }, { withCredentials: true });
      setNewMessage('');
      fetchMessages(activeConvo.id);
      fetchConversations();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send');
    } finally {
      setSending(false);
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
      <div className="max-w-6xl mx-auto px-6 md:px-12 py-8">
        <div className="flex items-center gap-3 mb-6">
          <MessageSquare className="w-6 h-6 text-[#39FF14]" />
          <h1 className="text-xl md:text-2xl font-black tracking-tighter uppercase text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="messages-title">
            Messages
          </h1>
        </div>

        <div className="grid md:grid-cols-[320px_1fr] border border-white/10 min-h-[500px]">
          {/* Sidebar */}
          <div className="border-r border-white/10 bg-[#0A0A0A] overflow-y-auto max-h-[600px]">
            <div className="p-3 border-b border-white/10">
              <p className="text-xs text-[#9CA3AF] uppercase tracking-wider">{conversations.length} conversations</p>
            </div>
            <ConversationList
              conversations={conversations}
              activeId={activeConvo?.id}
              onSelect={setActiveConvo}
            />
          </div>

          {/* Chat Area */}
          <div className="flex flex-col bg-[#050505]">
            {activeConvo ? (
              <>
                {/* Chat Header */}
                <div className="p-4 border-b border-white/10 bg-[#0A0A0A]">
                  <p className="text-white font-bold">
                    {activeConvo.other_brand_name || activeConvo.other_user?.name || 'User'}
                  </p>
                  {activeConvo.order_id && (
                    <p className="text-xs text-[#9CA3AF]">Re: Order</p>
                  )}
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 max-h-[400px]" data-testid="messages-area">
                  {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} isOwn={msg.sender_id === user.id} />
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                {/* Error */}
                {error && (
                  <div className="px-4 py-2 bg-red-500/10 border-t border-red-500/20 flex items-center gap-2 text-red-400 text-sm">
                    <AlertTriangle className="w-4 h-4" />
                    {error}
                  </div>
                )}

                {/* Input */}
                <form onSubmit={handleSend} className="p-4 border-t border-white/10 bg-[#0A0A0A] flex gap-2">
                  <Input
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    className="input-brutalist flex-1"
                    placeholder="Type a message..."
                    data-testid="message-input"
                  />
                  <Button type="submit" className="btn-primary px-4" disabled={sending || !newMessage.trim()} data-testid="send-message-button">
                    <Send className="w-4 h-4" />
                  </Button>
                </form>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-center p-8">
                <div>
                  <MessageSquare className="w-12 h-12 text-[#9CA3AF] mx-auto mb-4" />
                  <p className="text-[#9CA3AF]">Select a conversation or message a brand from a product page</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
