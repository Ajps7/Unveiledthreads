import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Button } from './ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { User, LogOut, ShoppingBag, LayoutDashboard, Shield, Menu, X, Heart, Bell, BarChart3, Package, MessageSquare, Gift } from 'lucide-react';
import { useState, useEffect } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL;

export default function Header() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [unreadMessages, setUnreadMessages] = useState(0);

  useEffect(() => {
    if (user) {
      Promise.all([
        axios.get(`${API}/api/notifications/unread-count`, { withCredentials: true }).catch(() => ({ data: { count: 0 } })),
        axios.get(`${API}/api/messages/unread-count`, { withCredentials: true }).catch(() => ({ data: { count: 0 } }))
      ]).then(([notifRes, msgRes]) => {
        setUnreadCount(notifRes.data.count);
        setUnreadMessages(msgRes.data.count);
      });
    }
  }, [user]);

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-black/60 border-b border-white/10">
      <div className="max-w-7xl mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2" data-testid="header-logo">
            <span 
              className="text-xl font-black tracking-tighter text-white uppercase"
              style={{ fontFamily: 'Clash Display, sans-serif' }}
            >
              UNVEILED
            </span>
            <span className="hidden md:inline text-xs text-[#39FF14] uppercase tracking-wider">
              Threads
            </span>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            <Link 
              to="/products" 
              className="text-sm text-[#C0C0C0] hover:text-white transition-colors uppercase tracking-wider"
              data-testid="nav-products"
            >
              Shop
            </Link>
            <Link 
              to="/brands" 
              className="text-sm text-[#C0C0C0] hover:text-white transition-colors uppercase tracking-wider"
              data-testid="nav-brands"
            >
              Brands
            </Link>
            <Link 
              to="/apply" 
              className="text-sm text-[#39FF14] hover:text-white transition-colors uppercase tracking-wider"
              data-testid="nav-apply"
            >
              Sell
            </Link>
          </nav>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            {user ? (
              <>
                {/* Messages icon */}
                <Link to="/messages" className="relative text-[#C0C0C0] hover:text-white transition-colors" data-testid="header-messages">
                  <MessageSquare className="w-5 h-5" />
                  {unreadMessages > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#39FF14] text-black text-[10px] font-bold rounded-full flex items-center justify-center">
                      {unreadMessages > 9 ? '9+' : unreadMessages}
                    </span>
                  )}
                </Link>

                {/* Wishlist icon */}
                <Link to="/wishlist" className="relative text-[#C0C0C0] hover:text-white transition-colors" data-testid="header-wishlist">
                  <Heart className="w-5 h-5" />
                </Link>

                {/* Notification bell */}
                <Link to="/notifications" className="relative text-[#C0C0C0] hover:text-white transition-colors" data-testid="header-notifications">
                  <Bell className="w-5 h-5" />
                  {unreadCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-4 h-4 bg-[#39FF14] text-black text-[10px] font-bold rounded-full flex items-center justify-center">
                      {unreadCount > 9 ? '9+' : unreadCount}
                    </span>
                  )}
                </Link>

                <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="text-white hover:bg-white/10 rounded-none" data-testid="user-menu-button">
                    <User className="w-5 h-5 mr-2" />
                    <span className="hidden md:inline">{user.name}</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="bg-[#0F0F0F] border-white/10 rounded-none min-w-[200px]">
                  <div className="px-3 py-2 border-b border-white/10">
                    <p className="text-sm text-white font-medium">{user.name}</p>
                    <p className="text-xs text-[#9CA3AF]">{user.email}</p>
                    <span className="inline-block mt-1 text-xs uppercase tracking-wider px-2 py-0.5 bg-[#39FF14]/10 text-[#39FF14] border border-[#39FF14]/30">
                      {user.role}
                    </span>
                  </div>
                  
                  {(user.role === 'brand' || user.role === 'admin') && (
                    <>
                      <DropdownMenuItem 
                        className="text-[#C0C0C0] hover:text-white hover:bg-white/5 rounded-none cursor-pointer"
                        onClick={() => navigate('/brand/dashboard')}
                        data-testid="brand-dashboard-link"
                      >
                        <LayoutDashboard className="w-4 h-4 mr-2" />
                        Brand Dashboard
                      </DropdownMenuItem>
                      <DropdownMenuItem 
                        className="text-[#C0C0C0] hover:text-white hover:bg-white/5 rounded-none cursor-pointer"
                        onClick={() => navigate('/brand/analytics')}
                        data-testid="brand-analytics-link"
                      >
                        <BarChart3 className="w-4 h-4 mr-2" />
                        Analytics
                      </DropdownMenuItem>
                      <DropdownMenuItem 
                        className="text-[#C0C0C0] hover:text-white hover:bg-white/5 rounded-none cursor-pointer"
                        onClick={() => navigate('/brand/products')}
                        data-testid="my-products-link"
                      >
                        <ShoppingBag className="w-4 h-4 mr-2" />
                        My Products
                      </DropdownMenuItem>
                    </>
                  )}
                  
                  <DropdownMenuItem 
                    className="text-[#C0C0C0] hover:text-white hover:bg-white/5 rounded-none cursor-pointer"
                    onClick={() => navigate('/wishlist')}
                    data-testid="wishlist-link"
                  >
                    <Heart className="w-4 h-4 mr-2" />
                    Wishlist
                  </DropdownMenuItem>
                  <DropdownMenuItem 
                    className="text-[#C0C0C0] hover:text-white hover:bg-white/5 rounded-none cursor-pointer"
                    onClick={() => navigate('/orders')}
                    data-testid="orders-link"
                  >
                    <Package className="w-4 h-4 mr-2" />
                    My Orders
                  </DropdownMenuItem>
                  <DropdownMenuItem 
                    className="text-[#C0C0C0] hover:text-white hover:bg-white/5 rounded-none cursor-pointer"
                    onClick={() => navigate('/messages')}
                    data-testid="messages-link"
                  >
                    <MessageSquare className="w-4 h-4 mr-2" />
                    Messages
                  </DropdownMenuItem>
                  <DropdownMenuItem 
                    className="text-[#C0C0C0] hover:text-white hover:bg-white/5 rounded-none cursor-pointer"
                    onClick={() => navigate('/referrals')}
                    data-testid="referrals-link"
                  >
                    <Gift className="w-4 h-4 mr-2" />
                    Refer & Earn
                  </DropdownMenuItem>
                  
                  {user.role === 'admin' && (
                    <DropdownMenuItem 
                      className="text-[#C0C0C0] hover:text-white hover:bg-white/5 rounded-none cursor-pointer"
                      onClick={() => navigate('/admin')}
                      data-testid="admin-dashboard-link"
                    >
                      <Shield className="w-4 h-4 mr-2" />
                      Admin Panel
                    </DropdownMenuItem>
                  )}
                  
                  <DropdownMenuSeparator className="bg-white/10" />
                  
                  <DropdownMenuItem 
                    className="text-red-400 hover:text-red-300 hover:bg-white/5 rounded-none cursor-pointer"
                    onClick={handleLogout}
                    data-testid="logout-button"
                  >
                    <LogOut className="w-4 h-4 mr-2" />
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              </>
            ) : (
              <div className="flex items-center gap-3">
                <Link to="/login">
                  <Button variant="ghost" className="text-[#C0C0C0] hover:text-white hover:bg-white/10 rounded-none" data-testid="login-button">
                    Login
                  </Button>
                </Link>
                <Link to="/register" className="hidden md:block">
                  <Button className="btn-primary text-sm" data-testid="register-button">
                    Sign Up
                  </Button>
                </Link>
              </div>
            )}

            {/* Mobile Menu Toggle */}
            <button 
              className="md:hidden text-white p-2"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              data-testid="mobile-menu-toggle"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden py-4 border-t border-white/10">
            <nav className="flex flex-col gap-4">
              <Link 
                to="/products" 
                className="text-sm text-[#C0C0C0] hover:text-white transition-colors uppercase tracking-wider py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Shop
              </Link>
              <Link 
                to="/brands" 
                className="text-sm text-[#C0C0C0] hover:text-white transition-colors uppercase tracking-wider py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Brands
              </Link>
              <Link 
                to="/apply" 
                className="text-sm text-[#39FF14] hover:text-white transition-colors uppercase tracking-wider py-2"
                onClick={() => setMobileMenuOpen(false)}
              >
                Sell Your Brand
              </Link>
              {!user && (
                <Link to="/register" className="mt-2">
                  <Button className="btn-primary w-full text-sm" onClick={() => setMobileMenuOpen(false)}>
                    Sign Up
                  </Button>
                </Link>
              )}
            </nav>
          </div>
        )}
      </div>
    </header>
  );
}
