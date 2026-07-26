import { Button } from '../ui/button';
import { ShieldAlert, CheckCircle, XCircle, Loader2 } from 'lucide-react';

/**
 * Admin buyer-protection disputes panel with refund / close actions.
 */
export function AdminDisputesPanel({ disputes, disputeProcessing, onRefund, onClose }) {
  return (
    <div className="mb-12" data-testid="admin-disputes-section">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold uppercase text-white flex items-center gap-2" style={{ fontFamily: 'Clash Display, sans-serif' }}>
          <ShieldAlert className="w-5 h-5 text-yellow-300" />
          Buyer Protection Disputes
        </h2>
        <span
          className="text-xs uppercase tracking-wider px-3 py-1 bg-yellow-500/10 text-yellow-300 border border-yellow-500/30"
          data-testid="open-disputes-count"
        >
          {disputes.length} open
        </span>
      </div>
      {disputes.length === 0 ? (
        <div className="border border-white/10 bg-[#0A0A0A] p-8 text-center">
          <ShieldAlert className="w-8 h-8 text-[#39FF14]/30 mx-auto mb-3" />
          <p className="text-[#9CA3AF] text-sm">No open disputes — nice and quiet.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {disputes.map((d) => {
            const order = d.order_summary || {};
            return (
              <div key={d.id} className="border border-yellow-500/30 bg-yellow-500/5 p-5" data-testid={`dispute-${d.id}`}>
                <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                  <div>
                    <p className="text-xs uppercase tracking-wider text-yellow-300 font-bold mb-1">
                      Non-delivery dispute
                    </p>
                    <p className="text-white font-bold">{order.product_name || 'Unknown product'}</p>
                    <p className="text-xs text-[#9CA3AF]">
                      £{Number(order.total_price || 0).toFixed(2)} · {d.brand_name || 'Unknown brand'} · Order #{d.order_id.slice(-6)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF]">Filed</p>
                    <p className="text-xs text-white">
                      {new Date(d.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>

                <div className="bg-[#0F0F0F] border border-white/5 p-3 mb-3">
                  <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-1">Buyer says</p>
                  <p className="text-sm text-white whitespace-pre-wrap">{d.buyer_message}</p>
                </div>

                <div className="grid grid-cols-2 gap-3 text-xs mb-4">
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF]">Shipping status</p>
                    <p className="text-white">{order.shipping_status || 'unknown'}</p>
                  </div>
                  <div>
                    <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF]">Tracking</p>
                    <p className="text-white">
                      {order.tracking_number
                        ? `${order.courier || ''} ${order.tracking_number}`
                        : <span className="text-yellow-300">None entered</span>}
                    </p>
                  </div>
                </div>

                <div className="flex gap-2 flex-wrap">
                  <Button
                    className="btn-primary text-sm py-2"
                    onClick={() => onRefund(d.id)}
                    disabled={disputeProcessing === d.id}
                    data-testid={`refund-dispute-${d.id}`}
                  >
                    {disputeProcessing === d.id ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <CheckCircle className="w-4 h-4 mr-1" />
                    )}
                    Refund Buyer
                  </Button>
                  <Button
                    className="btn-secondary text-sm py-2 text-red-400 hover:text-red-300"
                    onClick={() => onClose(d.id)}
                    disabled={disputeProcessing === d.id}
                    data-testid={`close-dispute-${d.id}`}
                  >
                    <XCircle className="w-4 h-4 mr-1" />
                    Close Without Refund
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
