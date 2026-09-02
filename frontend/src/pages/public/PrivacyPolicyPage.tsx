import { Seo } from "../../components/Seo";
import { Card } from "../../components/ui/Card";

export function PrivacyPolicyPage() {
  return (
    <>
      <Seo
        title="Privacy Policy"
        description="Privacy Policy for AI News Digest. Learn how we collect, use, and protect your data."
      />
      <div className="container-page py-8">
        <div className="mx-auto max-w-3xl">
          <h1 className="text-3xl font-bold text-slate-900">Privacy Policy</h1>
          <p className="mt-2 text-sm text-slate-500">Last updated: August 2026</p>

          <div className="mt-8 space-y-8">
            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">1. Introduction</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  AI News Digest (&quot;we&quot;, &quot;our&quot;, or &quot;the
                  service&quot;) is committed to protecting your privacy. This
                  Privacy Policy explains how we collect, use, disclose, and
                  safeguard your information when you use our AI-powered news
                  aggregation and digest platform.
                </p>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">2. Information We Collect</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  We collect the following types of information:
                </p>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700">
                  <li>
                    <strong>Account Information:</strong> Email address and
                    encrypted password when you register for an account.
                  </li>
                  <li>
                    <strong>Usage Data:</strong> Log data including IP address,
                    browser type, pages visited, and timestamps for operational
                    and security purposes.
                  </li>
                  <li>
                    <strong>Article Interaction Data:</strong> Records of
                    articles you view to improve digest recommendations.
                  </li>
                </ul>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">3. How We Use Your Information</h2>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700">
                  <li>To provide and maintain our service</li>
                  <li>To generate personalized news digests</li>
                  <li>To authenticate your identity and secure your account</li>
                  <li>To improve our algorithms and user experience</li>
                  <li>To send service-related notifications (e.g., digest delivery)</li>
                  <li>To detect, prevent, and address technical issues or abuse</li>
                </ul>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">4. Data Retention</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  We retain your account information for as long as your account
                  is active. If you delete your account, we will remove your
                  personal data within 30 days, except where retention is required
                  by law. Article interaction logs are anonymized after 90 days.
                </p>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">5. Account Deletion</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  You may request account deletion at any time by contacting
                  support or through your account settings. Upon deletion:
                </p>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700">
                  <li>Your profile and personal data will be permanently removed</li>
                  <li>Your email address will be removed from all mailing lists</li>
                  <li>Anonymized usage statistics may be retained for analytics</li>
                </ul>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">6. Data Security</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  We implement industry-standard security measures including:
                </p>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700">
                  <li>Password hashing with bcrypt</li>
                  <li>Encrypted connections (TLS/HTTPS)</li>
                  <li>Regular security audits and vulnerability scanning</li>
                  <li>Access controls and authentication for administrative functions</li>
                </ul>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">7. Third-Party Services</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  We may use third-party services for AI processing (e.g., OpenAI,
                  Anthropic) to summarize articles. These services process content
                  on our behalf under data processing agreements. We do not sell
                  your personal data to third parties.
                </p>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">8. Cookies</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  We use essential cookies for authentication and session
                  management. No tracking cookies or third-party advertising
                  cookies are used.
                </p>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">9. Your Rights</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  Depending on your jurisdiction, you may have the right to:
                </p>
                <ul className="mt-3 list-disc space-y-2 pl-5 text-slate-700">
                  <li>Access your personal data</li>
                  <li>Correct inaccurate data</li>
                  <li>Request deletion of your data</li>
                  <li>Object to or restrict processing</li>
                  <li>Data portability</li>
                </ul>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">10. Contact</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  For privacy-related inquiries or to exercise your data rights,
                  please contact us at the email address provided on our website.
                </p>
              </section>
            </Card>

            <Card>
              <section>
                <h2 className="text-xl font-semibold text-slate-900">11. Changes to This Policy</h2>
                <p className="mt-3 text-slate-700 leading-relaxed">
                  We may update this Privacy Policy from time to time. We will
                  notify you of material changes by posting the new policy on
                  this page and updating the &quot;Last updated&quot; date.
                </p>
              </section>
            </Card>
          </div>

          <p className="mt-8 text-sm text-slate-500">
            This policy is provided as a template and should be reviewed by a
            qualified legal professional before publication.
          </p>
        </div>
      </div>
    </>
  );
}
