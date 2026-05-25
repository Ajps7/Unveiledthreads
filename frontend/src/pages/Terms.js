import Header from '../components/Header';
import { Link } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, Shield } from 'lucide-react';

// Reusable section header — keeps the brutalist Clash Display look across the doc
const SectionHeading = ({ children }) => (
  <h2
    className="text-lg font-bold text-white uppercase mb-3"
    style={{ fontFamily: 'Clash Display, sans-serif' }}
  >
    {children}
  </h2>
);

const SubHeading = ({ children }) => (
  <h3 className="text-sm font-bold text-[#39FF14] uppercase tracking-wider mb-2 mt-4">
    {children}
  </h3>
);

const Callout = ({ tone, title, children }) => {
  const tones = {
    warning: 'border-yellow-500/30 bg-yellow-500/5 text-yellow-100',
    critical: 'border-red-500/30 bg-red-500/5 text-red-100',
    info: 'border-[#39FF14]/30 bg-[#39FF14]/5 text-[#C0C0C0]',
  };
  const Icon = tone === 'critical' ? AlertTriangle : tone === 'warning' ? AlertTriangle : Shield;
  const labelColours = {
    warning: 'text-yellow-400',
    critical: 'text-red-400',
    info: 'text-[#39FF14]',
  };
  return (
    <div className={`my-5 border p-4 ${tones[tone]}`}>
      <div className={`flex items-center gap-2 mb-2 ${labelColours[tone]}`}>
        <Icon className="w-4 h-4" />
        <p className="text-xs uppercase tracking-[0.2em] font-bold">{title}</p>
      </div>
      <div className="text-sm leading-relaxed">{children}</div>
    </div>
  );
};

