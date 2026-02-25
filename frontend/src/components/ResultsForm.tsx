import { useState, useEffect } from 'react';
import { AnalysisResult } from '../types';
import CopyButton from './CopyButton';
import AttributesDisplay from './AttributesDisplay';

interface ResultsFormProps {
  result: AnalysisResult;
  price?: number;
  onPriceChange?: (price: number) => void;
}

export default function ResultsForm({ result, price, onPriceChange }: ResultsFormProps) {
  const [title, setTitle] = useState(result.suggested_title);
  const [description, setDescription] = useState(result.suggested_description);
  const [category, setCategory] = useState(result.category || '');
  const [condition, setCondition] = useState(result.condition);
  const [features, setFeatures] = useState<string[]>(result.key_features);
  const [newFeature, setNewFeature] = useState('');
  const [priceInput, setPriceInput] = useState(price?.toFixed(2) || '');
  const [showReasoning, setShowReasoning] = useState(false);
  const [showDiscrepancies, setShowDiscrepancies] = useState(false);
  const [showEbayCategory, setShowEbayCategory] = useState(true);  // Expanded by default
  const [showEbayAspects, setShowEbayAspects] = useState(true);     // Expanded by default

  // Update state when result changes
  useEffect(() => {
    setTitle(result.suggested_title);
    setDescription(result.suggested_description);
    setCategory(result.category || '');
    setCondition(result.condition);
    setFeatures(result.key_features);
  }, [result]);

  // Update price input when price prop changes
  useEffect(() => {
    if (price !== undefined) {
      setPriceInput(price.toFixed(2));
    }
  }, [price]);

  const addFeature = () => {
    if (newFeature.trim()) {
      setFeatures([...features, newFeature.trim()]);
      setNewFeature('');
    }
  };

  const removeFeature = (index: number) => {
    setFeatures(features.filter((_, i) => i !== index));
  };

  const handlePriceChange = (value: string) => {
    setPriceInput(value);
    const numPrice = parseFloat(value);
    if (!isNaN(numPrice) && numPrice > 0 && onPriceChange) {
      onPriceChange(numPrice);
    }
  };

  const titleCharCount = title.length;

  // Get confidence color based on score
  const getConfidenceColor = (score: number) => {
    if (score >= 90) return 'text-green-600 bg-green-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-orange-600 bg-orange-100';
  };

  const confidenceScore = result.confidence_score || 100;
  const imagesAnalyzed = result.images_analyzed || 1;
  const hasDiscrepancies = result.discrepancies && result.discrepancies.length > 0;

  // Enhanced identification fields
  const analysisConfidence = result.analysis_confidence || 100;
  const hasEnhancedData = result.reasoning || result.visible_components?.length > 0 || result.ambiguities?.length > 0;

  // Format completeness status for display
  const getCompletenessLabel = (status: string) => {
    const labels: Record<string, string> = {
      'complete_set': 'Complete Set',
      'incomplete_set': 'Incomplete Set',
      'accessory_only': 'Accessory Only',
      'single_from_pair': 'Single from Pair',
      'unknown': 'Unknown'
    };
    return labels[status] || status;
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-br from-blue-50 to-purple-50 border-2 border-blue-200 rounded-xl p-6 shadow-md">
        <div className="flex justify-between items-start mb-4">
          <h3 className="font-bold text-lg bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
            ✨ AI Analysis Complete
          </h3>
          <div className="text-right">
            <div className={`inline-block px-3 py-1 rounded-full font-bold ${getConfidenceColor(confidenceScore)}`}>
              {confidenceScore}% Confidence
            </div>
            {imagesAnalyzed > 1 && (
              <div className="text-xs text-gray-600 mt-1">
                {imagesAnalyzed} images analyzed
              </div>
            )}
          </div>
        </div>

        {result.verification_notes && imagesAnalyzed > 1 && (
          <div className="mb-4 p-3 bg-white/70 rounded-lg text-sm text-gray-700">
            {result.verification_notes}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-600">Product:</span>{' '}
            <span className="font-medium">{result.product_name}</span>
          </div>
          {result.brand && (
            <div>
              <span className="text-gray-600">Brand:</span>{' '}
              <span className="font-medium">{result.brand}</span>
            </div>
          )}
          {result.color && (
            <div>
              <span className="text-gray-600">Color:</span>{' '}
              <span className="font-medium">{result.color}</span>
            </div>
          )}
          {result.material && (
            <div>
              <span className="text-gray-600">Material:</span>{' '}
              <span className="font-medium">{result.material}</span>
            </div>
          )}
        </div>

        {/* Discrepancies Section - Enhanced UX - Collapsible */}
        {hasDiscrepancies && (
          <div className="mt-4 border-2 border-yellow-300 rounded-xl overflow-hidden shadow-sm">
            {/* Header - Clickable */}
            <button
              onClick={() => setShowDiscrepancies(!showDiscrepancies)}
              className="w-full bg-gradient-to-r from-yellow-100 to-amber-100 px-4 py-3 hover:from-yellow-150 hover:to-amber-150 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="bg-yellow-500 p-1.5 rounded-lg">
                    <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="text-left">
                    <h4 className="font-bold text-yellow-900">
                      Image Differences Detected
                    </h4>
                    <p className="text-xs text-yellow-700">
                      {result.discrepancies.length} field{result.discrepancies.length > 1 ? 's' : ''} had different values across images
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-xs text-yellow-700 font-medium">
                    {imagesAnalyzed} images compared
                  </div>
                  <svg
                    className={`w-5 h-5 text-yellow-700 transition-transform ${showDiscrepancies ? 'rotate-180' : ''}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
            </button>

            {/* Discrepancy Cards - Conditionally Shown */}
            {showDiscrepancies && (
              <div className="bg-white p-4 space-y-3 border-t border-yellow-300">
                {result.discrepancies.map((disc, idx) => (
                  <div key={idx} className="bg-gradient-to-br from-yellow-50 to-amber-50 border border-yellow-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                    <div className="flex items-start gap-3">
                      {/* Field Icon */}
                      <div className="flex-shrink-0 mt-0.5">
                        <div className="w-8 h-8 bg-yellow-200 rounded-lg flex items-center justify-center">
                          <svg className="w-4 h-4 text-yellow-700" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                        </div>
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        {/* Field Name */}
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-bold text-yellow-900 capitalize">
                            {disc.field_name.replace(/_/g, ' ')}
                          </span>
                          <span className="text-xs bg-yellow-200 text-yellow-800 px-2 py-0.5 rounded-full font-medium">
                            Conflict
                          </span>
                        </div>

                        {/* Values */}
                        <div className="space-y-2">
                          <div className="flex flex-wrap gap-2">
                            {disc.values.map((value, vIdx) => (
                              <div key={vIdx} className="group relative">
                                <div className="bg-white border-2 border-yellow-300 rounded-lg px-3 py-1.5 text-sm font-medium text-gray-800 hover:border-yellow-400 transition-colors">
                                  {value || '(not detected)'}
                                </div>
                              </div>
                            ))}
                          </div>

                          {/* Confidence Impact */}
                          <div className="flex items-start gap-2 mt-2">
                            <svg className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            <p className="text-xs text-yellow-700 leading-relaxed">
                              {disc.confidence_impact}
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}

                {/* Info Footer */}
                <div className="mt-4 pt-3 border-t border-yellow-200">
                  <div className="flex items-start gap-2 bg-blue-50 rounded-lg p-3">
                    <svg className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    <div className="text-xs text-blue-800">
                      <span className="font-semibold">How we handled this:</span> The values shown in the listing below are based on the most common data found across all {imagesAnalyzed} images. Where conflicts existed, we selected the value that appeared most frequently.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* AI Reasoning Section - Collapsible */}
        {hasEnhancedData && (
          <div className="mt-4 border-2 border-blue-200 rounded-lg overflow-hidden">
            <button
              onClick={() => setShowReasoning(!showReasoning)}
              className="w-full p-4 bg-blue-50 hover:bg-blue-100 transition-colors flex items-center justify-between"
            >
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <span className="font-semibold text-blue-800">Show AI's Reasoning</span>
                <span className="text-xs text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full">
                  {analysisConfidence}% confidence
                </span>
              </div>
              <svg
                className={`w-5 h-5 text-blue-600 transition-transform ${showReasoning ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>

            {showReasoning && (
              <div className="p-4 bg-white space-y-4">
                {/* Reasoning */}
                {result.reasoning && (
                  <div>
                    <h5 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                      <span className="text-blue-600">💡</span>
                      Why this product identification:
                    </h5>
                    <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg italic">
                      "{result.reasoning}"
                    </p>
                  </div>
                )}

                {/* Visible Components */}
                {result.visible_components && result.visible_components.length > 0 && (
                  <div>
                    <h5 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                      <span className="text-green-600">👁️</span>
                      Components detected:
                    </h5>
                    <div className="flex flex-wrap gap-2">
                      {result.visible_components.map((component, idx) => (
                        <span key={idx} className="text-xs bg-green-50 text-green-700 px-3 py-1 rounded-full border border-green-200">
                          {component}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Completeness Status */}
                {result.completeness_status && result.completeness_status !== 'unknown' && (
                  <div>
                    <h5 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                      <span className="text-purple-600">📦</span>
                      Completeness:
                    </h5>
                    <span className={`inline-block text-sm px-3 py-1 rounded-full font-medium ${
                      result.completeness_status === 'complete_set' ? 'bg-green-100 text-green-700' :
                      result.completeness_status === 'incomplete_set' ? 'bg-orange-100 text-orange-700' :
                      result.completeness_status === 'accessory_only' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {getCompletenessLabel(result.completeness_status)}
                    </span>
                  </div>
                )}

                {/* Missing Components */}
                {result.missing_components && result.missing_components.length > 0 && (
                  <div>
                    <h5 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                      <span className="text-red-600">⚠️</span>
                      Missing components:
                    </h5>
                    <ul className="list-disc list-inside text-sm text-red-700 bg-red-50 p-3 rounded-lg">
                      {result.missing_components.map((component, idx) => (
                        <li key={idx}>{component}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Ambiguities */}
                {result.ambiguities && result.ambiguities.length > 0 && (
                  <div>
                    <h5 className="font-semibold text-gray-800 mb-2 flex items-center gap-2">
                      <span className="text-yellow-600">❓</span>
                      Uncertainties:
                    </h5>
                    <ul className="list-disc list-inside text-sm text-yellow-700 bg-yellow-50 p-3 rounded-lg">
                      {result.ambiguities.map((ambiguity, idx) => (
                        <li key={idx}>{ambiguity}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* eBay Category Section */}
      {result.ebay_category && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          <button
            onClick={() => setShowEbayCategory(!showEbayCategory)}
            className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
              </svg>
              <h3 className="text-lg font-semibold text-gray-900">eBay Category</h3>
              <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
                {Math.round((result.ebay_category.selection_confidence || 0) * 100)}% confidence
              </span>
            </div>
            <svg
              className={`w-5 h-5 transition-transform ${showEbayCategory ? 'rotate-90' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          {showEbayCategory && (
            <div className="p-4 border-t border-gray-200 bg-gray-50 space-y-4">
              <div className="bg-white rounded-lg p-4 border border-indigo-200">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-1">
                    <div className="w-8 h-8 bg-indigo-100 rounded-lg flex items-center justify-center">
                      <span className="text-indigo-700 font-bold text-sm">{result.ebay_category.category_id}</span>
                    </div>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-gray-900 mb-1">{result.ebay_category.category_name}</h4>
                    <p className="text-sm text-gray-600">{result.ebay_category.category_path}</p>
                    {result.ebay_category.selection_reasoning && (
                      <p className="text-sm text-gray-700 mt-2 italic bg-gray-50 p-2 rounded">
                        {result.ebay_category.selection_reasoning}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* eBay Aspects/Item Specifics Section */}
      {result.ebay_aspects && Object.keys(result.ebay_aspects).length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          <button
            onClick={() => setShowEbayAspects(!showEbayAspects)}
            className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
              </svg>
              <h3 className="text-lg font-semibold text-gray-900">eBay Item Specifics</h3>
              <span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                {Object.keys(result.ebay_aspects).length} aspects
              </span>
            </div>
            <svg
              className={`w-5 h-5 transition-transform ${showEbayAspects ? 'rotate-90' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </button>

          {showEbayAspects && (
            <div className="p-4 border-t border-gray-200 bg-gray-50">
              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Aspect
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Value
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {Object.entries(result.ebay_aspects).map(([name, value]) => (
                      <tr key={name} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">
                          {name}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-700">
                          {Array.isArray(value) ? value.join(', ') : value}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Product Attributes Display */}
      <AttributesDisplay result={result} />

      {/* Title */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <label htmlFor="title" className="block text-sm font-medium text-gray-700">
            Listing Title
          </label>
          <div className="flex items-center gap-2">
            <span className={`text-sm ${titleCharCount > 200 ? 'text-red-600' : 'text-gray-500'}`}>
              {titleCharCount} characters
            </span>
            <CopyButton text={title} />
          </div>
        </div>
        <textarea
          id="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
          aria-label="Listing title"
        />
      </div>

      {/* Description */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <label htmlFor="description" className="block text-sm font-medium text-gray-700">
            Description
          </label>
          <CopyButton text={description} />
        </div>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={8}
          className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
          aria-label="Product description"
        />
      </div>

      {/* Category, Condition, and Price */}
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-2">
          <label htmlFor="category" className="block text-sm font-medium text-gray-700">
            Category
          </label>
          <input
            id="category"
            type="text"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            placeholder="e.g., Electronics"
            aria-label="Product category"
          />
        </div>

        <div className="space-y-2">
          <label htmlFor="condition" className="block text-sm font-medium text-gray-700">
            Condition
          </label>
          <select
            id="condition"
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            aria-label="Product condition"
          >
            <option value="New">New</option>
            <option value="Used - Like New">Used - Like New</option>
            <option value="Used - Good">Used - Good</option>
            <option value="Used - Fair">Used - Fair</option>
            <option value="Refurbished">Refurbished</option>
          </select>
        </div>

        <div className="space-y-2">
          <label htmlFor="price" className="block text-sm font-medium text-gray-700">
            Listing Price
          </label>
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500 font-medium">
              $
            </span>
            <input
              id="price"
              type="number"
              value={priceInput}
              onChange={(e) => handlePriceChange(e.target.value)}
              step="0.01"
              min="0"
              placeholder="0.00"
              className="w-full pl-7 pr-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              aria-label="Listing price"
            />
          </div>
        </div>
      </div>

      {/* Key Features - hidden from UI but data preserved for listing */}
    </div>
  );
}
