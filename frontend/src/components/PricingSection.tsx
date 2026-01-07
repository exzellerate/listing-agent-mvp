import { useState } from 'react';
import { PricingData, Platform, AnalysisResult } from '../types';
import { researchPricing, APIError } from '../services/api';

interface PricingSectionProps {
  analysis: AnalysisResult;
  platform: Platform;
  onPriceSelected?: (price: number) => void;
}

export default function PricingSection({ analysis, platform, onPriceSelected }: PricingSectionProps) {
  const [pricingData, setPricingData] = useState<PricingData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCompetitors, setShowCompetitors] = useState(false);
  const [customPrice, setCustomPrice] = useState<string>('');

  const handleResearch = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await researchPricing(
        analysis.product_name,
        analysis.category,
        analysis.condition,
        platform
      );
      setPricingData(data);
      setCustomPrice(data.statistics.suggested_price.toFixed(2));
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to research pricing. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUsePrice = () => {
    const price = parseFloat(customPrice);
    if (!isNaN(price) && price > 0 && onPriceSelected) {
      onPriceSelected(price);
    }
  };

  const getConfidenceColor = (score: number) => {
    if (score >= 80) return 'text-green-600 bg-green-100';
    if (score >= 50) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getConfidenceEmoji = (score: number) => {
    if (score >= 80) return '🟢';
    if (score >= 50) return '🟡';
    return '🔴';
  };

  if (!pricingData && !loading && !error) {
    return (
      <div className="bg-gradient-to-br from-green-50 to-blue-50 border-2 border-green-200 rounded-xl p-6 shadow-md">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-bold text-gray-900 mb-1">
              💰 Want to know the right price?
            </h3>
            <p className="text-sm text-gray-600">
              Get AI-powered market pricing analysis with competitor data and insights
            </p>
          </div>
          <button
            onClick={handleResearch}
            className="px-6 py-3 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white rounded-xl font-bold transition-all duration-300 transform hover:scale-105 shadow-lg"
          >
            Research Pricing
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="bg-white border-2 border-gray-200 rounded-xl p-8 shadow-md">
        <div className="flex flex-col items-center justify-center">
          <div className="relative">
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-green-200"></div>
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-t-green-600 border-r-blue-600 absolute top-0 left-0"></div>
          </div>
          <p className="mt-4 text-lg font-semibold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
            Researching market prices...
          </p>
          <p className="text-sm text-gray-500 mt-1">Analyzing competitor data and market trends</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border-2 border-red-200 rounded-xl p-6 shadow-md">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
            <svg className="w-6 h-6 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="font-bold text-red-900">Pricing Research Failed</h3>
            <p className="text-red-700 mt-1">{error}</p>
            <button
              onClick={handleResearch}
              className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!pricingData) return null;

  const { statistics, confidence_score, market_insights, competitor_prices, timestamp } = pricingData;
  const priceRange = statistics.max_price - statistics.min_price;
  const suggestedPosition = ((statistics.suggested_price - statistics.min_price) / priceRange) * 100;

  return (
    <div className="space-y-4 animate-fadeIn">
      {/* Header with confidence */}
      <div className="bg-gradient-to-br from-green-50 to-blue-50 border-2 border-green-200 rounded-xl p-6 shadow-md">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="text-2xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent">
              💰 Pricing Analysis
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              Updated: {new Date(timestamp).toLocaleString()}
            </p>
          </div>
          <div className={`px-4 py-2 rounded-full font-bold ${getConfidenceColor(confidence_score)}`}>
            {getConfidenceEmoji(confidence_score)} {confidence_score}% Confidence
          </div>
        </div>

        {/* Price Range Visualization */}
        <div className="bg-white rounded-lg p-6 shadow-sm">
          <div className="flex justify-between text-sm font-medium text-gray-600 mb-2">
            <span>Min: ${statistics.min_price.toFixed(2)}</span>
            <span>Max: ${statistics.max_price.toFixed(2)}</span>
          </div>

          <div className="relative h-8 bg-gradient-to-r from-red-200 via-yellow-200 to-green-200 rounded-full overflow-hidden">
            <div
              className="absolute top-0 h-full w-1 bg-blue-600 shadow-lg"
              style={{ left: `${suggestedPosition}%` }}
            >
              <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 whitespace-nowrap">
                <div className="bg-blue-600 text-white px-3 py-1 rounded-lg font-bold text-sm shadow-lg">
                  ${statistics.suggested_price.toFixed(2)}
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mt-6">
            <div className="text-center">
              <p className="text-sm text-gray-600">Average</p>
              <p className="text-lg font-bold text-gray-900">${statistics.average.toFixed(2)}</p>
            </div>
            <div className="text-center border-x-2">
              <p className="text-sm text-gray-600">Median</p>
              <p className="text-lg font-bold text-gray-900">${statistics.median.toFixed(2)}</p>
            </div>
            <div className="text-center">
              <p className="text-sm text-gray-600">Suggested</p>
              <p className="text-2xl font-bold text-blue-600">${statistics.suggested_price.toFixed(2)}</p>
            </div>
          </div>
        </div>

        {/* Market Insights */}
        <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-bold text-blue-900 mb-2">📊 Market Insights</h4>
          <p className="text-sm text-blue-800">{market_insights}</p>
        </div>
      </div>

      {/* Custom Price Input */}
      <div className="bg-white border-2 border-gray-200 rounded-xl p-6 shadow-md">
        <h4 className="font-bold text-gray-900 mb-3">Set Your Price</h4>
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Listing Price
            </label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 font-bold">
                $
              </span>
              <input
                type="number"
                value={customPrice}
                onChange={(e) => setCustomPrice(e.target.value)}
                step="0.01"
                min="0"
                className="w-full pl-8 pr-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-bold text-lg"
                placeholder="0.00"
              />
            </div>
          </div>
          <button
            onClick={handleUsePrice}
            className="self-end px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg font-bold transition-all transform hover:scale-105 shadow-md"
          >
            Use This Price
          </button>
        </div>
      </div>

      {/* Competitor Listings */}
      {competitor_prices.length > 0 && (
        <div className="bg-white border-2 border-gray-200 rounded-xl overflow-hidden shadow-md">
          <button
            onClick={() => setShowCompetitors(!showCompetitors)}
            className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
          >
            <h4 className="font-bold text-gray-900">
              🔍 Competitor Listings ({competitor_prices.length})
            </h4>
            <svg
              className={`w-5 h-5 text-gray-600 transform transition-transform ${showCompetitors ? 'rotate-180' : ''}`}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>

          {showCompetitors && (
            <div className="border-t-2 border-gray-200 divide-y divide-gray-200">
              {competitor_prices.map((comp, index) => (
                <div key={index} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{comp.title}</p>
                      {comp.date_sold && (
                        <p className="text-sm text-gray-500 mt-1">Sold: {comp.date_sold}</p>
                      )}
                    </div>
                    <div className="text-right flex-shrink-0">
                      <p className="text-xl font-bold text-green-600">${comp.price.toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Refresh Button */}
      <button
        onClick={handleResearch}
        disabled={loading}
        className="w-full px-4 py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-medium transition-colors disabled:opacity-50"
      >
        🔄 Refresh Pricing Data
      </button>
    </div>
  );
}
