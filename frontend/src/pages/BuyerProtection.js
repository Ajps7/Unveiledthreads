import { Link } from 'react-router-dom';
import Header from '../components/Header';
import { ShieldCheck, ArrowLeft, AlertCircle, CheckCircle, Clock, Mail } from 'lucide-react';

const SectionHeading = ({ children }) => (
  <h2
    className="text-lg font-bold text-white uppercase mb-3 mt-10"
    style={{ fontFamily: 'Clash Display, sans-serif' }}
  >
    {children}
  </h2>
);

const P = ({ children }) => (
  <p className="text-sm text-[#C0C0C0] leading-relaxed mb-3">{children}</p>
);

const Bullet = ({ children }) => (
  <li className="text-sm text-[#C0C0C0] leading-relaxed mb-2 pl-2">{children}</li>
);

export default function BuyerProtection() {
  return (
    <div className="min-h-screen bg-[#050505]" data-testid="buyer-protection-page">
      <Header />
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-12">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to home
        </Link>

        <div className="flex items-center gap-3 mb-3">
          <ShieldCheck className="w-6 h-6 text-[#39FF14]" />
          <p className="text-xs uppercase tracking-[0.3em] text-[#39FF14]">Trust & Safety</p>
        </div>

        <h1
          className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-2 text-white"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
          data-testid="buyer-protection-title"
        >
          BUYER PROTECTION
        </h1>
        <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-10">
          Last updated: Feb 2026 · Version 1.0 (Non-Delivery cover)
        </p>

        <div className="border border-[#39FF14]/30 bg-[#39FF14]/5 p-5 mb-10">
          <div className="flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-[#39FF14] flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-white font-bold mb-2">In short</p>
              <p className="text-sm text-[#C0C0C0] leading-relaxed">
                If your order doesn&apos;t arrive within 14 days of payment and the seller can&apos;t resolve it,
                we&apos;ll refund you in full. No extra fee, no fine print &mdash; you&apos;re covered automatically
                on every purchase.
              </p>
            </div>
          </div>
        </div>

        {/* What's covered */}
        <SectionHeading>1. What&apos;s covered</SectionHeading>
        <P>
          Unveiled Threads Buyer Protection covers <span className="text-white font-semibold">non-delivery</span> of
          paid orders. You&apos;re eligible for a full refund if:
        </P>
        <ul className="list-disc list-inside mb-4">
          <Bullet>You paid for an order on Unveiled Threads (you&apos;ll see it in your Orders page).</Bullet>
          <Bullet>It&apos;s been <span className="text-white font-semibold">14 days or more</span> since you paid.</Bullet>
          <Bullet>The order has <span className="text-white font-semibold">not been marked as delivered</span>.</Bullet>
          <Bullet>You&apos;ve made a reasonable attempt to contact the seller via in-app messaging.</Bullet>
        </ul>

        {/* Not covered */}
        <SectionHeading>2. What&apos;s not covered (yet)</SectionHeading>
        <P>
          The first version of Buyer Protection is intentionally narrow so we can resolve disputes quickly and fairly.
          The following are <span className="text-white font-semibold">not</span> covered under this policy:
        </P>
        <ul className="list-disc list-inside mb-4">
          <Bullet>Items that arrived but are damaged, faulty or not as described &mdash; these are covered by the Consumer Rights Act 2015 (against the seller directly).</Bullet>
          <Bullet>Change-of-mind returns &mdash; covered by the seller&apos;s own returns policy and the Consumer Contracts Regulations 2013 (14-day cooling-off, against the seller).</Bullet>
          <Bullet>Sizing issues &mdash; check the listing&apos;s size guide and message the brand first.</Bullet>
          <Bullet>Orders where tracking shows delivered, but the parcel was stolen after delivery (this is a courier / police matter).</Bullet>
        </ul>
        <P className="text-xs text-[#9CA3AF]">
          For all of the above, you still have full statutory rights against the seller. Open the order, message the brand,
          and use our admin contact below if you can&apos;t get a response.
        </P>

        {/* How to file */}
        <SectionHeading>3. How to file a dispute</SectionHeading>
        <ol className="list-decimal list-inside space-y-2 mb-4 text-sm text-[#C0C0C0]">
          <li>Go to <Link to="/my-orders" className="text-[#39FF14] hover:underline">My Orders</Link>.</li>
          <li>Find the order &mdash; if you&apos;re eligible, you&apos;ll see a yellow <span className="text-yellow-300 font-bold">&ldquo;Report a problem&rdquo;</span> button.</li>
          <li>Click it, write a short description of what happened, submit.</li>
          <li>You&apos;ll hear back from our team within <span className="text-white font-semibold">3 working days</span>.</li>
        </ol>

        {/* Decision */}
        <SectionHeading>4. How we decide</SectionHeading>
        <P>We check the objective facts attached to the order:</P>
        <ul className="list-disc list-inside mb-4">
          <Bullet>
            <span className="text-white">No tracking number</span> 14+ days after payment → refund issued.
          </Bullet>
          <Bullet>
            <span className="text-white">Tracking shows in transit</span> 14+ days after payment with no movement for 10+ days → refund issued.
          </Bullet>
          <Bullet>
            <span className="text-white">Tracking shows delivered</span> → dispute closed, with a clear reason. You can ask the courier for proof of delivery.
          </Bullet>
          <Bullet>
            <span className="text-white">Seller proves dispatch with proof of postage</span> after the dispute opens → we&apos;ll give the parcel a further reasonable window before refunding.
          </Bullet>
        </ul>

        {/* Process */}
        <SectionHeading>5. How the refund works</SectionHeading>
        <P>
          Refunds are processed through Stripe back to the card you paid with. The funds normally
          appear within <span className="text-white font-semibold">5&ndash;10 working days</span> depending on your bank.
          We claw the money back from the seller&apos;s account &mdash; the buyer is never out of pocket.
        </P>
        <div className="border border-white/10 bg-[#0F0F0F] p-4 mb-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="flex items-start gap-2">
            <Clock className="w-4 h-4 text-[#39FF14] flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-white font-bold mb-1 uppercase tracking-wider">Day 0</p>
              <p className="text-[#9CA3AF]">You file the dispute.</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-yellow-300 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-white font-bold mb-1 uppercase tracking-wider">Day 1&ndash;3</p>
              <p className="text-[#9CA3AF]">We review tracking + seller response.</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <CheckCircle className="w-4 h-4 text-[#39FF14] flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-white font-bold mb-1 uppercase tracking-wider">Day 3&ndash;13</p>
              <p className="text-[#9CA3AF]">Refund appears on your card.</p>
            </div>
          </div>
        </div>

        {/* Sellers */}
        <SectionHeading>6. For sellers</SectionHeading>
        <P>
          If a Buyer Protection refund is issued against one of your orders, the amount is reversed from your
          Stripe balance. You&apos;ll get a notification and the order will be marked as refunded.
        </P>
        <P>
          Repeated non-delivery disputes will affect your standing on the platform and may lead to your brand
          being suspended pending review. The best defence is simple:{' '}
          <span className="text-white">enter a real tracking number as soon as you post the parcel</span>, and reply to buyer messages.
        </P>

        {/* Limits */}
        <SectionHeading>7. Honest limits</SectionHeading>
        <P>
          Unveiled Threads is in MVP. Buyer Protection is currently a manual review by our team, not an automated
          process. Decisions are made in good faith using the data on each order. If you disagree with a decision,
          email <a href="mailto:support@unveiledthreads.co.uk" className="text-[#39FF14] hover:underline">support@unveiledthreads.co.uk</a> within
          14 days and we&apos;ll have a different team member take a second look.
        </P>

        {/* Statutory */}
        <SectionHeading>8. Your statutory rights</SectionHeading>
        <P>
          Nothing in this policy affects your statutory rights under UK law (Consumer Rights Act 2015,
          Consumer Contracts Regulations 2013). For purchases from registered businesses you still have
          a 14-day right to cancel and full faulty-goods protection &mdash; those rights are against the seller,
          and Buyer Protection sits <span className="text-white">on top</span> of them, not instead of them.
        </P>

        <div className="border-t border-white/10 pt-6 mt-10 flex items-center gap-3">
          <Mail className="w-4 h-4 text-[#39FF14]" />
          <a href="mailto:support@unveiledthreads.co.uk" className="text-sm text-[#39FF14] hover:underline">
            support@unveiledthreads.co.uk
          </a>
        </div>
        <p className="text-xs text-[#6B7280] mt-6">
          Unveiled Threads is registered with the UK Information Commissioner&apos;s Office &middot; Reg No. ZC176765
        </p>
      </div>
    </div>
  );
}
