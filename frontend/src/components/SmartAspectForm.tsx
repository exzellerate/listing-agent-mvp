import { useState, useEffect } from 'react';
import { AlertCircle, Loader2, Sparkles, CheckCircle, Eye, Brain, HelpCircle } from 'lucide-react';
import { PredictedAspect, CategoryAspectResponse } from '../types';
import { analyzeCategoryAspects } from '../services/api';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ItemSpecific {
  name: string;
  cardinality: 'SINGLE' | 'MULTI';
  usage: 'REQUIRED' | 'RECOMMENDED' | 'OPTIONAL';
  values?: string[];
  max_values?: number;
  constraint?: 'SELECTION_ONLY' | 'FREE_TEXT';
}

interface SmartAspectFormProps {
  analysisId: number;
  categoryId: string;
  categoryName: string;
  initialValues?: Record<string, string | string[]>;
  onChange: (specifics: Record<string, string | string[]>) => void;
  errors?: Record<string, string>;
}

export default function SmartAspectForm({
  analysisId,
  categoryId,
  categoryName,
  initialValues = {},
  onChange,
  errors = {}
}: SmartAspectFormProps) {
  const [itemSpecifics, setItemSpecifics] = useState<ItemSpecific[]>([]);
  const [loadingSpecifics, setLoadingSpecifics] = useState(false);
  const [specificsError, setSpecificsError] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string | string[]>>(initialValues);
  const [predictions, setPredictions] = useState<Record<string, PredictedAspect>>({});
  const [loadingPredictions, setLoadingPredictions] = useState(false);
  const [predictionError, setPredictionError] = useState<string | null>(null);
  const [showAllFields, setShowAllFields] = useState(false);

  useEffect(() => {
    setFormValues(initialValues);
  }, [initialValues]);

  // Fetch item specifics when category changes
  useEffect(() => {
    if (categoryId) {
      fetchItemSpecifics();
    }
  }, [categoryId]);

  // Fetch predictions when item specifics are loaded
  useEffect(() => {
    if (analysisId && categoryId && itemSpecifics.length > 0) {
      fetchPredictions();
    }
  }, [analysisId, categoryId, itemSpecifics]);

  const fetchItemSpecifics = async () => {
    setLoadingSpecifics(true);
    setSpecificsError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/ebay/categories/${categoryId}/item-specifics`
      );

      if (!response.ok) {
        if (response.status === 404) {
          console.log('Item specifics endpoint not available - skipping');
          setItemSpecifics([]);
          setSpecificsError(null);
          setLoadingSpecifics(false);
          return;
        }

        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch item specifics');
      }

      const data = await response.json();
      setItemSpecifics(data.item_specifics || []);
    } catch (err: any) {
      console.error('Failed to fetch item specifics:', err);
      if (!err.message?.includes('404')) {
        setSpecificsError(err.message || 'Failed to load item specifics for this category');
      }
      setItemSpecifics([]);
    } finally {
      setLoadingSpecifics(false);
    }
  };

  // Helper function to find matching value in dropdown options
  const findMatchingValue = (predictedValue: string, availableValues: string[]): string | null => {
    if (!predictedValue || !availableValues || availableValues.length === 0) {
      return null;
    }

    const normalized = predictedValue.trim().toLowerCase();

    // Try exact match first
    const exactMatch = availableValues.find(v => v.toLowerCase() === normalized);
    if (exactMatch) {
      console.log(`✓ Exact match found: "${predictedValue}" -> "${exactMatch}"`);
      return exactMatch;
    }

    // Try partial match (predicted value contains option or vice versa)
    const partialMatch = availableValues.find(v => {
      const optionNorm = v.toLowerCase();
      return normalized.includes(optionNorm) || optionNorm.includes(normalized);
    });

    if (partialMatch) {
      console.log(`✓ Partial match found: "${predictedValue}" -> "${partialMatch}"`);
      return partialMatch;
    }

    console.warn(`✗ No match found for "${predictedValue}" in options:`, availableValues);
    return null;
  };

  const fetchPredictions = async () => {
    setLoadingPredictions(true);
    setPredictionError(null);

    try {
      const response: CategoryAspectResponse = await analyzeCategoryAspects({
        analysis_id: analysisId,
        category_id: categoryId
      });

      console.log('📊 AI Predictions received:', response.aspect_analysis.predicted_aspects);
      setPredictions(response.aspect_analysis.predicted_aspects);

      // Smart auto-populate: validate against available options
      const autoPopulated = response.aspect_analysis.auto_populate_fields;
      console.log('🎯 Auto-populate candidates:', autoPopulated);

      if (Object.keys(autoPopulated).length > 0) {
        const validatedValues: Record<string, string | string[]> = { ...formValues };
        let appliedCount = 0;
        let skippedCount = 0;

        Object.entries(autoPopulated).forEach(([aspectName, predictedValue]) => {
          // Find the aspect definition to check if it has predefined values
          const aspectDef = itemSpecifics.find(s => s.name === aspectName);

          if (!aspectDef) {
            console.warn(`⚠️ Aspect "${aspectName}" not found in item specifics`);
            skippedCount++;
            return;
          }

          // If aspect has predefined values, validate the predicted value
          if (aspectDef.values && aspectDef.values.length > 0) {
            const matchedValue = findMatchingValue(predictedValue as string, aspectDef.values);

            if (matchedValue) {
              validatedValues[aspectName] = matchedValue;
              appliedCount++;
              console.log(`✓ Applied: ${aspectName} = "${matchedValue}"`);
            } else {
              skippedCount++;
              console.log(`✗ Skipped: ${aspectName} (no matching option for "${predictedValue}")`);
            }
          } else {
            // Free text field - accept as-is
            validatedValues[aspectName] = predictedValue;
            appliedCount++;
            console.log(`✓ Applied (free text): ${aspectName} = "${predictedValue}"`);
          }
        });

        console.log(`📈 Auto-population summary: ${appliedCount} applied, ${skippedCount} skipped`);

        setFormValues(validatedValues);
        onChange(validatedValues);
      }
    } catch (err: any) {
      console.error('Failed to fetch aspect predictions:', err);
      setPredictionError(err.message || 'Failed to get AI predictions');
    } finally {
      setLoadingPredictions(false);
    }
  };

  const handleInputChange = (name: string, value: string | string[]) => {
    const newValues = {
      ...formValues,
      [name]: value
    };
    setFormValues(newValues);
    onChange(newValues);
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.75) return 'text-green-600 bg-green-50 border-green-200';
    if (confidence >= 0.5) return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    return 'text-gray-500 bg-gray-50 border-gray-200';
  };

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.75) return CheckCircle;
    if (confidence >= 0.5) return Brain;
    return HelpCircle;
  };

  const getSourceIcon = (source: string) => {
    if (source === 'visible') return Eye;
    if (source === 'inferred') return Brain;
    return HelpCircle;
  };

  const getSourceLabel = (source: string) => {
    if (source === 'visible') return 'Visible in image';
    if (source === 'inferred') return 'Inferred by AI';
    return 'Unknown source';
  };

  const renderPredictionBadge = (aspectName: string) => {
    const prediction = predictions[aspectName];
    if (!prediction || prediction.confidence === 0) return null;

    const ConfidenceIcon = getConfidenceIcon(prediction.confidence);
    const SourceIcon = getSourceIcon(prediction.source);

    return (
      <div className="mt-2 flex items-start gap-2">
        <div className={`flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border ${getConfidenceColor(prediction.confidence)}`}>
          <ConfidenceIcon className="w-4 h-4 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium">
                AI Prediction ({Math.round(prediction.confidence * 100)}%)
              </span>
              <SourceIcon className="w-3 h-3" title={getSourceLabel(prediction.source)} />
            </div>
            {prediction.value && (
              <p className="text-sm mt-0.5 truncate" title={prediction.value}>
                {prediction.value}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  };

  const renderInput = (specific: ItemSpecific) => {
    const value = formValues[specific.name] || (specific.cardinality === 'MULTI' ? [] : '');
    const isRequired = specific.usage === 'REQUIRED';
    const hasError = errors[specific.name];
    const prediction = predictions[specific.name];
    const isAutoPopulated = prediction && prediction.confidence >= 0.75;

    // Single value with predefined options
    if (specific.cardinality === 'SINGLE' && specific.values && specific.values.length > 0) {
      return (
        <div className="space-y-2">
          <select
            value={value as string}
            onChange={(e) => handleInputChange(specific.name, e.target.value)}
            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200 ${
              hasError ? 'border-red-500' : isAutoPopulated ? 'border-green-500 bg-green-50' : 'border-gray-300'
            }`}
          >
            <option value="">Select {specific.name}</option>
            {specific.values.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
          {renderPredictionBadge(specific.name)}
        </div>
      );
    }

    // Free text input
    return (
      <div className="space-y-2">
        <input
          type="text"
          value={value as string}
          onChange={(e) => handleInputChange(specific.name, e.target.value)}
          placeholder={`Enter ${specific.name}`}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200 ${
            hasError ? 'border-red-500' : isAutoPopulated ? 'border-green-500 bg-green-50' : 'border-gray-300'
          }`}
        />
        {renderPredictionBadge(specific.name)}
      </div>
    );
  };

  // Separate fields into categories
  const requiredFields = itemSpecifics.filter(s => s.usage === 'REQUIRED');
  const recommendedFields = itemSpecifics.filter(s => s.usage === 'RECOMMENDED');
  const optionalFields = itemSpecifics.filter(s => s.usage === 'OPTIONAL');

  // Count predicted fields
  const predictedCount = Object.keys(predictions).filter(k => predictions[k].confidence >= 0.75).length;
  const totalRequired = requiredFields.length;

  // Show loading state while fetching item specifics
  if (loadingSpecifics) {
    return (
      <div className="flex flex-col items-center justify-center py-12 space-y-4">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        <p className="text-sm text-gray-600">Loading category-specific fields...</p>
      </div>
    );
  }

  // Show error if failed to fetch item specifics
  if (specificsError) {
    return (
      <div className="flex items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
        <AlertCircle className="w-5 h-5 flex-shrink-0" />
        <span className="text-sm">{specificsError}</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with AI Status */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <Sparkles className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900 mb-1">
              AI-Powered Item Specifics for {categoryName}
            </h3>
            {loadingPredictions ? (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Analyzing product images to predict aspect values...</span>
              </div>
            ) : predictionError ? (
              <div className="flex items-center gap-2 text-sm text-red-600">
                <AlertCircle className="w-4 h-4" />
                <span>{predictionError}</span>
              </div>
            ) : predictedCount > 0 ? (
              <p className="text-sm text-gray-600">
                AI has auto-populated <span className="font-semibold text-green-600">{predictedCount}</span> fields with high confidence.
                {totalRequired > 0 && ` ${totalRequired} fields are required.`}
              </p>
            ) : (
              <p className="text-sm text-gray-600">
                Complete the item specifics below. {totalRequired > 0 && `${totalRequired} fields are required.`}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Required Fields */}
      {requiredFields.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <span className="w-2 h-2 bg-red-500 rounded-full"></span>
            Required Fields ({requiredFields.length})
          </h4>
          {requiredFields.map((specific) => (
            <div key={specific.name}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {specific.name}
                <span className="text-red-500 ml-1">*</span>
              </label>
              {renderInput(specific)}
              {errors[specific.name] && (
                <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors[specific.name]}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Recommended Fields */}
      {recommendedFields.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
            <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
            Recommended Fields ({recommendedFields.length})
          </h4>
          {recommendedFields.map((specific) => (
            <div key={specific.name}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {specific.name}
                <span className="text-sm text-gray-500 ml-1">(Recommended)</span>
              </label>
              {renderInput(specific)}
              {errors[specific.name] && (
                <p className="mt-1 text-sm text-red-600 flex items-center gap-1">
                  <AlertCircle className="w-4 h-4" />
                  {errors[specific.name]}
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Optional Fields - Collapsible */}
      {optionalFields.length > 0 && (
        <div className="space-y-4">
          <button
            type="button"
            onClick={() => setShowAllFields(!showAllFields)}
            className="flex items-center gap-2 text-sm font-semibold text-gray-700 hover:text-gray-900"
          >
            <span className="w-2 h-2 bg-gray-400 rounded-full"></span>
            Optional Fields ({optionalFields.length})
            <span className="text-xs text-gray-500">
              {showAllFields ? '(Click to hide)' : '(Click to show)'}
            </span>
          </button>
          
          {showAllFields && (
            <div className="space-y-4 pl-4 border-l-2 border-gray-200">
              {optionalFields.map((specific) => (
                <div key={specific.name}>
                  <label className="block text-sm font-medium text-gray-600 mb-1">
                    {specific.name}
                    <span className="text-xs text-gray-400 ml-1">(Optional)</span>
                  </label>
                  {renderInput(specific)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Help Text */}
      <div className="mt-6 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-xs text-gray-600">
          <span className="font-medium">About AI Predictions:</span> Fields with green backgrounds were auto-filled by AI with high confidence (≥75%).
          Yellow badges indicate moderate confidence predictions. Always review and verify all values before publishing.
        </p>
      </div>
    </div>
  );
}
