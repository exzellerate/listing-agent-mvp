import { useState } from 'react';
import { AnalysisResult } from '../types';

interface AttributesDisplayProps {
  result: AnalysisResult;
}

export default function AttributesDisplay({ result }: AttributesDisplayProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Don't render if no attributes data
  if (!result.product_attributes && !result.extracted_attributes) {
    return null;
  }

  const hasProductAttributes = result.product_attributes && Object.keys(result.product_attributes).length > 0;
  const hasExtractedAttributes = result.extracted_attributes && Object.keys(result.extracted_attributes).length > 0;

  const renderAttributeValue = (value: any): string => {
    if (Array.isArray(value)) {
      return value.join(', ');
    }
    if (value === null || value === undefined) {
      return 'N/A';
    }
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return String(value);
  };

  const formatKey = (key: string): string => {
    return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  };

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
          <h3 className="text-lg font-semibold text-gray-900">Product Attributes</h3>
        </div>
        <span className="text-sm text-gray-500">
          {isExpanded ? 'Hide' : 'Show'} Details
        </span>
      </button>

      {isExpanded && (
        <div className="p-4 border-t border-gray-200 bg-gray-50 space-y-4">
          {/* Standard Product Attributes */}
          {hasProductAttributes && (
            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <h4 className="text-sm font-semibold text-blue-700 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                </svg>
                Standard Attributes
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(result.product_attributes!).map(([key, value]) => {
                  if (key === 'additional_attributes') return null;
                  return (
                    <div key={key} className="flex flex-col">
                      <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                        {formatKey(key)}
                      </span>
                      <span className="text-sm text-gray-900 mt-1">
                        {renderAttributeValue(value)}
                      </span>
                    </div>
                  );
                })}
              </div>

              {/* Additional Attributes */}
              {result.product_attributes.additional_attributes &&
               Object.keys(result.product_attributes.additional_attributes).length > 0 && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h5 className="text-xs font-semibold text-gray-600 mb-2">Additional Attributes</h5>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {Object.entries(result.product_attributes.additional_attributes).map(([key, value]) => (
                      <div key={key} className="flex flex-col">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                          {formatKey(key)}
                        </span>
                        <span className="text-sm text-gray-900 mt-1">
                          {renderAttributeValue(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Extracted Attributes */}
          {hasExtractedAttributes && (
            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <h4 className="text-sm font-semibold text-green-700 mb-3 flex items-center gap-2">
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z" clipRule="evenodd" />
                </svg>
                Extracted Attributes
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(result.extracted_attributes!).map(([key, value]) => (
                  <div key={key} className="flex flex-col">
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                      {formatKey(key)}
                    </span>
                    <span className="text-sm text-gray-900 mt-1">
                      {renderAttributeValue(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Summary Badge */}
          <div className="flex items-center justify-between pt-2">
            <div className="flex gap-2">
              {hasProductAttributes && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                  {Object.keys(result.product_attributes!).filter(k => k !== 'additional_attributes').length} Standard
                </span>
              )}
              {hasExtractedAttributes && (
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                  {Object.keys(result.extracted_attributes!).length} Extracted
                </span>
              )}
            </div>
            <span className="text-xs text-gray-500">
              These attributes were automatically detected from your images
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
