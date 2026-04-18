import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { Toaster } from "./components/ui/sonner";

// Pages
import Home from "./pages/Home";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Products from "./pages/Products";
import ProductDetail from "./pages/ProductDetail";
import Brands from "./pages/Brands";
import BrandProfile from "./pages/BrandProfile";
import BrandApplication from "./pages/BrandApplication";
import BrandDashboard from "./pages/BrandDashboard";
import BrandAnalytics from "./pages/BrandAnalytics";
import BoostSuccess from "./pages/BoostSuccess";
import OrderSuccess from "./pages/OrderSuccess";
import MyOrders from "./pages/MyOrders";
import Wishlist from "./pages/Wishlist";
import Referrals from "./pages/Referrals";
import Messages from "./pages/Messages";
import AdminDashboard from "./pages/AdminDashboard";

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/products" element={<Products />} />
            <Route path="/products/:id" element={<ProductDetail />} />
            <Route path="/brands" element={<Brands />} />
            <Route path="/brands/:id" element={<BrandProfile />} />
            <Route path="/apply" element={<BrandApplication />} />
            <Route path="/brand/dashboard" element={<BrandDashboard />} />
            <Route path="/brand/products" element={<BrandDashboard />} />
            <Route path="/brand/analytics" element={<BrandAnalytics />} />
            <Route path="/boost/success" element={<BoostSuccess />} />
            <Route path="/order/success" element={<OrderSuccess />} />
            <Route path="/orders" element={<MyOrders />} />
            <Route path="/wishlist" element={<Wishlist />} />
            <Route path="/referrals" element={<Referrals />} />
            <Route path="/messages" element={<Messages />} />
            <Route path="/admin" element={<AdminDashboard />} />
          </Routes>
        </BrowserRouter>
        <Toaster />
      </div>
    </AuthProvider>
  );
}

export default App;
