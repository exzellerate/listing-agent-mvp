import { Link } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';

export default function LandingPage() {
  const { isSignedIn } = useAuth();

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <header className="px-6 py-4 flex justify-between items-center max-w-7xl mx-auto">
        <div className="text-2xl font-bold text-gray-900">
          Listing Agent
        </div>
        <div className="flex gap-4">
          {isSignedIn ? (
            <Link
              to="/upload"
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/sign-in"
                className="px-4 py-2 text-gray-700 hover:text-gray-900 transition"
              >
                Sign In
              </Link>
              <Link
                to="/sign-up"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-7xl mx-auto px-6 py-20">
        <div className="text-center">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            AI-Powered Product Listings
          </h1>
          <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
            Transform product photos into optimized eBay listings in seconds.
            Our AI analyzes your images, identifies products, and generates
            professional titles, descriptions, and item specifics.
          </p>
          <div className="flex gap-4 justify-center">
            <Link
              to={isSignedIn ? "/upload" : "/sign-up"}
              className="px-8 py-3 bg-blue-600 text-white text-lg rounded-lg hover:bg-blue-700 transition"
            >
              {isSignedIn ? "Start Listing" : "Get Started Free"}
            </Link>
            <a
              href="#features"
              className="px-8 py-3 border border-gray-300 text-gray-700 text-lg rounded-lg hover:bg-gray-50 transition"
            >
              Learn More
            </a>
          </div>
        </div>

        {/* Features Section */}
        <section id="features" className="mt-32">
          <h2 className="text-3xl font-bold text-center text-gray-900 mb-12">
            How It Works
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Upload Photos</h3>
              <p className="text-gray-600">
                Simply upload photos of your product. Our AI works best with multiple angles
                and clear images.
              </p>
            </div>

            <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">AI Analysis</h3>
              <p className="text-gray-600">
                Our AI identifies your product, researches market prices, and determines
                the best eBay category and item specifics.
              </p>
            </div>

            <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-100">
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">Publish</h3>
              <p className="text-gray-600">
                Review the generated listing, make any adjustments, and publish directly
                to eBay with one click.
              </p>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="mt-32 text-center bg-blue-600 rounded-2xl p-12">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to streamline your listings?
          </h2>
          <p className="text-blue-100 mb-8 max-w-xl mx-auto">
            Join sellers who are saving hours every week with AI-powered listing creation.
          </p>
          <Link
            to={isSignedIn ? "/upload" : "/sign-up"}
            className="px-8 py-3 bg-white text-blue-600 text-lg font-semibold rounded-lg hover:bg-blue-50 transition inline-block"
          >
            {isSignedIn ? "Go to Dashboard" : "Start Free Trial"}
          </Link>
        </section>
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-6 py-8 mt-20 border-t border-gray-200">
        <div className="text-center text-gray-500">
          &copy; {new Date().getFullYear()} Listing Agent. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
