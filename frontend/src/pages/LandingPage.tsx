import { Link } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';
import { Zap, Upload, LayoutGrid, TrendingUp, ArrowRight, Star } from 'lucide-react';

export default function LandingPage() {
  const { isSignedIn } = useAuth();

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
          Upload a photo. Our AI creates optimized listings for eBay, Amazon, Etsy & more.
          It's that simple — the rest is magic.
        </p>

        {/* CTA Buttons */}
        <div className="flex gap-4 justify-center mb-6">
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

        {/* Social Proof */}
        <div className="flex items-center justify-center gap-2 text-sm text-gray-600">
          <div className="flex">
            {[...Array(5)].map((_, i) => (
              <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
            ))}
          </div>
          <span>Join 15,000+ sellers making listings effortless</span>
        </div>
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
              One Photo.
            </h3>
            <h3 className="text-3xl md:text-4xl font-bold text-green-500 mb-4">
              Unlimited Listings.
            </h3>
            <p className="text-gray-600 mb-6">
              Our advanced AI analyzes your product image and automatically generates:
            </p>
            <ul className="space-y-3">
              {[
                'Compelling titles optimized for search',
                'Detailed, accurate descriptions',
                'Perfect category & tag suggestions',
                'Multi-platform formatting (eBay, Amazon, Etsy)'
              ].map((item, i) => (
                <li key={i} className="flex items-center gap-3 text-gray-700">
                  <ArrowRight className="w-4 h-4 text-green-500 flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Right Content - Placeholder Mockup */}
          <div className="flex-1 relative">
            <div className="bg-gradient-to-br from-purple-100 via-blue-100 to-green-100 rounded-2xl p-8 aspect-[4/3] flex items-center justify-center">
              <div className="bg-white rounded-xl shadow-lg p-4 w-full max-w-xs">
                <div className="bg-gray-200 rounded-lg aspect-square mb-3 flex items-center justify-center">
                  <span className="text-gray-400 text-sm">Product Image</span>
                </div>
                <div className="h-3 bg-gray-200 rounded mb-2 w-3/4"></div>
                <div className="h-2 bg-gray-100 rounded mb-1 w-full"></div>
                <div className="h-2 bg-gray-100 rounded w-2/3"></div>
              </div>
            </div>
            {/* Listed Badge */}
            <div className="absolute bottom-4 left-4 bg-white rounded-lg shadow-lg px-4 py-2">
              <span className="text-xs text-gray-500">Listed in</span>
              <div className="text-xl font-bold text-green-500">2.3 sec</div>
            </div>
          </div>
        </div>
      </section>

      {/* Why Sellers Love Section */}
      <section className="max-w-7xl mx-auto px-6 py-16">
        <div className="text-center mb-12">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-2">
            Why sellers love{' '}
            <span className="bg-gradient-to-r from-purple-500 to-green-500 bg-clip-text text-transparent">
              exzellerate
            </span>
          </h2>
          <p className="text-gray-600">Less time listing. More time selling.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {/* Lightning Fast */}
          <div className="text-center md:text-left">
            <div className="w-14 h-14 bg-purple-100 rounded-xl flex items-center justify-center mb-4 mx-auto md:mx-0">
              <Zap className="w-7 h-7 text-purple-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Lightning Fast</h3>
            <p className="text-gray-600">
              List products in seconds, not hours. Our AI works while you focus on growing your business.
            </p>
          </div>

          {/* Multi-Platform Ready */}
          <div className="text-center md:text-left">
            <div className="w-14 h-14 bg-green-100 rounded-xl flex items-center justify-center mb-4 mx-auto md:mx-0">
              <LayoutGrid className="w-7 h-7 text-green-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Multi-Platform Ready</h3>
            <p className="text-gray-600">
              One upload creates perfectly formatted listings for all major marketplaces automatically.
            </p>
          </div>

          {/* Optimized for Sales */}
          <div className="text-center md:text-left">
            <div className="w-14 h-14 bg-teal-100 rounded-xl flex items-center justify-center mb-4 mx-auto md:mx-0">
              <TrendingUp className="w-7 h-7 text-teal-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Optimized for Sales</h3>
            <p className="text-gray-600">
              AI-generated titles and descriptions proven to increase visibility and conversion rates.
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

      {/* Stats Section */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="bg-gradient-to-r from-gray-50 to-green-50/30 rounded-3xl py-16">
          <div className="grid md:grid-cols-3 gap-8 text-center">
            <div>
              <div className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-purple-500 to-purple-600 bg-clip-text text-transparent mb-2">
                15,000+
              </div>
              <p className="text-gray-600">Active Sellers</p>
            </div>
            <div>
              <div className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-teal-500 to-green-500 bg-clip-text text-transparent mb-2">
                500K+
              </div>
              <p className="text-gray-600">Listings Created</p>
            </div>
            <div>
              <div className="text-5xl md:text-6xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent mb-2">
                98%
              </div>
              <p className="text-gray-600">Satisfaction Rate</p>
            </div>
          </div>
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
          <p className="text-gray-500 text-sm">
            © {new Date().getFullYear()} exzellerate. Making marketplace selling effortless with AI.
          </p>
        </div>
      </footer>
    </div>
  );
}
