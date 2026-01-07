import { useState } from 'react';
import { AnalysisResult } from '../types';

interface RawJsonDisplayProps {
  result: AnalysisResult;
}

export default function RawJsonDisplay({ result }: RawJsonDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg
            className={`w-5 h-5 transition-transform ${isExpanded ? 'rotate-90' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          <h3 className="text-lg font-semibold text-gray-900">Raw JSON Response</h3>
        </div>
        <div className="flex items-center gap-3">
          {result.ebay_category && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
              eBay Category
            </span>
          )}
          {result.ebay_aspects && Object.keys(result.ebay_aspects).length > 0 && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-100 text-indigo-800">
              {Object.keys(result.ebay_aspects).length} eBay Aspects
            </span>
          )}
          <span className="text-sm text-gray-500">
            {isExpanded ? 'Hide' : 'Show'} Details
          </span>
        </div>
      </button>

      {isExpanded && (
        <div className="p-4 border-t border-gray-200 bg-gray-50">
          {/* eBay Category Section */}
          {result.ebay_category && (
            <div className="mb-4 bg-white rounded-lg p-4 border border-purple-200">
              <h4 className="text-sm font-semibold text-purple-700 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
                </svg>
                eBay Category
              </h4>
              <pre className="text-xs text-gray-800 overflow-x-auto bg-purple-50 p-3 rounded border border-purple-100">
                {JSON.stringify(result.ebay_category, null, 2)}
              </pre>
            </div>
          )}

          {/* eBay Aspects Section */}
          {result.ebay_aspects && Object.keys(result.ebay_aspects).length > 0 && (
            <div className="mb-4 bg-white rounded-lg p-4 border border-indigo-200">
              <h4 className="text-sm font-semibold text-indigo-700 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M7 3a1 1 0 000 2h6a1 1 0 100-2H7zM4 7a1 1 0 011-1h10a1 1 0 110 2H5a1 1 0 01-1-1zM2 11a2 2 0 012-2h12a2 2 0 012 2v4a2 2 0 01-2 2H4a2 2 0 01-2-2v-4z" />
                </svg>
                eBay Aspects ({Object.keys(result.ebay_aspects).length})
              </h4>
              <pre className="text-xs text-gray-800 overflow-x-auto bg-indigo-50 p-3 rounded border border-indigo-100">
                {JSON.stringify(result.ebay_aspects, null, 2)}
              </pre>
            </div>
          )}

          {/* Complete JSON Section */}
          <div className="bg-white rounded-lg p-4 border border-gray-300">
            <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M12.316 3.051a1 1 0 01.633 1.265l-4 12a1 1 0 11-1.898-.632l4-12a1 1 0 011.265-.633zM5.707 6.293a1 1 0 010 1.414L3.414 10l2.293 2.293a1 1 0 11-1.414 1.414l-3-3a1 1 0 010-1.414l3-3a1 1 0 011.414 0zm8.586 0a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 11-1.414-1.414L16.586 10l-2.293-2.293a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
              Complete JSON Response
            </h4>
            <div className="relative">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(result, null, 2));
                  alert('JSON copied to clipboard!');
                }}
                className="absolute top-2 right-2 px-3 py-1 text-xs bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                Copy
              </button>
              <pre className="text-xs text-gray-800 overflow-x-auto bg-gray-100 p-3 rounded border border-gray-200 max-h-96 overflow-y-auto">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          </div>

          {/* Info Footer */}
          <div className="mt-4 flex items-center justify-between text-xs text-gray-500">
            <div className="flex items-center gap-2">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <span>This is the complete analysis response from the backend</span>
            </div>
            {result.analysis_id && (
              <span className="font-mono bg-gray-200 px-2 py-1 rounded">
                ID: {result.analysis_id}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
