import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Tag } from 'lucide-react';

/**
 * "Move to Dead Stock" confirmation modal.
 */
export function MoveToDeadStockDialog({ dialog, price, setPrice, moving, onConfirm, onClose }) {
  return (
    <Dialog open={!!dialog} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="bg-[#0F0F0F] border-white/10 rounded-none max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-white uppercase flex items-center gap-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            <Tag className="w-5 h-5 text-[#39FF14]" /> Move to Dead Stock
          </DialogTitle>
        </DialogHeader>
        {dialog?.product && (
          <div className="space-y-4 mt-4">
            <div className="border border-white/10 bg-[#0A0A0A] p-3">
              <p className="text-xs uppercase tracking-wider text-[#9CA3AF] mb-1">Product</p>
              <p className="text-white text-sm">{dialog.product.name}</p>
              <p className="text-xs text-[#9CA3AF] mt-1">Current price: £{dialog.product.price.toFixed(2)}</p>
            </div>
            <div>
              <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">
                New Dead Stock Price (£)
              </label>
              <Input
                type="number"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="input-brutalist"
                data-testid="dead-stock-price-input"
                placeholder="Leave as current to keep price the same"
              />
              <p className="text-xs text-[#9CA3AF] mt-2">
                The original price (£{dialog.product.price.toFixed(2)}) will be shown alongside the new one with a
                &quot;-X%&quot; badge so buyers can see the saving. Set the same price to keep it unchanged.
              </p>
            </div>
            <div className="flex gap-3 pt-2">
              <Button
                className="btn-primary flex-1"
                onClick={onConfirm}
                disabled={moving}
                data-testid="confirm-dead-stock-button"
              >
                {moving ? 'Moving…' : 'Move to Dead Stock'}
              </Button>
              <Button className="btn-secondary" onClick={onClose}>Cancel</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
