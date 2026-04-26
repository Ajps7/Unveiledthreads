import Header from '../components/Header';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function Terms() {
  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-12">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to home
        </Link>

        <h1 className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-2 text-white" style={{ fontFamily: 'Clash Display, sans-serif' }} data-testid="terms-title">
          TERMS & CONDITIONS
        </h1>
        <p className="text-sm text-[#9CA3AF] mb-10">Last updated: April 2026</p>

        <div className="space-y-10 text-[#C0C0C0] text-sm leading-relaxed">

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>1. About Unveiled Threads</h2>
            <p>Unveiled Threads ("the Platform", "we", "us") is an online marketplace operated in the United Kingdom that connects independent streetwear brands ("Sellers", "Brands") with buyers ("Buyers", "Customers"). By accessing or using the Platform, you agree to be bound by these Terms & Conditions.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>2. Eligibility</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>You must be at least 18 years old to create an account or make purchases.</li>
              <li>By registering, you confirm that all information provided is accurate and up to date.</li>
              <li>Seller accounts are subject to application review and approval by our admin team.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>3. Accounts</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>You are responsible for maintaining the confidentiality of your account credentials.</li>
              <li>You must not share your account with others or create multiple accounts.</li>
              <li>We reserve the right to suspend or terminate accounts that violate these terms.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>4. Seller Terms</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Sellers must be UK-based and sell authentic streetwear products only.</li>
              <li>All product listings must include accurate descriptions, images, pricing, sizing, and stock information.</li>
              <li>Sellers are responsible for fulfilling orders, providing tracking information, and shipping items within a reasonable timeframe.</li>
              <li>Product images must be clear, well-lit, and accurately represent the item being sold.</li>
              <li>Counterfeit, stolen, or prohibited goods are strictly forbidden and will result in immediate account termination.</li>
              <li>Sellers must not attempt to redirect transactions off-platform.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>5. Buyer Terms</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>All purchases are made directly through the Platform's secure checkout powered by Stripe.</li>
              <li>Buyers are responsible for reviewing product details, sizing, and descriptions before purchasing.</li>
              <li>Once an order is placed and payment is confirmed, the Seller is notified and expected to ship the item.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>6. Pricing & Fees</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>All prices are listed in GBP (£) and are set by the Seller.</li>
              <li>A <span className="text-white font-medium">4% platform fee</span> is added to each transaction. This fee supports the operation and development of Unveiled Threads.</li>
              <li>Shipping costs are set per product by the Seller and displayed at checkout.</li>
              <li>The total amount charged to the Buyer includes: product price + platform fee + shipping cost.</li>
              <li>Sellers receive the product price plus shipping cost; the platform retains the 4% fee.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>7. Boosted Brand Promotions</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Sellers may purchase promotional "Boost" packages to increase brand visibility on the Platform.</li>
              <li>Boost packages are non-refundable once activated.</li>
              <li>Featured placement does not guarantee sales or a specific number of views.</li>
              <li>Boost packages are available in Weekly (£9.99), Monthly (£29.99), and Quarterly (£69.99) tiers.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>8. Payments & Refunds</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>All payments are processed securely through Stripe. We do not store card details.</li>
              <li>Refund requests must be raised within 14 days of delivery.</li>
              <li>Refunds are at the discretion of the Seller, in accordance with UK Consumer Rights Act 2015.</li>
              <li>The Platform may mediate disputes between Buyers and Sellers at its discretion.</li>
              <li>In the event of a refund, the platform fee is non-refundable.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>9. Shipping & Delivery</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Sellers are responsible for dispatching orders and providing valid tracking information.</li>
              <li>Shipping is managed directly by the Seller via their chosen courier (Royal Mail, Evri, DPD, etc.).</li>
              <li>Unveiled Threads is not liable for delays, damage, or loss during transit.</li>
              <li>Buyers can track their orders via the "My Orders" page.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>10. Community & Messaging</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Users must treat all members of the community with respect.</li>
              <li>Abusive, hateful, discriminatory, or threatening content is strictly prohibited.</li>
              <li>Messages are automatically scanned for prohibited content including: attempts to exchange personal contact details (phone numbers, emails), redirect transactions off-platform (PayPal, Venmo, bank transfers), or share external links.</li>
              <li>Violations may result in message removal, account warnings, or permanent suspension.</li>
              <li>Community posts and product comments are publicly visible and subject to moderation.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>11. Referral Programme</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Users may refer others using a unique referral code.</li>
              <li>Referral credits (£5) are awarded when the referred user completes their first purchase.</li>
              <li>Credits are non-transferable and have no cash value.</li>
              <li>Abuse of the referral programme (e.g. self-referrals, fake accounts) will result in credit forfeiture and potential account suspension.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>12. Intellectual Property</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Sellers retain ownership of their brand names, logos, and product designs.</li>
              <li>By listing on Unveiled Threads, Sellers grant us a non-exclusive licence to display their content on the Platform for promotional purposes.</li>
              <li>The Unveiled Threads name, logo, and design are the intellectual property of the Platform.</li>
              <li>Users must not copy, reproduce, or redistribute Platform content without permission.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>13. Privacy & Data</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>We collect and process personal data in accordance with the UK General Data Protection Regulation (UK GDPR) and the Data Protection Act 2018.</li>
              <li>Personal data is used solely for operating the Platform, processing orders, and sending relevant notifications.</li>
              <li>We do not sell personal data to third parties.</li>
              <li>Users may request access to, correction of, or deletion of their personal data by contacting us.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>14. Limitation of Liability</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>Unveiled Threads acts as a marketplace facilitator and is not a party to transactions between Buyers and Sellers.</li>
              <li>We are not liable for the quality, safety, legality, or accuracy of items listed by Sellers.</li>
              <li>To the fullest extent permitted by law, our liability is limited to the platform fees collected in relation to any disputed transaction.</li>
              <li>We do not guarantee uninterrupted or error-free access to the Platform.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>15. Termination</h2>
            <ul className="list-disc pl-5 space-y-2">
              <li>We reserve the right to suspend or terminate any account at our discretion, particularly in cases of fraud, policy violations, or abuse.</li>
              <li>Users may delete their account at any time. Outstanding orders must be fulfilled before closure.</li>
              <li>Upon termination, all active listings will be removed from the Platform.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>16. Governing Law</h2>
            <p>These Terms & Conditions are governed by and construed in accordance with the laws of England and Wales. Any disputes shall be subject to the exclusive jurisdiction of the courts of England and Wales.</p>
          </section>

          <section>
            <h2 className="text-lg font-bold text-white uppercase mb-3" style={{ fontFamily: 'Clash Display, sans-serif' }}>17. Changes to Terms</h2>
            <p>We may update these Terms & Conditions from time to time. Continued use of the Platform after changes constitutes acceptance of the revised terms. We will notify registered users of significant changes via email or in-app notification.</p>
          </section>

          <section className="border-t border-white/10 pt-8">
            <p className="text-[#9CA3AF]">
              If you have any questions about these Terms & Conditions, please contact us through the Platform's messaging system or email us at support@unveiledthreads.uk.
            </p>
          </section>
        </div>
      </div>
    </div>
  );
}
