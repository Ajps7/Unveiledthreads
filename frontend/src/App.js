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
import BoostSuccess from "./pages/BoostSuccess";
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
            <Route path="/boost/success" element={<BoostSuccess />} />
            <Route path="/admin" element={<AdminDashboard />} />
          </Routes>
        </BrowserRouter>
        <Toaster />
      </div>
    </AuthProvider>
  );
}

export default App;
