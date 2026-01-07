import { useState, useEffect } from 'react';
import type { AnalysisResult, CategoryRecommendation, CategoryAspects, FormattedAspect } from '../types';

interface CategoryAspectsSectionProps {
  result: AnalysisResult;
}

interface AspectValues {
  [aspectName: string]: string | string[];
}

export function CategoryAspectsSection({ result }: CategoryAspectsSectionProps) {
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(
    result.suggested_category_id || null
  );
  const [aspectValues, setAspectValues] = useState<AspectValues>({});
  const [showAllCategories, setShowAllCategories] = useState(false);

  // Get category suggestions
  const categorySuggestions = result.ebay_category_suggestions || [];
  const hasCategories = categorySuggestions.length > 0;

  // Get aspects for selected category
  const currentAspects = selectedCategoryId === result.suggested_category_id
    ? result.suggested_category_aspects
    : null;

  // DEBUG: Log to console
  console.log('CategoryAspectsSection - result:', result);
  console.log('CategoryAspectsSection - ebay_category_suggestions:', result.ebay_category_suggestions);
  console.log('CategoryAspectsSection - suggested_category_id:', result.suggested_category_id);
  console.log('CategoryAspectsSection - suggested_category_aspects:', result.suggested_category_aspects);
  console.log('CategoryAspectsSection - hasCategories:', hasCategories);

  if (!hasCategories) {
    console.log('CategoryAspectsSection - No categories found, returning null');
    return null;
  }

  const handleCategorySelect = (categoryId: string) => {
    setSelectedCategoryId(categoryId);
    // TODO: In Phase 2, we'll fetch aspects for this category if not already loaded
  };

  const handleAspectChange = (aspectName: string, value: string | string[]) => {
    setAspectValues(prev => ({
      ...prev,
      [aspectName]: value
    }));
  };

  const renderAspectInput = (aspect: FormattedAspect) => {
    const value = aspectValues[aspect.name] || (aspect.multi_select ? [] : '');

    if (aspect.input_type === 'dropdown') {
      if (aspect.multi_select) {
        // Multi-select dropdown
        return (
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700">
              {aspect.name}
              {aspect.required && <span className="text-red-500 ml-1">*</span>}
            </label>
            <div className="max-h-40 overflow-y-auto border rounded-lg p-2 bg-white">
              {aspect.values.map((val, idx) => (
                <label key={idx} className="flex items-center gap-2 p-1 hover:bg-gray-50 rounded">
                  <input
                    type="checkbox"
                    checked={Array.isArray(value) && value.includes(val.value)}
                    onChange={(e) => {
                      const currentValues = Array.isArray(value) ? value : [];
                      const newValues = e.target.checked
                        ? [...currentValues, val.value]
                        : currentValues.filter(v => v !== val.value);
                      handleAspectChange(aspect.name, newValues);
                    }}
                    className="rounded border-gray-300"
                  />
                  <span className="text-sm">{val.value}</span>
                </label>
              ))}
            </div>
          </div>
        );
      } else {
        // Single-select dropdown
        return (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {aspect.name}
              {aspect.required && <span className="text-red-500 ml-1">*</span>}
            </label>
            <select
              value={typeof value === 'string' ? value : ''}
              onChange={(e) => handleAspectChange(aspect.name, e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Select...</option>
              {aspect.values.map((val, idx) => (
                <option key={idx} value={val.value}>
                  {val.value}
                </option>
              ))}
            </select>
          </div>
        );
      }
    } else {
      // Text input
      return (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {aspect.name}
            {aspect.required && <span className="text-red-500 ml-1">*</span>}
            {aspect.max_length && (
              <span className="text-xs text-gray-500 ml-2">
                (max {aspect.max_length} chars)
              </span>
            )}
          </label>
          <input
            type="text"
            value={typeof value === 'string' ? value : ''}
            onChange={(e) => handleAspectChange(aspect.name, e.target.value)}
            maxLength={aspect.max_length}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder={`Enter ${aspect.name.toLowerCase()}...`}
          />
        </div>
      );
    }
  };

  const categoriesToShow = showAllCategories
    ? categorySuggestions
    : categorySuggestions.slice(0, 3);

  return (
    <div className="space-y-6">
      {/* Category Suggestions */}
      <div className="bg-gradient-to-br from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl p-6 shadow-md">
        <h3 className="font-bold text-xl bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent mb-4">
          eBay Category Suggestions
        </h3>

        <div className="space-y-3">
          {categoriesToShow.map((category, idx) => {
            const isSelected = selectedCategoryId === category.category_id;
            const isTopPick = idx === 0;

            return (
              <button
                key={category.category_id}
                onClick={() => handleCategorySelect(category.category_id)}
                className={`w-full text-left p-4 rounded-lg border-2 transition-all ${
                  isSelected
                    ? 'border-purple-500 bg-purple-100 shadow-lg'
                    : 'border-gray-200 bg-white hover:border-purple-300 hover:shadow-md'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-gray-900">
                        {category.category_name}
                      </span>
                      {isTopPick && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-bold rounded-full">
                          Top Pick
                        </span>
                      )}
                      {isSelected && (
                        <span className="text-purple-600">
                          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                          </svg>
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mb-2">
                      {category.category_path}
                    </p>
                    <p className="text-xs text-gray-500">
                      {category.reasoning}
                    </p>
                  </div>
                  <div className="flex-shrink-0">
                    <div className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-semibold">
                      {Math.round(category.confidence * 100)}%
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {categorySuggestions.length > 3 && (
          <button
            onClick={() => setShowAllCategories(!showAllCategories)}
            className="mt-3 w-full py-2 text-purple-600 hover:text-purple-700 font-medium text-sm transition-colors"
          >
            {showAllCategories ? '↑ Show Less' : `↓ Show ${categorySuggestions.length - 3} More Categories`}
          </button>
        )}
      </div>

      {/* Aspect Fields */}
      {currentAspects && selectedCategoryId && (
        <div className="bg-white border-2 border-gray-200 rounded-xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-xl text-gray-900">
              Item Specifics for {currentAspects.category_name}
            </h3>
            <div className="text-sm text-gray-600">
              <span className="font-semibold text-red-600">
                {currentAspects.counts.required} Required
              </span>
              <span className="mx-2">•</span>
              <span className="font-semibold text-yellow-600">
                {currentAspects.counts.recommended} Recommended
              </span>
              <span className="mx-2">•</span>
              <span className="text-gray-500">
                {currentAspects.counts.optional} Optional
              </span>
            </div>
          </div>

          {/* Required Aspects */}
          {currentAspects.aspects.required.length > 0 && (
            <div className="mb-6">
              <h4 className="font-bold text-md text-red-600 mb-3 flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Required Fields
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {currentAspects.aspects.required.map((aspect, idx) => (
                  <div key={idx}>
                    {renderAspectInput(aspect)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Aspects */}
          {currentAspects.aspects.recommended.length > 0 && (
            <div className="mb-6">
              <h4 className="font-bold text-md text-yellow-600 mb-3 flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                </svg>
                Recommended Fields
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {currentAspects.aspects.recommended.map((aspect, idx) => (
                  <div key={idx}>
                    {renderAspectInput(aspect)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Optional Aspects (collapsed by default) */}
          {currentAspects.aspects.optional.length > 0 && (
            <details className="group">
              <summary className="cursor-pointer font-bold text-md text-gray-600 mb-3 flex items-center gap-2 hover:text-gray-800">
                <svg className="w-5 h-5 transform group-open:rotate-90 transition-transform" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
                Optional Fields ({currentAspects.counts.optional})
              </summary>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                {currentAspects.aspects.optional.map((aspect, idx) => (
                  <div key={idx}>
                    {renderAspectInput(aspect)}
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}

      {!currentAspects && selectedCategoryId && (
        <div className="bg-yellow-50 border-2 border-yellow-200 rounded-xl p-6 text-center">
          <p className="text-yellow-800 font-medium">
            Loading aspect fields for selected category...
          </p>
        </div>
      )}
    </div>
  );
}