export default function Terms() {
  return (
    <div className="min-h-screen bg-[#050505]">
      <Header />
      <div className="max-w-3xl mx-auto px-6 md:px-12 py-12">
        <Link to="/" className="inline-flex items-center gap-2 text-[#9CA3AF] hover:text-white mb-8 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to home
        </Link>

        <h1
          className="text-3xl md:text-4xl font-black tracking-tighter uppercase mb-2 text-white"
          style={{ fontFamily: 'Clash Display, sans-serif' }}
          data-testid="terms-title"
        >
          TERMS &amp; CONDITIONS OF USE
        </h1>
        <p className="text-xs uppercase tracking-[0.2em] text-[#9CA3AF] mb-1">
          Version 2.0 · Last updated April 2026
        </p>
        <p className="text-xs text-[#9CA3AF] mb-6">
          Governed by the Laws of England &amp; Wales
        </p>

        {/* MVP / Demo disclosure — prominent so initial audience is informed */}
        <div className="mb-8 border border-yellow-500/30 bg-yellow-500/5 p-4" data-testid="terms-mvp-notice">
          <p className="text-xs uppercase tracking-[0.2em] text-yellow-400 mb-2 font-bold">MVP / Demo notice</p>
          <p className="text-[#C0C0C0] leading-relaxed text-sm">
            Unveiled Threads is currently operating in an early <strong className="text-white">MVP (Minimum Viable Product) / demo</strong> state.
            While the platform is fully functional — including payments, brand onboarding and order fulfilment — some features may be incomplete,
            change without notice, or be temporarily unavailable while we polish them based on early feedback. We are working closely with our
            first cohort of brands and buyers to build something genuinely useful for the UK independent streetwear scene. By using the Platform
            during this phase, you acknowledge that the experience may evolve quickly and that we reserve the right to refine features, pricing,
            and processes as we learn what works best for our community.
          </p>
        </div>

        <Callout tone="warning" title="Important — please read carefully">
          These Terms &amp; Conditions constitute a legally binding agreement between you and Unveiled Threads Ltd.
          By accessing or using the Platform, you unconditionally accept these terms in their entirety.
          If you do not agree, you must immediately cease all use of the Platform.
        </Callout>

        <div className="space-y-10 text-[#C0C0C0] text-sm leading-relaxed">

          <section>
            <SectionHeading>1. Platform overview &amp; nature of service</SectionHeading>
            <p>
              Unveiled Threads (“the Platform,” “we,” “us,” “our”) is an online marketplace technology platform operated in the United Kingdom that
              provides listing, payment-processing, and communications infrastructure to connect independent streetwear brands (“Sellers”) with
              purchasers (“Buyers”).
            </p>
            <Callout tone="critical" title="Critical disclaimer — marketplace facilitator status">
              Unveiled Threads is solely a technology intermediary and marketplace facilitator. We are <strong>NOT</strong>:
              <ul className="list-disc pl-5 mt-2 space-y-1">
                <li>A party to any contract of sale between a Buyer and a Seller</li>
                <li>An agent, employer, or principal of any Seller</li>
                <li>A retailer, reseller, or distributor of any goods listed on the Platform</li>
                <li>Responsible for the quality, safety, legality, authenticity, or fitness of any goods</li>
              </ul>
              <p className="mt-3">All sales contracts are formed exclusively between the Buyer and the relevant Seller.</p>
            </Callout>
          </section>

          <section>
            <SectionHeading>2. Eligibility &amp; account registration</SectionHeading>
            <SubHeading>2.1 General eligibility</SubHeading>
            <p>
              You must be at least 18 years of age to register, access, or use the Platform. By registering, you represent and warrant that all
              information provided is accurate, complete, current, and not misleading. You are solely responsible for any consequences arising
              from inaccurate or false registration information.
            </p>
            <SubHeading>2.2 Seller eligibility</SubHeading>
            <p>
              Sellers must be UK-based and legally authorised to sell the goods they list. Seller accounts are subject to application review at
              our sole discretion. Approval does not constitute endorsement of any Seller or their products. We reserve the right to refuse or
              revoke Seller status without reason and without liability.
            </p>
          </section>

          <section>
            <SectionHeading>3. Account security &amp; responsibilities</SectionHeading>
            <p>
              You are solely responsible for maintaining the confidentiality and security of your login credentials. All activity conducted
              through your account is your sole responsibility, whether or not authorised by you. You must not share, transfer, or sell your
              account, nor create multiple accounts. You must notify us immediately at{' '}
              <a href="mailto:legal@unveiledthreads.co.uk" className="text-[#39FF14] hover:underline">legal@unveiledthreads.co.uk</a>{' '}
              upon becoming aware of any unauthorised access or security breach. We are not liable for any loss or damage arising from your
              failure to maintain account security.
            </p>
          </section>

          <section>
            <SectionHeading>4. Seller obligations &amp; warranties</SectionHeading>
            <SubHeading>4.1 Product listings</SubHeading>
            <p>
              Sellers must only list authentic goods for which they hold full title and right to sell. All listings must include accurate,
              non-misleading descriptions, images, pricing, sizing, and stock levels. Sellers warrant that all listed goods comply with all
              applicable UK laws, regulations, and trading standards. Counterfeit, stolen, prohibited, or restricted goods are strictly forbidden
              and will result in immediate account termination and referral to law enforcement where appropriate.
            </p>
            <SubHeading>4.2 Fulfilment obligations</SubHeading>
            <p>
              Sellers are solely responsible for order fulfilment, packaging, dispatch, and providing valid tracking information. Sellers must
              dispatch items within the timeframe stated in their listing, and in any event within 5 business days of payment confirmation.
              Failure to fulfil orders without reasonable justification may result in account suspension, financial penalties, and liability to
              the relevant Buyer.
            </p>
            <SubHeading>4.3 Seller indemnity</SubHeading>
            <p>
              Sellers agree to fully indemnify, defend, and hold harmless Unveiled Threads, its directors, officers, employees, and agents from
              and against any and all claims, damages, losses, liabilities, costs, and expenses (including legal fees) arising from:
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>Any goods or services offered or sold by the Seller</li>
              <li>Any breach of these Terms by the Seller</li>
              <li>Any infringement of third-party intellectual property rights</li>
              <li>Any claim by a Buyer or third party relating to a Seller’s products</li>
              <li>Any regulatory action or fine resulting from Seller conduct</li>
            </ul>
          </section>

          <section>
            <SectionHeading>5. Buyer terms &amp; acknowledgements</SectionHeading>
            <p>
              All purchases are made directly through the Platform’s secure Stripe checkout. Buyers are solely responsible for reviewing all
              product details, sizing, descriptions, and Seller policies before purchasing. By completing a purchase, the Buyer enters into a
              direct contract with the Seller, not with Unveiled Threads. Unveiled Threads makes no warranty or representation regarding the
              quality, fitness for purpose, or authenticity of any item purchased through the Platform. Buyers acknowledge that their statutory
              rights under the Consumer Rights Act 2015 are exercisable against the Seller, not against Unveiled Threads.
            </p>
          </section>

          <section>
            <SectionHeading>6. Pricing, fees &amp; payments</SectionHeading>
            <SubHeading>6.1 Pricing structure</SubHeading>
            <p>
              All prices are listed in GBP (£) and set exclusively by individual Sellers. A non-negotiable platform fee of <strong className="text-white">4%</strong> is
              applied to each transaction to support Platform operation and development. Shipping costs are set per product by the Seller and
              displayed at checkout prior to payment. The total charged to the Buyer comprises: product price + platform fee + shipping cost.
              Sellers receive: product price + shipping cost. The Platform retains the 4% fee.
            </p>
            <SubHeading>6.2 Fee non-refundability</SubHeading>
            <p>
              Platform fees are strictly non-refundable under all circumstances, including in cases of disputed transactions, refunds,
              chargebacks, or order cancellations. This reflects the administrative costs incurred in processing the transaction.
            </p>
          </section>

          <section>
            <SectionHeading>7. Refunds, returns &amp; dispute resolution</SectionHeading>
            <SubHeading>7.1 Seller refund policy</SubHeading>
            <p>
              Refund requests must be raised directly with the Seller within 14 days of confirmed delivery. Refunds are at the Seller’s
              discretion, subject to their stated returns policy and the Consumer Rights Act 2015. Unveiled Threads is not liable to provide
              refunds and will not act as guarantor for Seller refund obligations.
            </p>
            <SubHeading>7.2 Platform dispute mediation</SubHeading>
            <p>
              Unveiled Threads may, at its sole discretion and without obligation, facilitate dispute resolution between Buyers and Sellers.
              Any mediation provided by the Platform is offered as a courtesy only and does not constitute acceptance of liability or legal
              responsibility for the outcome. Our decision in any mediation is final and non-binding on either party’s right to pursue external
              legal remedies. We reserve the right to withhold Seller payouts pending investigation of a dispute without incurring any liability
              to the Seller.
            </p>
          </section>

          <section>
            <SectionHeading>8. Shipping, delivery &amp; transit</SectionHeading>
            <p>
              Sellers are entirely responsible for packaging, dispatch, and delivery of all orders. Shipping is managed directly by the Seller
              via their chosen courier (e.g. Royal Mail, Evri, DPD). Unveiled Threads accepts <strong className="text-white">NO</strong> liability whatsoever for:
            </p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>Delays, failures, or errors by any third-party courier or postal service</li>
              <li>Loss, theft, or damage to goods during transit</li>
              <li>Incorrect delivery due to Buyer-supplied address errors</li>
              <li>Customs delays, import duties, or cross-border delivery complications</li>
            </ul>
            <p className="mt-3">
              Buyers must raise delivery disputes directly with the Seller. The Seller is responsible for courier claims. Buyers may track
              orders via the “My Orders” page; tracking data is sourced from third-party couriers and its accuracy is not guaranteed by the
              Platform.
            </p>
          </section>

          <section>
            <SectionHeading>9. Boosted brand promotions</SectionHeading>
            <p>
              Sellers may purchase promotional “Boost” packages to increase visibility on the Platform. Boost packages are:
              Weekly (£9.99), Monthly (£29.99), and Quarterly (£69.99). All Boost packages are strictly non-refundable once activated,
              regardless of performance. Boost packages do not constitute a guarantee of any specific level of sales, views, impressions,
              or revenue. Unveiled Threads reserves the right to amend Boost pricing, availability, and features at any time without liability.
              Featured placement is at the Platform’s discretion and may vary. No SLA or placement guarantee is implied.
            </p>
          </section>

          <section>
            <SectionHeading>10. Limitation of liability</SectionHeading>
            <Callout tone="critical" title="Important — limitation of liability">
              To the maximum extent permitted by applicable law:
              <p className="mt-2">
                Our total aggregate liability to you (whether in contract, tort, negligence, breach of statutory duty, or otherwise) arising out
                of or in connection with these Terms or your use of the Platform shall not exceed the <strong>lower</strong> of:
              </p>
              <ul className="list-[lower-alpha] pl-5 mt-2 space-y-1">
                <li>the total platform fees collected from or attributable to you in the 3-month period immediately preceding the event giving rise to the claim; or</li>
                <li>£100 (one hundred pounds sterling).</li>
              </ul>
              <p className="mt-2">This cap applies to all claims in aggregate, not per incident.</p>
            </Callout>
            <SubHeading>10.2 Exclusion of consequential loss</SubHeading>
            <p>To the fullest extent permitted by law, Unveiled Threads shall not be liable for any:</p>
            <ul className="list-disc pl-5 space-y-2 mt-2">
              <li>Loss of profits, revenue, or anticipated savings</li>
              <li>Loss of business, contracts, or opportunities</li>
              <li>Loss of data or corruption of data</li>
              <li>Reputational damage or loss of goodwill</li>
              <li>Indirect, incidental, special, exemplary, or consequential loss of any nature</li>
            </ul>
            <p className="mt-2">This applies regardless of whether we were advised of the possibility of such losses.</p>
            <SubHeading>10.3 No warranties</SubHeading>
            <p>
              The Platform is provided “as is” and “as available” without any representation or warranty of any kind, express or implied. We
              expressly disclaim any implied warranties of merchantability, fitness for a particular purpose, non-infringement, and accuracy.
              We do not warrant that the Platform will be uninterrupted, error-free, secure, or free of viruses or harmful components. We do
              not warrant that search results, listings, or user-generated content are accurate, complete, or current.
            </p>
            <SubHeading>10.4 Third-party services</SubHeading>
            <p>
              The Platform integrates third-party services including Stripe (payment processing) and courier tracking. We are not responsible
              for the availability, accuracy, or conduct of these third parties. Any links or integrations to external platforms are provided
              for convenience only. We do not endorse or assume liability for third-party content or services.
            </p>
          </section>

          <section>
            <SectionHeading>11. Community standards &amp; messaging</SectionHeading>
            <p>
              All users must treat others with respect. Abusive, hateful, discriminatory, or threatening conduct is strictly prohibited.
              Messages are automatically monitored for: attempts to share personal contact details, redirect payments off-platform
              (PayPal, Venmo, bank transfers), or share external links. Violations may result in message removal, warnings, temporary
              suspension, or permanent account termination at our sole discretion. Community posts and product comments are publicly visible
              and subject to moderation. We may remove any content at any time without notice or liability. We are not responsible for
              user-generated content and do not endorse any opinions, statements, or representations made by Platform users.
            </p>
          </section>

          <section>
            <SectionHeading>12. Intellectual property</SectionHeading>
            <p>
              Sellers retain ownership of their brand names, logos, and product designs. By listing on the Platform, Sellers grant Unveiled
              Threads a non-exclusive, royalty-free, worldwide licence to display, reproduce, and use their content for Platform operation
              and promotional purposes. Sellers warrant that they own or have full licence rights to all content they upload, and that such
              content does not infringe any third-party rights. The Unveiled Threads name, logo, design, and Platform codebase are the
              exclusive intellectual property of the Platform. Unauthorised use is prohibited. Any infringement claims by third parties
              relating to Seller content are the Seller’s sole responsibility under Section 4.3.
            </p>
          </section>

          <section>
            <SectionHeading>13. Privacy &amp; data</SectionHeading>
            <p>
              We collect and process personal data in accordance with the UK GDPR and the Data Protection Act 2018. Personal data is used
              solely for Platform operation, order processing, legal compliance, and relevant user communications. We do not sell personal
              data to third parties. Users may request access to, correction of, or deletion of their personal data by contacting{' '}
              <a href="mailto:privacy@unveiledthreads.co.uk" className="text-[#39FF14] hover:underline">privacy@unveiledthreads.co.uk</a>.
              By using the Platform, you consent to our use of cookies and analytics tools as described in our Privacy Policy (available on
              the website).
            </p>
          </section>

          <section>
            <SectionHeading>14. Force majeure</SectionHeading>
            <p>
              Unveiled Threads shall not be in breach of these Terms, nor liable for any delay or failure in performance, where such delay
              or failure arises from causes beyond our reasonable control, including but not limited to: acts of God, fire, flood, earthquake,
              pandemic, war, terrorism, civil unrest, government action, labour disputes, failure of third-party internet services or
              infrastructure, or failure of payment processors.
            </p>
          </section>

          <section>
            <SectionHeading>15. Termination &amp; suspension</SectionHeading>
            <p>
              We reserve the right to suspend, restrict, or permanently terminate any account at our sole discretion, including for suspected
              fraud, policy violations, abuse, or reputational risk to the Platform. Termination by us does not create any liability to the
              user for compensation, damages, or loss of profits. Users may delete their account at any time via account settings. All
              outstanding orders must be fulfilled before account closure. Upon termination for any reason, all active listings will be
              removed, pending payouts may be held pending audit, and the user’s licence to use the Platform ceases immediately. We are not
              liable for any loss of content, data, or revenue resulting from account termination.
            </p>
          </section>

          <section>
            <SectionHeading>16. General legal provisions</SectionHeading>
            <SubHeading>16.1 Entire agreement</SubHeading>
            <p>
              These Terms, together with our Privacy Policy, Cookie Policy, and any applicable Seller Agreement, constitute the entire
              agreement between you and Unveiled Threads and supersede all prior understandings, representations, or agreements.
            </p>
            <SubHeading>16.2 Severability</SubHeading>
            <p>
              If any provision of these Terms is found by a court of competent jurisdiction to be invalid, unlawful, or unenforceable, that
              provision shall be severed and the remaining provisions shall continue in full force and effect.
            </p>
            <SubHeading>16.3 No waiver</SubHeading>
            <p>
              A failure or delay by us to exercise any right or remedy under these Terms does not constitute a waiver of that or any other
              right or remedy.
            </p>
            <SubHeading>16.4 Assignment</SubHeading>
            <p>
              You may not assign or transfer your rights or obligations under these Terms without our prior written consent. We may assign
              our rights and obligations to any group company or successor entity without notice.
            </p>
            <SubHeading>16.5 Governing law &amp; jurisdiction</SubHeading>
            <p>
              These Terms &amp; Conditions are governed by and construed in accordance with the laws of England and Wales. Both parties
              irrevocably submit to the exclusive jurisdiction of the courts of England and Wales in respect of any dispute or claim arising
              out of or in connection with these Terms.
            </p>
          </section>

          <section>
            <SectionHeading>17. Changes to these terms</SectionHeading>
            <p>
              We may update these Terms at any time. The current version will always be available on the Platform. Continued use of the
              Platform following any change constitutes your unconditional acceptance of the revised Terms. We will endeavour to notify
              registered users of material changes via email or in-app notification. However, it remains your responsibility to check these
              Terms periodically.
            </p>
          </section>

          <section className="border border-white/10 p-5 bg-[#0A0A0A]">
            <p className="text-xs uppercase tracking-[0.2em] text-[#39FF14] mb-2 font-bold">Get in touch</p>
            <p>
              Questions regarding these Terms &amp; Conditions should be directed to:{' '}
              <a href="mailto:legal@unveiledthreads.co.uk" className="text-[#39FF14] hover:underline">legal@unveiledthreads.co.uk</a>
            </p>
          </section>

          <p className="text-xs text-[#9CA3AF] italic border-t border-white/5 pt-6">
            Note: These Terms have been drafted to provide strong operational protections for Unveiled Threads as a marketplace facilitator.
            You are strongly advised to have this document reviewed by a qualified UK commercial solicitor before publishing. This document
            does not constitute legal advice.
          </p>

        </div>
      </div>
    </div>
  );
}
