import { createContext, useContext, useEffect, useMemo, useState, useCallback } from 'react';

/**
 * Cart state lives in localStorage ONLY (no backend cart table).
 * Single-brand enforced client-side AND server-side.
 *
 * Shape of a cart line:
 *   { product_id, size, top_size, bottom_size, quantity,
 *     // snapshot fields (for UI display before /preview re-prices):
 *     product_name, brand_id, brand_name, image, unit_price, shipping_cost,
 *     is_preorder, preorder_ship_date, listing_type, sizing_mode }
 *
 * `brand_id` + `brand_name` live on the cart root so the UI knows which
 * brand owns the current basket without inspecting every item.
 */

const STORAGE_KEY = 'ut_cart_v1';
const EMPTY = { brand_id: null, brand_name: null, items: [] };

const CartContext = createContext(null);

function read() {
  try {
    const raw = typeof window !== 'undefined' ? window.localStorage.getItem(STORAGE_KEY) : null;
    if (!raw) return { ...EMPTY };
    const parsed = JSON.parse(raw);
    if (!parsed || !Array.isArray(parsed.items)) return { ...EMPTY };
    return parsed;
  } catch (_) {
    return { ...EMPTY };
  }
}

function write(cart) {
  try {
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
    }
  } catch (_) { /* quota — ignore */ }
}

// Two cart lines refer to the SAME SKU (so adding bumps quantity) only
// when every size-identifying field matches exactly. Different sizes of
// the same product live as separate lines.
function sameLine(a, b) {
  return (
    a.product_id === b.product_id &&
    (a.size || null) === (b.size || null) &&
    (a.top_size || null) === (b.top_size || null) &&
    (a.bottom_size || null) === (b.bottom_size || null)
  );
}

export function CartProvider({ children }) {
  const [cart, setCart] = useState(() => read());

  // Keep multiple tabs in sync (best-effort — no server authority).
  useEffect(() => {
    const onStorage = (e) => {
      if (e.key === STORAGE_KEY) setCart(read());
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  useEffect(() => { write(cart); }, [cart]);

  const persist = useCallback((next) => setCart(next), []);

  /**
   * Add a line to the cart.
   * Returns:
   *   { ok: true }
   *   { ok: false, reason: 'different_brand', currentBrandName, incomingBrandName }
   *      — caller shows a confirm dialog and can call replaceWith() to swap.
   */
  const addItem = useCallback((line) => {
    if (!line || !line.product_id || !line.brand_id) {
      return { ok: false, reason: 'invalid' };
    }
    const current = read();
    if (current.brand_id && current.brand_id !== line.brand_id && current.items.length > 0) {
      return {
        ok: false,
        reason: 'different_brand',
        currentBrandName: current.brand_name,
        incomingBrandName: line.brand_name,
        incomingLine: line,
      };
    }
    const existingIdx = current.items.findIndex((it) => sameLine(it, line));
    let items;
    if (existingIdx >= 0) {
      items = current.items.map((it, i) =>
        i === existingIdx ? { ...it, quantity: Math.min((it.quantity || 1) + (line.quantity || 1), 10) } : it
      );
    } else {
      items = [...current.items, { ...line, quantity: line.quantity || 1 }];
    }
    const next = { brand_id: line.brand_id, brand_name: line.brand_name, items };
    persist(next);
    return { ok: true };
  }, [persist]);

  /** Replace the entire cart with a single new line from a different brand. */
  const replaceWith = useCallback((line) => {
    const next = { brand_id: line.brand_id, brand_name: line.brand_name, items: [{ ...line, quantity: line.quantity || 1 }] };
    persist(next);
    return { ok: true };
  }, [persist]);

  const removeItem = useCallback((index) => {
    const current = read();
    const items = current.items.filter((_, i) => i !== index);
    const next = items.length === 0 ? { ...EMPTY } : { ...current, items };
    persist(next);
  }, [persist]);

  const updateQty = useCallback((index, qty) => {
    const current = read();
    const q = Math.max(1, Math.min(10, parseInt(qty, 10) || 1));
    const items = current.items.map((it, i) => (i === index ? { ...it, quantity: q } : it));
    persist({ ...current, items });
  }, [persist]);

  const clearCart = useCallback(() => persist({ ...EMPTY }), [persist]);

  const value = useMemo(() => {
    const count = cart.items.reduce((acc, it) => acc + (it.quantity || 1), 0);
    const subtotal = cart.items.reduce((acc, it) => acc + (it.unit_price || 0) * (it.quantity || 1), 0);
    return {
      cart,
      count,
      subtotalEstimate: subtotal,
      isEmpty: cart.items.length === 0,
      addItem,
      replaceWith,
      removeItem,
      updateQty,
      clearCart,
    };
  }, [cart, addItem, replaceWith, removeItem, updateQty, clearCart]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used within <CartProvider>');
  return ctx;
}
