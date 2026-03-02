import { useState, useEffect } from 'react';
import type { AnalysisResult, FormattedAspect } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface CategoryAspectsSectionProps {
  result: AnalysisResult;
}

interface AspectValues {
  [aspectName: string]: string | string[];
}

// eBay API response format for item specifics
interface EbayItemSpecific {
  name: string;
  cardinality: 'SINGLE' | 'MULTI';
  usage: 'REQUIRED' | 'RECOMMENDED' | 'OPTIONAL';
  values?: string[];
  max_values?: number;
  constraint?: 'SELECTION_ONLY' | 'FREE_TEXT';
}

// Category suggestion format for display
interface CategorySuggestion {
  category_id: string;
  category_name: string;
  category_path: string;
  confidence: number;
  reasoning: string;
}

// Structured aspects data for form rendering
interface FormattedAspectsData {
  category_name: string;
  counts: {
    required: number;
    recommended: number;
    optional: number;
  };
  aspects: {
    required: FormattedAspect[];
    recommended: FormattedAspect[];
    optional: FormattedAspect[];
  };
}

export function CategoryAspectsSection({ result }: CategoryAspectsSectionProps) {
  // Build category suggestions from result.ebay_category (primary + alternatives)
  const categorySuggestions: CategorySuggestion[] = [];

  if (result.ebay_category) {
    // Add primary category
    categorySuggestions.push({
      category_id: result.ebay_category.category_id,
      category_name: result.ebay_category.category_name,
      category_path: result.ebay_category.category_path,
      confidence: result.ebay_category.selection_confidence || 0.9,
      reasoning: result.ebay_category.selection_reasoning || 'AI-selected category'
    });

    // Add alternatives if available
    if (result.ebay_category.alternatives_considered) {
      result.ebay_category.alternatives_considered.forEach(alt => {
        categorySuggestions.push({
          category_id: alt.category_id,
          category_name: alt.category_name,
          category_path: alt.category_name, // Use name as path since full path not available
          confidence: 0.7,
          reasoning: alt.rejection_reason || 'Alternative category'
        });
      });
    }
  }

  const hasCategories = categorySuggestions.length > 0;
  const primaryCategoryId = result.ebay_category?.category_id || null;

  // State
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(primaryCategoryId);
  const [aspectValues, setAspectValues] = useState<AspectValues>({});
  const [showAllCategories, setShowAllCategories] = useState(false);
  const [hasUserChangedCategory, setHasUserChangedCategory] = useState(false);

  // New state for fetched aspects from eBay API
  const [fetchedAspects, setFetchedAspects] = useState<FormattedAspectsData | null>(null);
  const [loadingAspects, setLoadingAspects] = useState(false);
  const [aspectsError, setAspectsError] = useState<string | null>(null);

  // DEBUG: Log to console
  console.log('🔍 CategoryAspectsSection - ebay_category:', result.ebay_category);
  console.log('🔍 CategoryAspectsSection - Built categorySuggestions:', categorySuggestions);
  console.log('🔍 CategoryAspectsSection - primaryCategoryId:', primaryCategoryId);
  console.log('🔍 CategoryAspectsSection - ebay_aspects:', result.ebay_aspects);

  if (!hasCategories) {
    console.log('CategoryAspectsSection - No categories found, returning null');
    return null;
  }

  // Transform eBay API response to FormattedAspect format
  const transformApiResponse = (
    apiAspects: EbayItemSpecific[],
    categoryName: string
  ): FormattedAspectsData => {
    const required: FormattedAspect[] = [];
    const recommended: FormattedAspect[] = [];
    const optional: FormattedAspect[] = [];

    apiAspects.forEach(spec => {
      const formattedAspect: FormattedAspect = {
        name: spec.name,
        required: spec.usage === 'REQUIRED',
        input_type: (spec.constraint === 'SELECTION_ONLY' && spec.values && spec.values.length > 0)
          ? 'dropdown'
          : 'text',
        values: (spec.values || []).map(v => ({ value: v })),
        multi_select: spec.cardinality === 'MULTI',
        max_length: undefined,
        // Additional required properties
        data_type: 'string',
        usage: spec.usage,
        enabled_for_variations: false,
        applicable_to: ['ITEM']
      };

      if (spec.usage === 'REQUIRED') {
        required.push(formattedAspect);
      } else if (spec.usage === 'RECOMMENDED') {
        recommended.push(formattedAspect);
      } else {
        optional.push(formattedAspect);
      }
    });

    return {
      category_name: categoryName,
      counts: {
        required: required.length,
        recommended: recommended.length,
        optional: optional.length
      },
      aspects: { required, recommended, optional }
    };
  };

  // Fetch item specifics from eBay API when category changes
  useEffect(() => {
    if (!selectedCategoryId) {
      setFetchedAspects(null);
      return;
    }

    const fetchAspects = async () => {
      setLoadingAspects(true);
      setAspectsError(null);

      try {
        console.log(`🔄 Fetching item specifics for category: ${selectedCategoryId}`);
        const response = await fetch(
          `${API_BASE_URL}/api/ebay/categories/${selectedCategoryId}/item-specifics`
        );

        if (!response.ok) {
          if (response.status === 404) {
            console.log('Item specifics endpoint not available - skipping');
            setFetchedAspects(null);
            setLoadingAspects(false);
            return;
          }
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch item specifics');
        }

        const data = await response.json();
        const apiAspects: EbayItemSpecific[] = data.item_specifics || [];

        // Get category name from suggestions
        const category = categorySuggestions.find(c => c.category_id === selectedCategoryId);
        const categoryName = category?.category_name || 'Selected Category';

        // Transform to FormattedAspectsData
        const formatted = transformApiResponse(apiAspects, categoryName);
        console.log('✅ Fetched and transformed aspects:', formatted);
        setFetchedAspects(formatted);

      } catch (err: any) {
        console.error('Failed to fetch item specifics:', err);
        setAspectsError(err.message || 'Failed to load item specifics');
        setFetchedAspects(null);
      } finally {
        setLoadingAspects(false);
      }
    };

    fetchAspects();
  }, [selectedCategoryId]);

  // Prepopulate aspects with LLM-predicted values (only for primary category)
  const prepopulateAspects = () => {
    console.log('🔍 prepopulateAspects called');
    console.log('  - result.ebay_aspects:', result.ebay_aspects);
    console.log('  - fetchedAspects:', fetchedAspects);

    if (!result.ebay_aspects || !fetchedAspects) {
      console.log('  ❌ Missing data - skipping prepopulation');
      return;
    }

    const newValues: AspectValues = {};
    const allAspects = [
      ...fetchedAspects.aspects.required,
      ...fetchedAspects.aspects.recommended,
      ...fetchedAspects.aspects.optional
    ];

    console.log('  - Total aspects to check:', allAspects.length);
    console.log('  - LLM aspect keys:', Object.keys(result.ebay_aspects));

    // Iterate through all aspects for this category
    allAspects.forEach((aspect) => {
      // Case-insensitive search for matching LLM aspect
      const llmAspectKey = Object.keys(result.ebay_aspects!).find(
        (key) => key.toLowerCase() === aspect.name.toLowerCase()
      );

      if (llmAspectKey) {
        const llmValue = result.ebay_aspects![llmAspectKey];
        console.log(`  ✓ Match found: ${aspect.name} = ${JSON.stringify(llmValue)}`);

        // For dropdown fields, validate that the value matches
        if (aspect.input_type === 'dropdown' && aspect.values.length > 0) {
          if (aspect.multi_select) {
            // Multi-select dropdown: filter out values that don't match
            const values = Array.isArray(llmValue) ? llmValue : [llmValue];
            const matchedValues = values.filter((v) =>
              aspect.values.some((av) => av.value.toLowerCase() === String(v).toLowerCase())
            );
            if (matchedValues.length > 0) {
              newValues[aspect.name] = matchedValues;
              console.log(`    → Set multi-select: ${aspect.name} = ${JSON.stringify(matchedValues)}`);
            } else {
              console.log(`    ⚠ No matching dropdown values for ${aspect.name}`);
            }
          } else {
            // Single-select dropdown: only set if value matches
            const valueStr = Array.isArray(llmValue) ? llmValue[0] : String(llmValue);
            const matchedValue = aspect.values.find(
              (av) => av.value.toLowerCase() === valueStr.toLowerCase()
            );
            if (matchedValue) {
              newValues[aspect.name] = matchedValue.value;
              console.log(`    → Set dropdown: ${aspect.name} = ${matchedValue.value}`);
            } else {
              console.log(`    ⚠ No matching dropdown value for ${aspect.name} (tried: ${valueStr})`);
            }
          }
        } else {
          // Free text field: use the value directly
          newValues[aspect.name] = llmValue;
          console.log(`    → Set text field: ${aspect.name} = ${JSON.stringify(llmValue)}`);
        }
      }
    });

    console.log('  📝 Final values to set:', newValues);
    console.log('  📝 Number of values:', Object.keys(newValues).length);
    setAspectValues(newValues);
  };

  // Prepopulate when aspects are fetched (only for primary category, not user-changed)
  useEffect(() => {
    console.log('🔄 Prepopulation useEffect triggered');
    console.log('  - hasUserChangedCategory:', hasUserChangedCategory);
    console.log('  - selectedCategoryId:', selectedCategoryId);
    console.log('  - primaryCategoryId:', primaryCategoryId);
    console.log('  - fetchedAspects exists:', !!fetchedAspects);
    console.log('  - result.ebay_aspects exists:', !!result.ebay_aspects);

    // Only prepopulate for the primary category (not when user manually changes)
    if (
      !hasUserChangedCategory &&
      selectedCategoryId === primaryCategoryId &&
      fetchedAspects &&
      result.ebay_aspects
    ) {
      console.log('  ✅ All conditions met - calling prepopulateAspects');
      prepopulateAspects();
    } else {
      console.log('  ❌ Conditions not met - skipping prepopulation');
    }
  }, [fetchedAspects, result.ebay_aspects, hasUserChangedCategory]);

  const handleCategorySelect = (categoryId: string) => {
    setSelectedCategoryId(categoryId);
    setHasUserChangedCategory(true);
    // Clear all aspect values when user manually changes category
    setAspectValues({});
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

      {/* Loading State */}
      {loadingAspects && selectedCategoryId && (
        <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-6 text-center">
          <div className="flex items-center justify-center gap-3">
            <svg className="animate-spin h-5 w-5 text-blue-600" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <p className="text-blue-800 font-medium">
              Loading item specifics for selected category...
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {aspectsError && selectedCategoryId && (
        <div className="bg-red-50 border-2 border-red-200 rounded-xl p-6">
          <div className="flex items-start gap-3">
            <svg className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div className="flex-1">
              <p className="text-red-800 font-medium">Couldn't load item specifics for this category.</p>
              <p className="text-red-600 text-sm mt-1">{aspectsError}</p>
              <div className="mt-3 flex items-center gap-3">
                <button
                  onClick={() => {
                    setAspectsError(null);
                    // Re-trigger the useEffect by toggling
                    const catId = selectedCategoryId;
                    setSelectedCategoryId(null);
                    setTimeout(() => setSelectedCategoryId(catId), 0);
                  }}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  Retry
                </button>
                <button
                  onClick={() => setAspectsError(null)}
                  className="text-sm text-gray-600 hover:text-gray-800 underline"
                >
                  Continue without item specifics
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Aspect Fields */}
      {fetchedAspects && selectedCategoryId && !loadingAspects && (
        <div className="bg-white border-2 border-gray-200 rounded-xl p-6 shadow-md">
          <div className="flex items-center justify-between mb-6">
            <h3 className="font-bold text-xl text-gray-900">
              Item Specifics for {fetchedAspects.category_name}
            </h3>
            <div className="text-sm text-gray-600">
              <span className="font-semibold text-red-600">
                {fetchedAspects.counts.required} Required
              </span>
              <span className="mx-2">•</span>
              <span className="font-semibold text-yellow-600">
                {fetchedAspects.counts.recommended} Recommended
              </span>
              <span className="mx-2">•</span>
              <span className="text-gray-500">
                {fetchedAspects.counts.optional} Optional
              </span>
            </div>
          </div>

          {/* Required Aspects */}
          {fetchedAspects.aspects.required.length > 0 && (
            <div className="mb-6">
              <h4 className="font-bold text-md text-red-600 mb-3 flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                Required Fields
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {fetchedAspects.aspects.required.map((aspect, idx) => (
                  <div key={idx}>
                    {renderAspectInput(aspect)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Aspects */}
          {fetchedAspects.aspects.recommended.length > 0 && (
            <div className="mb-6">
              <h4 className="font-bold text-md text-yellow-600 mb-3 flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
                </svg>
                Recommended Fields
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {fetchedAspects.aspects.recommended.map((aspect, idx) => (
                  <div key={idx}>
                    {renderAspectInput(aspect)}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Optional Aspects (collapsed by default) */}
          {fetchedAspects.aspects.optional.length > 0 && (
            <details className="group">
              <summary className="cursor-pointer font-bold text-md text-gray-600 mb-3 flex items-center gap-2 hover:text-gray-800">
                <svg className="w-5 h-5 transform group-open:rotate-90 transition-transform" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd" />
                </svg>
                Optional Fields ({fetchedAspects.counts.optional})
              </summary>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                {fetchedAspects.aspects.optional.map((aspect, idx) => (
                  <div key={idx}>
                    {renderAspectInput(aspect)}
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
}
