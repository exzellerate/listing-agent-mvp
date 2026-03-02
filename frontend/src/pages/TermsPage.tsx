import { Link } from 'react-router-dom';
import { Zap } from 'lucide-react';

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="px-6 py-4 flex justify-between items-center max-w-7xl mx-auto">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-gray-900">exzellerate</span>
        </Link>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Terms & Conditions</h1>
        <p className="text-sm text-gray-500 mb-10">Last updated: March 2, 2026</p>

        <div className="space-y-10 text-gray-700 leading-relaxed">
          {/* 1. Introduction & Acceptance */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">1. Introduction & Acceptance</h2>
            <p>
              Welcome to exzellerate, operated by its owner. These Terms & Conditions ("Terms") govern your
              access to and use of the exzellerate platform, including all features, services, and content
              available through the website.
            </p>
            <p className="mt-3">
              By accessing or using exzellerate, you agree to be bound by these Terms. If you do not agree
              to these Terms, you must not use the platform.
            </p>
          </section>

          {/* 2. Service Description */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">2. Service Description</h2>
            <p>
              exzellerate is an AI-powered listing generation tool for online marketplaces, currently
              supporting eBay. The service allows users to:
            </p>
            <ul className="list-disc ml-6 mt-3 space-y-1">
              <li>Upload product images for AI-powered analysis</li>
              <li>Generate optimized listing content including titles, descriptions, and item specifics</li>
              <li>Connect their eBay account to publish listings directly</li>
            </ul>
          </section>

          {/* 3. User Responsibilities */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">3. User Responsibilities</h2>
            <p>By using exzellerate, you acknowledge and agree that:</p>
            <ul className="list-disc ml-6 mt-3 space-y-2">
              <li>You are solely responsible for reviewing, verifying, and editing ALL AI-generated content before publishing any listing.</li>
              <li>You must ensure all listings comply with eBay's policies and all applicable laws and regulations.</li>
              <li>You are responsible for the accuracy of all published listings, including product descriptions, pricing, and condition assessments.</li>
              <li>You must have proper authorization to sell any items you list.</li>
              <li>You are responsible for the security of your eBay account and all activity that occurs through it.</li>
            </ul>
          </section>

          {/* 4. AI-Generated Content Disclaimer */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">4. AI-Generated Content Disclaimer</h2>
            <p>
              The AI analysis provided by exzellerate is a tool to assist with listing creation. It is
              not professional advice of any kind.
            </p>
            <p className="mt-3">
              AI may produce content that is inaccurate, incomplete, or unsuitable for your specific
              listing needs. There is no warranty on the accuracy of any AI-generated information,
              including but not limited to:
            </p>
            <ul className="list-disc ml-6 mt-3 space-y-1">
              <li>Product identification and brand recognition</li>
              <li>Condition assessments</li>
              <li>Pricing suggestions</li>
              <li>Product descriptions and titles</li>
              <li>Category and item specifics selection</li>
            </ul>
            <p className="mt-3">
              You must independently verify all AI-generated information before using it. AI capabilities
              and outputs may change without notice.
            </p>
          </section>

          {/* 5. eBay & Third-Party Integration */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">5. eBay & Third-Party Integration</h2>
            <p>
              exzellerate integrates with eBay and other third-party services but does not control their
              policies, enforcement actions, or platform availability. exzellerate is not responsible for:
            </p>
            <ul className="list-disc ml-6 mt-3 space-y-1">
              <li>Account suspensions or restrictions imposed by eBay</li>
              <li>Listing removals by eBay</li>
              <li>Policy violation penalties assessed by eBay</li>
              <li>Negative feedback or buyer disputes</li>
              <li>Fee disputes with eBay</li>
            </ul>
            <p className="mt-3">
              eBay's terms of service apply independently to all your eBay activity. You may revoke
              exzellerate's OAuth access to your eBay account at any time. exzellerate is not responsible
              for eBay API changes, outages, or policy updates that may affect the service.
            </p>
          </section>

          {/* 6. Limitation of Liability */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">6. Limitation of Liability</h2>
            <p>
              THE PLATFORM IS PROVIDED "AS-IS" AND "AS-AVAILABLE" WITHOUT WARRANTIES OF ANY KIND,
              WHETHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY,
              FITNESS FOR A PARTICULAR PURPOSE, OR NON-INFRINGEMENT.
            </p>
            <p className="mt-3">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, EXZELLERATE SHALL NOT BE LIABLE FOR ANY INDIRECT,
              INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO:
            </p>
            <ul className="list-disc ml-6 mt-3 space-y-1">
              <li>Lost revenue, lost sales, or lost profits</li>
              <li>Lost business opportunities</li>
              <li>Losses arising from inaccurate AI-generated content</li>
              <li>Losses from marketplace policy violations</li>
              <li>Losses from account actions taken by eBay or other platforms</li>
              <li>Losses from pricing errors in listings</li>
            </ul>
            <p className="mt-3">
              IN NO EVENT SHALL EXZELLERATE'S TOTAL LIABILITY EXCEED THE AMOUNT YOU HAVE PAID TO
              EXZELLERATE IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM. AS THE SERVICE IS CURRENTLY
              PROVIDED FREE OF CHARGE, THIS LIABILITY CAP MAY BE ZERO.
            </p>
          </section>

          {/* 7. Indemnification */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">7. Indemnification</h2>
            <p>
              You agree to indemnify, defend, and hold harmless exzellerate and its owner from and against
              any and all claims, damages, losses, liabilities, costs, and expenses (including reasonable
              attorneys' fees) arising from or related to:
            </p>
            <ul className="list-disc ml-6 mt-3 space-y-1">
              <li>Your use of AI-generated content in listings</li>
              <li>Listings that violate eBay policies or applicable laws</li>
              <li>Your breach of these Terms</li>
              <li>Third-party claims regarding your listings</li>
              <li>Intellectual property infringement through your listings</li>
            </ul>
          </section>

          {/* 8. Data & Privacy */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">8. Data & Privacy</h2>
            <p>
              By using exzellerate, you acknowledge and consent to the following:
            </p>
            <ul className="list-disc ml-6 mt-3 space-y-2">
              <li>Images you upload are processed by third-party AI providers (including Anthropic) for analysis and listing generation.</li>
              <li>Listing data is stored as necessary for service operation and improvement.</li>
              <li>You consent to the processing of your uploaded images by AI providers as part of the service.</li>
            </ul>
            <p className="mt-3">
              A comprehensive Privacy Policy may be published separately in the future.
            </p>
          </section>

          {/* 9. Acceptable Use */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">9. Acceptable Use</h2>
            <p>You agree not to use exzellerate to:</p>
            <ul className="list-disc ml-6 mt-3 space-y-1">
              <li>List prohibited or illegal items</li>
              <li>Create misleading or deceptive listing content</li>
              <li>Infringe on intellectual property rights</li>
              <li>Reverse engineer, decompile, or disassemble the platform or its AI systems</li>
            </ul>
            <p className="mt-3">
              Violations of these acceptable use guidelines may result in immediate termination of your
              access to the platform.
            </p>
          </section>

          {/* 10. Free Service */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">10. Free Service</h2>
            <p>
              exzellerate is currently provided at no cost. The service may be modified, suspended, or
              discontinued at any time without prior notice. There is no obligation to maintain uptime,
              availability, or any specific level of service.
            </p>
          </section>

          {/* 11. Changes to Terms */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">11. Changes to Terms</h2>
            <p>
              exzellerate reserves the right to update or modify these Terms at any time. Changes will be
              effective upon posting to the platform. Your continued use of the service after changes are
              posted constitutes your acceptance of the updated Terms.
            </p>
          </section>

          {/* 12. Governing Law & Disputes */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">12. Governing Law & Disputes</h2>
            <p>
              These Terms shall be governed by and construed in accordance with the laws of the applicable
              jurisdiction. Any disputes arising from or related to these Terms or your use of the platform
              shall be resolved through binding arbitration where permitted by law.
            </p>
          </section>

          {/* 13. Contact */}
          <section>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">13. Contact</h2>
            <p>
              If you have questions about these Terms & Conditions, please contact us at{' '}
              <a href="mailto:support@exzellerate.com" className="text-green-600 hover:underline">
                support@exzellerate.com
              </a>.
            </p>
          </section>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">exzellerate</span>
          </div>
          <p className="text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} exzellerate. Making marketplace selling effortless with AI.
          </p>
        </div>
      </footer>
    </div>
  );
}
