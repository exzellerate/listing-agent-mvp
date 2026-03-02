import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';
import { Zap, Upload, MousePointerClick, TrendingUp, ArrowRight, Package, Users, LayoutList, Award } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function LandingPage() {
  const { isSignedIn } = useAuth();
  const [stats, setStats] = useState<{ listings_published: number; active_sellers: number } | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/stats/public`)
      .then(res => res.ok ? res.json() : null)
      .then(data => { if (data) setStats(data); })
      .catch(() => {});
  }, []);

  return (
    <div className="min-h-screen bg-white">
      {/* Header */}
      <header className="px-6 py-4 flex justify-between items-center max-w-7xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <span className="text-xl font-bold text-gray-900">exzellerate</span>
        </div>
        <div className="flex gap-3">
          {isSignedIn ? (
            <Link
              to="/upload"
              className="px-4 py-2 bg-green-500 text-white rounded-full hover:bg-green-600 transition font-medium"
            >
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link
                to="/sign-in"
                className="px-4 py-2 border border-gray-300 text-gray-700 rounded-full hover:bg-gray-50 transition font-medium"
              >
                Sign In
              </Link>
              <Link
                to="/sign-up"
                className="px-4 py-2 bg-green-500 text-white rounded-full hover:bg-green-600 transition font-medium"
              >
                Get Started
              </Link>
            </>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 pt-16 pb-12 text-center">
        <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-4">
          List on marketplaces
        </h1>
        <h2 className="text-5xl md:text-6xl font-bold mb-6">
          <span className="bg-gradient-to-r from-purple-500 via-pink-500 to-green-500 bg-clip-text text-transparent">
            with just an image
          </span>
        </h2>
        <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
          Upload a photo. Our AI creates optimized listings for eBay.
          It's that simple — the rest is magic.
        </p>

        {/* CTA Buttons */}
        <div className="flex gap-4 justify-center mb-8">
          <Link
            to={isSignedIn ? "/upload" : "/sign-up"}
            className="px-6 py-3 bg-green-500 text-white rounded-full hover:bg-green-600 transition font-medium flex items-center gap-2"
          >
            <Upload className="w-5 h-5" />
            Upload & List Now
          </Link>
          <a
            href="#how-it-works"
            className="px-6 py-3 border border-gray-300 text-gray-700 rounded-full hover:bg-gray-50 transition font-medium"
          >
            See How It Works
          </a>
        </div>

        {/* Real-time stats */}
        {stats && (stats.listings_published > 0 || stats.active_sellers > 0) && (
          <div className="flex justify-center gap-12 text-center">
            {stats.listings_published > 0 && (
              <div className="flex items-center gap-2">
                <Package className="w-5 h-5 text-green-500" />
                <span className="text-2xl font-bold text-gray-900">{stats.listings_published.toLocaleString()}</span>
                <span className="text-sm text-gray-500">listings published</span>
              </div>
            )}
            {stats.active_sellers > 0 && (
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-purple-500" />
                <span className="text-2xl font-bold text-gray-900">{stats.active_sellers.toLocaleString()}</span>
                <span className="text-sm text-gray-500">active sellers</span>
              </div>
            )}
          </div>
        )}

      </section>

      {/* AI-Powered Magic Card */}
      <section className="max-w-6xl mx-auto px-6 py-12">
        <div className="bg-gray-50 rounded-3xl p-8 md:p-12 flex flex-col md:flex-row gap-8 items-center">
          {/* Left Content */}
          <div className="flex-1">
            <span className="inline-block px-3 py-1 bg-green-100 text-green-700 text-sm font-medium rounded-full mb-4">
              AI-Powered Magic
            </span>
            <h3 className="text-3xl md:text-4xl font-bold text-gray-900 mb-1">
              Your Image.
            </h3>
            <h3 className="text-3xl md:text-4xl font-bold text-green-500 mb-4">
              A Sales-Ready Listing.
            </h3>
            <p className="text-gray-600 mb-6">
              Upload a simple photo and our AI turns it into a fully optimized marketplace listing:
            </p>
            <ul className="space-y-3">
              {[
                'SEO-optimized titles that rank higher in search',
                'Detailed, compelling product descriptions',
                'Smart category & item specifics selection',
                'Ready to publish on eBay, Amazon & more'
              ].map((item, i) => (
                <li key={i} className="flex items-center gap-3 text-gray-700">
                  <ArrowRight className="w-4 h-4 text-green-500 flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Right Content - Sample Product */}
          <div className="flex-1">
            <div className="bg-gradient-to-br from-purple-100 via-blue-100 to-green-100 rounded-2xl p-8 aspect-[4/3] flex items-center justify-center">
              <div className="bg-white rounded-xl shadow-lg p-4 w-full max-w-xs">
                <img
                  src="/sample-product.jpg"
                  alt="Sample product"
                  className="rounded-lg aspect-square mb-3 object-cover w-full"
                />
                <div className="h-3 bg-gray-200 rounded mb-2 w-3/4"></div>
                <div className="h-2 bg-gray-100 rounded mb-1 w-full"></div>
                <div className="h-2 bg-gray-100 rounded w-2/3"></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Why exzellerate Section */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
            Why{' '}
            <span className="bg-gradient-to-r from-purple-500 to-green-500 bg-clip-text text-transparent">
              exzellerate
            </span>
          </h2>
          <p className="text-gray-600">Less time listing. More time selling.</p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Dead Simple */}
          <div className="text-center md:text-left">
            <div className="w-14 h-14 bg-purple-100 rounded-xl flex items-center justify-center mb-4 mx-auto md:mx-0">
              <MousePointerClick className="w-7 h-7 text-purple-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Dead Simple</h3>
            <p className="text-gray-600">
              Upload a photo, review the listing, and publish. That's it — no learning curve, no complexity.
            </p>
          </div>

          {/* Optimized for Sales */}
          <div className="text-center md:text-left">
            <div className="w-14 h-14 bg-green-100 rounded-xl flex items-center justify-center mb-4 mx-auto md:mx-0">
              <TrendingUp className="w-7 h-7 text-green-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Optimized to Sell</h3>
            <p className="text-gray-600">
              AI-generated titles and descriptions designed to increase visibility and drive conversions.
            </p>
          </div>

          {/* Perfectly Formatted */}
          <div className="text-center md:text-left">
            <div className="w-14 h-14 bg-teal-100 rounded-xl flex items-center justify-center mb-4 mx-auto md:mx-0">
              <LayoutList className="w-7 h-7 text-teal-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Perfectly Formatted</h3>
            <p className="text-gray-600">
              Every listing is structured and formatted exactly how marketplaces want it — ready to go live.
            </p>
          </div>

          {/* Built by eBay Experts */}
          <div className="text-center md:text-left">
            <div className="w-14 h-14 bg-amber-100 rounded-xl flex items-center justify-center mb-4 mx-auto md:mx-0">
              <Award className="w-7 h-7 text-amber-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Ex-eBay Team</h3>
            <p className="text-gray-600">
              Built by a former eBay team member who knows exactly what makes listings succeed on the platform.
            </p>
          </div>
        </div>
      </section>

      {/* Simple. Smart. Selling. Section */}
      <section id="how-it-works" className="mx-6 my-12">
        <div className="max-w-6xl mx-auto bg-gradient-to-r from-purple-600 via-purple-500 to-teal-500 rounded-3xl p-12 text-center text-white">
          <h2 className="text-3xl md:text-4xl font-bold mb-12">
            Simple. Smart. Selling.
          </h2>

          <div className="grid md:grid-cols-3 gap-8 mb-10">
            {/* Step 1 */}
            <div>
              <div className="text-6xl font-bold text-white/30 mb-2">1</div>
              <h3 className="text-xl font-semibold mb-2">Upload Photo</h3>
              <p className="text-white/80 text-sm">
                Snap or upload your product image
              </p>
            </div>

            {/* Step 2 */}
            <div>
              <div className="text-6xl font-bold text-white/30 mb-2">2</div>
              <h3 className="text-xl font-semibold mb-2">AI Generates</h3>
              <p className="text-white/80 text-sm">
                Watch as perfect listings are created
              </p>
            </div>

            {/* Step 3 */}
            <div>
              <div className="text-6xl font-bold text-white/30 mb-2">3</div>
              <h3 className="text-xl font-semibold mb-2">Publish & Sell</h3>
              <p className="text-white/80 text-sm">
                Post to marketplaces with one click
              </p>
            </div>
          </div>

          <Link
            to={isSignedIn ? "/upload" : "/sign-up"}
            className="inline-block px-8 py-3 bg-white text-purple-600 rounded-full font-semibold hover:bg-gray-100 transition"
          >
            Start Listing for Free
          </Link>
          <p className="text-white/70 text-sm mt-4">
            No credit card required • Free forever plan
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-6 py-8 flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">exzellerate</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/terms" className="text-gray-500 hover:text-gray-700 text-sm">Terms & Conditions</Link>
            <p className="text-gray-500 text-sm">
              © {new Date().getFullYear()} exzellerate. Making marketplace selling effortless with AI.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
