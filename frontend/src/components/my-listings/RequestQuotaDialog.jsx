import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { Button } from '../ui/button';

/**
 * "Request more Dead Stock slots" modal.
 */
export function RequestQuotaDialog({ open, onOpenChange, quota, requestedQuota, setRequestedQuota, reason, setReason, onSubmit }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-[#0F0F0F] border-white/10 rounded-none max-w-md">
        <DialogHeader>
          <DialogTitle className="text-xl font-bold text-white uppercase" style={{ fontFamily: 'Clash Display, sans-serif' }}>
            Request More Slots
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4 mt-4">
          <p className="text-sm text-[#9CA3AF]">
            Default Dead Stock cap is <span className="text-white font-semibold">{quota?.quota || 10}</span> items.
            Ask the admin team for more if you&apos;ve got a bigger archive to shift.
          </p>
          <div>
            <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">
              Requested quota
            </label>
            <Input
              type="number"
              value={requestedQuota}
              onChange={(e) => setRequestedQuota(e.target.value)}
              className="input-brutalist"
              data-testid="requested-quota-input"
              min={(quota?.quota || 10) + 1}
              max={200}
            />
          </div>
          <div>
            <label className="block text-xs text-[#C0C0C0] uppercase tracking-wider mb-1">
              Reason (optional)
            </label>
            <Textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="input-brutalist min-h-[80px] resize-none"
              placeholder="e.g. clearing out three past collections..."
              data-testid="quota-reason-input"
            />
          </div>
          <div className="flex gap-3 pt-2">
            <Button className="btn-primary flex-1" onClick={onSubmit} data-testid="submit-quota-request-button">
              Submit Request
            </Button>
            <Button className="btn-secondary" onClick={() => onOpenChange(false)}>Cancel</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
