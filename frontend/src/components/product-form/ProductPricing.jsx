import { Input } from '../ui/input';
import { calcBuyerFee } from '../../lib/fees';

/**
 * Price / shipping / stock inputs + live "buyer sees" preview.
 */
export function ProductPricing({ form, setForm }) {
  return (
    <div className="border border-white/10 bg-[#0A0A0A] p-6 mb-6">
      <h2 className="text-lg font-bold text-white uppercase mb-4" style={{ fontFamily: 'Clash Display, sans-serif' }}>
        Pricing & Stock
      </h2>

      <div className="grid md:grid-cols-3 gap-5">
        <div>
          <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
            Price (£) *
          </label>
          <Input
            type="number"
            step="0.01"
            min="0.01"
            value={form.price}
            onChange={(e) => setForm({ ...form, price: e.target.value })}
            className="input-brutalist"
            placeholder="49.99"
            data-testid="product-price-input"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
            Shipping Cost (£)
          </label>
          <Input
            type="number"
            step="0.01"
            min="0"
            value={form.shipping_cost}
            onChange={(e) => setForm({ ...form, shipping_cost: e.target.value })}
            className="input-brutalist"
            placeholder="3.99"
            data-testid="product-shipping-input"
          />
          <p className="text-xs text-[#9CA3AF] mt-1">Set to 0 for free shipping</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-[#C0C0C0] uppercase tracking-wider mb-2">
            Total Stock *
          </label>
          <Input
            type="number"
            min="1"
            value={form.stock}
            onChange={(e) => setForm({ ...form, stock: e.target.value })}
            className="input-brutalist"
            placeholder="50"
            data-testid="product-stock-input"
          />
        </div>
      </div>

      {form.price && (
        <div className="mt-5 p-4 bg-[#0F0F0F] border border-white/5">
          <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-2">Buyer sees</p>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white">£{parseFloat(form.price || 0).toFixed(2)}</span>
            <span className="text-sm text-[#9CA3AF]">
              + £{calcBuyerFee(parseFloat(form.price || 0)).toFixed(2)} Buyer Protection fee
              {parseFloat(form.shipping_cost || 0) > 0
                ? ` + £${parseFloat(form.shipping_cost).toFixed(2)} shipping`
                : ' + free shipping'}
            </span>
          </div>
          <p className="text-xs text-[#39FF14] mt-1">
            You receive: £{(parseFloat(form.price || 0) + parseFloat(form.shipping_cost || 0)).toFixed(2)} per sale
          </p>
        </div>
      )}
    </div>
  );
}
