import { Button } from '../ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

/**
 * Admin brand-applications panel: risk-scored queue with approve/reject actions.
 */
export function AdminApplicationsPanel({
  applications,
  statusFilter,
  setStatusFilter,
  processing,
  onApprove,
  onReject,
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold uppercase text-white" style={{ fontFamily: 'Clash Display, sans-serif' }}>
          Brand Applications
        </h2>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[140px] bg-transparent border-white/20 rounded-none text-white" data-testid="status-filter">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-[#0F0F0F] border-white/10 rounded-none">
            <SelectItem value="pending" className="text-white hover:bg-white/10 rounded-none">Pending</SelectItem>
            <SelectItem value="waitlisted" className="text-white hover:bg-white/10 rounded-none">Waitlisted</SelectItem>
            <SelectItem value="approved" className="text-white hover:bg-white/10 rounded-none">Approved</SelectItem>
            <SelectItem value="rejected" className="text-white hover:bg-white/10 rounded-none">Rejected</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-4" data-testid="applications-list">
        {applications.length > 0 ? (
          applications.map((app) => {
            const score = app.risk_score ?? 0;
            const riskTier = score >= 50 ? 'high' : score >= 20 ? 'medium' : 'low';
            const riskColour = {
              high: 'bg-red-500/10 text-red-400 border-red-500/40',
              medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/40',
              low: 'bg-green-500/10 text-green-400 border-green-500/40',
            }[riskTier];
            return (
              <div key={app.id} className="border border-white/10 bg-[#0A0A0A] p-4">
                <div className="flex items-start justify-between mb-3 gap-3">
                  <div className="flex-1">
                    <h3 className="text-white font-bold">{app.brand_name}</h3>
                    <p className="text-xs text-[#9CA3AF]">{app.user?.email}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span
                      className={`text-xs uppercase tracking-wider px-2 py-1 ${
                        app.status === 'pending'
                          ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30'
                          : app.status === 'approved'
                          ? 'bg-green-500/10 text-green-400 border border-green-500/30'
                          : 'bg-red-500/10 text-red-400 border border-red-500/30'
                      }`}
                    >
                      {app.status}
                    </span>
                    <span
                      className={`text-[10px] uppercase tracking-wider px-2 py-1 border ${riskColour}`}
                      title={`Risk score: ${score}`}
                      data-testid={`risk-badge-${app.id}`}
                    >
                      Risk {score} · {riskTier}
                    </span>
                    {app.auto_approved && (
                      <span className="text-[10px] uppercase tracking-wider px-2 py-1 border bg-[#39FF14]/10 text-[#39FF14] border-[#39FF14]/30">
                        Auto-approved
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-sm text-[#9CA3AF] mb-3 line-clamp-2">{app.description}</p>
                <div className="flex flex-wrap gap-2 mb-3 text-xs text-[#C0C0C0]">
                  <span>{app.location}</span>
                  <span>•</span>
                  <span className="capitalize">{app.category}</span>
                </div>
                {app.risk_reasons && app.risk_reasons.length > 0 && (
                  <div className="mb-3 p-2 bg-[#0F0F0F] border border-white/5">
                    <p className="text-[10px] uppercase tracking-wider text-[#9CA3AF] mb-1">Risk flags</p>
                    <ul className="text-xs text-yellow-300 list-disc list-inside space-y-0.5">
                      {app.risk_reasons.map((r) => (
                        <li key={r}>{r.replace(/_/g, ' ')}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {app.status === 'pending' && (
                  <div className="flex gap-2">
                    <Button
                      className="btn-primary flex-1 text-sm py-2"
                      onClick={() => onApprove(app.id)}
                      disabled={processing === app.id}
                      data-testid={`approve-${app.id}`}
                    >
                      {processing === app.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <CheckCircle className="w-4 h-4 mr-1" />
                      )}
                      Approve
                    </Button>
                    <Button
                      className="btn-secondary flex-1 text-sm py-2 text-red-400 hover:text-red-300"
                      onClick={() => onReject(app.id)}
                      disabled={processing === app.id}
                      data-testid={`reject-${app.id}`}
                    >
                      <XCircle className="w-4 h-4 mr-1" />
                      Reject
                    </Button>
                  </div>
                )}
              </div>
            );
          })
        ) : (
          <div className="border border-white/10 bg-[#0A0A0A] p-8 text-center">
            <p className="text-[#9CA3AF]">No {statusFilter} applications</p>
          </div>
        )}
      </div>
    </div>
  );
}
