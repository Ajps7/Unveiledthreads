import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { Toaster } from "./components/ui/sonner";

// Pages
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import Products from "./pages/Products";
import ProductDetail from "./pages/ProductDetail";
import Brands from "./pages/Brands";
import BrandProfile from "./pages/BrandProfile";
import BrandApplication from "./pages/BrandApplication";
import BrandDashboard from "./pages/BrandDashboard";
import BrandAnalytics from "./pages/BrandAnalytics";
import AddProduct from "./pages/AddProduct";
import MyListings from "./pages/MyListings";
import BoostSuccess from "./pages/BoostSuccess";
import OrderSuccess from "./pages/OrderSuccess";
import MyOrders from "./pages/MyOrders";
import Wishlist from "./pages/Wishlist";
import Referrals from "./pages/Referrals";
import Messages from "./pages/Messages";
import Notifications from "./pages/Notifications";
import Community from "./pages/Community";
import Terms from "./pages/Terms";
import Privacy from "./pages/Privacy";
import Account from "./pages/Account";
import AdminDashboard from "./pages/AdminDashboard";
import CookieBanner from "./components/CookieBanner";

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:id" element={<ProductDetail />} />
            <Route path="/brands" element={<Brands />} />
            <Route path="/brands/:id" element={<BrandProfile />} />
            <Route path="/@:slug" element={<BrandProfile />} />
            <Route path="/apply" element={<BrandApplication />} />
            <Route path="/brand/dashboard" element={<BrandDashboard />} />
            <Route path="/brand/products" element={<MyListings />} />
            <Route path="/brand/add-product" element={<AddProduct />} />
            <Route path="/brand/analytics" element={<BrandAnalytics />} />
            <Route path="/boost/success" element={<BoostSuccess />} />
            <Route path="/order/success" element={<OrderSuccess />} />
            <Route path="/orders" element={<MyOrders />} />
            <Route path="/wishlist" element={<Wishlist />} />
            <Route path="/referrals" element={<Referrals />} />
            <Route path="/messages" element={<Messages />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/community" element={<Community />} />
            <Route path="/terms" element={<Terms />} />
            <Route path="/privacy" element={<Privacy />} />
            <Route path="/account" element={<Account />} />
            <Route path="/admin" element={<AdminDashboard />} />
          </Routes>
          <CookieBanner />
        </BrowserRouter>
        <Toaster />
      </div>
    </AuthProvider>
  );
}

export default App;
