import Header from '../components/Header';
import { Link } from 'react-router-dom';
import { ArrowLeft, Shield, Lock, Mail, Trash2 } from 'lucide-react';

const SectionHeading = ({ children }) => (
  <h2
    className="text-lg font-bold text-white uppercase mb-3 mt-10"
    style={{ fontFamily: 'Clash Display, sans-serif' }}
  >
    {children}
  </h2>
);

const SubHeading = ({ children }) => (
  <h3 className="text-sm font-bold text-[#39FF14] uppercase tracking-wider mb-2 mt-5">
    {children}
  </h3>
);

const P = ({ children }) => (
  <p className="text-sm text-[#C0C0C0] leading-relaxed mb-3">{children}</p>
);

const Bullet = ({ children }) => (
  <li className="text-sm text-[#C0C0C0] leading-relaxed mb-2 pl-2">{children}</li>
);

export default function Privacy() {
  return (
    <div className="min-h-screen bg-[#050505]" data-testid="privacy-page">
      <Header />
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-12">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to home
        </Link>

        <div className="flex items-center gap-3 mb-3">
          <Shield className="w-6 h-6 text-[#39FF14]" />
          <p className="text-xs uppercase tracking-[0.3em] text-[#39FF14]">UK GDPR / Data Protection Act 2018</p>
        </div>

        <h1
          className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-2 text-white"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
          data-testid="privacy-title"
        >
          PRIVACY POLICY
        </h1>
        <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-10">
          Last updated: February 2026 · Version 1.0
        </p>

        <div className="border border-[#39FF14]/30 bg-[#39FF14]/5 p-4 mb-8">
          <p className="text-sm text-[#C0C0C0] leading-relaxed">
            <span className="text-[#39FF14] font-bold">In short:</span> we only collect what we need to run the marketplace,
            we never sell your data, your payment details live with Stripe (not us), and you can export or delete your
            account at any time from your account settings.
          </p>
        </div>

        {/* 1 */}
        <SectionHeading>1. Who we are</SectionHeading>
        <P>
          Unveiled Threads ("we", "us", "our") is a UK-based online marketplace connecting small and medium
          clothing brands with buyers. For the purposes of UK GDPR and the Data Protection Act 2018, we are
          the <span className="text-white font-semibold">Data Controller</span> of the personal data described in this notice.
        </P>
        <P>
          If you have any questions about this policy or your data, contact us at{' '}
          <a href="mailto:privacy@unveiledthreads.co.uk" className="text-[#39FF14] hover:underline">
            privacy@unveiledthreads.co.uk
          </a>.
        </P>

        {/* 2 */}
        <SectionHeading>2. What data we collect</SectionHeading>

        <SubHeading>Account data</SubHeading>
        <ul className="list-disc list-inside mb-4">
          <Bullet>Your name and email address</Bullet>
          <Bullet>A securely hashed password (we never see your raw password)</Bullet>
          <Bullet>The role attached to your account (buyer / brand / admin)</Bullet>
        </ul>

        <SubHeading>Brand application data (sellers only)</SubHeading>
        <ul className="list-disc list-inside mb-4">
          <Bullet>Brand name, business description, website &amp; social handles</Bullet>
          <Bullet>Business email address</Bullet>
        </ul>

        <SubHeading>Order &amp; transaction data</SubHeading>
        <ul className="list-disc list-inside mb-4">
          <Bullet>Shipping address you provide at checkout</Bullet>
          <Bullet>Product, price, quantity and order status</Bullet>
          <Bullet>Tracking number and courier (when provided by the seller)</Bullet>
        </ul>

        <SubHeading>Payment data</SubHeading>
        <P>
          <span className="text-white font-semibold">We do not store card numbers, CVV, bank details or KYC documents.</span>{' '}
          All payments are processed by Stripe Inc. (PCI-DSS Level 1 certified). When a seller signs up to receive
          payouts, identity verification documents are submitted directly to Stripe — they never touch our servers.
        </P>

        <SubHeading>Communications data</SubHeading>
        <ul className="list-disc list-inside mb-4">
          <Bullet>Messages you send to other users via the in-app messaging system</Bullet>
          <Bullet>Community posts and comments you publish on the platform</Bullet>
          <Bullet>Reviews you leave for purchases</Bullet>
        </ul>

        <SubHeading>Technical data</SubHeading>
        <ul className="list-disc list-inside mb-4">
          <Bullet>IP address (for rate-limiting and security only)</Bullet>
          <Bullet>Browser type and basic device information</Bullet>
          <Bullet>Strictly necessary session cookies (no advertising trackers)</Bullet>
        </ul>

        {/* 3 */}
        <SectionHeading>3. Why we use your data &amp; legal basis</SectionHeading>
        <ul className="list-disc list-inside mb-4">
          <Bullet><b>Contract</b> — to run your account, process orders and connect you with sellers.</Bullet>
          <Bullet><b>Legitimate interest</b> — to keep the platform secure, prevent fraud, detect off-platform sales, and improve the service.</Bullet>
          <Bullet><b>Legal obligation</b> — to keep transaction records for tax and accounting purposes (typically 6 years under UK HMRC rules).</Bullet>
          <Bullet><b>Consent</b> — for any future marketing emails (you opt in, you can opt out anytime).</Bullet>
        </ul>

        {/* 4 */}
        <SectionHeading>4. Who we share data with</SectionHeading>
        <P>We only share personal data with carefully chosen processors who help us run the service:</P>
        <ul className="list-disc list-inside mb-4">
          <Bullet><b>Stripe Inc.</b> — payment processing and seller KYC (US/EU, GDPR-compliant)</Bullet>
          <Bullet><b>Resend</b> — transactional email delivery</Bullet>
          <Bullet><b>MongoDB Atlas</b> — encrypted database hosting (EU region)</Bullet>
          <Bullet><b>Anthropic (Claude)</b> — automated content moderation only (messages are scanned, not stored by the AI)</Bullet>
          <Bullet><b>Sellers</b> — when you place an order, the seller receives your name, shipping address and order details so they can fulfil the order</Bullet>
        </ul>
        <P>
          <span className="text-white font-semibold">We do not sell your personal data and we do not share it with advertising networks.</span>
        </P>

        {/* 5 */}
        <SectionHeading>5. How long we keep your data</SectionHeading>
        <ul className="list-disc list-inside mb-4">
          <Bullet><b>Account data</b> — while your account is active, then deleted on request</Bullet>
          <Bullet><b>Order records</b> — anonymised after account deletion, retained for up to 6 years for HMRC</Bullet>
          <Bullet><b>Messages</b> — retained while the conversation exists, redacted on account deletion</Bullet>
          <Bullet><b>Password reset tokens</b> — 1 hour, then invalidated</Bullet>
          <Bullet><b>Server logs</b> — 30 days max</Bullet>
        </ul>

        {/* 6 */}
        <SectionHeading>6. Your rights</SectionHeading>
        <P>Under UK GDPR you have the following rights, free of charge, at any time:</P>
        <ul className="list-disc list-inside mb-4">
          <Bullet><b>Right of access</b> — see what data we hold (Account → Export My Data)</Bullet>
          <Bullet><b>Right to portability</b> — download a copy in JSON format</Bullet>
          <Bullet><b>Right to rectification</b> — fix incorrect data via account settings or email us</Bullet>
          <Bullet><b>Right to erasure</b> — delete your account permanently (Account → Delete Account)</Bullet>
          <Bullet><b>Right to object / restrict processing</b> — email us at privacy@unveiledthreads.co.uk</Bullet>
          <Bullet><b>Right to complain</b> — to the UK Information Commissioner's Office at <a href="https://ico.org.uk" target="_blank" rel="noreferrer" className="text-[#39FF14] hover:underline">ico.org.uk</a></Bullet>
        </ul>

        <div className="border border-[#39FF14]/30 bg-[#39FF14]/5 p-4 mt-4 mb-6">
          <div className="flex items-start gap-3">
            <Trash2 className="w-5 h-5 text-[#39FF14] flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm text-white font-semibold mb-1">Want to export or delete your data right now?</p>
              <p className="text-sm text-[#C0C0C0]">
                Go to{' '}
                <Link to="/account" className="text-[#39FF14] hover:underline" data-testid="privacy-account-link">
                  Account Settings
                </Link>{' '}
                — both happen instantly with no email back-and-forth.
              </p>
            </div>
          </div>
        </div>

        {/* 7 */}
        <SectionHeading>7. Cookies</SectionHeading>
        <P>
          We use a single category of cookies: <span className="text-white font-semibold">strictly necessary cookies</span> for
          authentication (your secure session token) and CSRF protection. We do not use advertising, analytics or
          tracking cookies. Because these cookies are essential for the site to function, no consent is required
          under PECR — but we still show you a banner so you know they're there.
        </P>

        {/* 8 */}
        <SectionHeading>8. Security</SectionHeading>
        <ul className="list-disc list-inside mb-4">
          <Bullet>All traffic is encrypted via TLS 1.2+</Bullet>
          <Bullet>Passwords are hashed with bcrypt (industry standard)</Bullet>
          <Bullet>Card and bank data never reach our servers</Bullet>
          <Bullet>Rate-limiting and account enumeration protection on auth endpoints</Bullet>
          <Bullet>Production secrets are stored in deployment environment variables, never in code</Bullet>
        </ul>

        {/* 9 */}
        <SectionHeading>9. International transfers</SectionHeading>
        <P>
          Some of our processors (Stripe, Resend, Anthropic) may process data outside the UK/EEA. Where this happens
          we rely on Standard Contractual Clauses (SCCs) and equivalent UK transfer mechanisms approved by the ICO.
        </P>

        {/* 10 */}
        <SectionHeading>10. Children</SectionHeading>
        <P>
          Unveiled Threads is not directed at anyone under 16. If you believe we've collected data about a child,
          email us and we will delete it immediately.
        </P>

        {/* 11 */}
        <SectionHeading>11. Changes to this policy</SectionHeading>
        <P>
          If we make material changes we'll update this page and notify active users by email. Continued use of
          the service after an update means you accept the revised policy.
        </P>

        {/* 12 */}
        <SectionHeading>12. Contact</SectionHeading>
        <div className="flex items-center gap-3 mb-3">
          <Mail className="w-4 h-4 text-[#39FF14]" />
          <a href="mailto:privacy@unveiledthreads.co.uk" className="text-sm text-[#39FF14] hover:underline">
            privacy@unveiledthreads.co.uk
          </a>
        </div>
        <div className="flex items-center gap-3 mb-12">
          <Lock className="w-4 h-4 text-[#39FF14]" />
          <span className="text-sm text-[#C0C0C0]">
            ICO complaints: <a href="https://ico.org.uk/make-a-complaint" target="_blank" rel="noreferrer" className="text-[#39FF14] hover:underline">ico.org.uk/make-a-complaint</a>
          </span>
        </div>

        <div className="border-t border-white/10 pt-6 text-xs text-[#9CA3AF]">
          <p>
            This Privacy Policy works alongside our{' '}
            <Link to="/terms" className="text-[#39FF14] hover:underline">Terms &amp; Conditions</Link>.
            Together they govern your use of Unveiled Threads.
          </p>
        </div>
      </div>
    </div>
  );
}
