import { useState, useEffect } from 'react';
import { AlertCircle, Loader2 } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ItemSpecific {
  name: string;
  cardinality: 'SINGLE' | 'MULTI';
  usage: 'REQUIRED' | 'RECOMMENDED' | 'OPTIONAL';
  values?: string[];
  max_values?: number;
  constraint?: 'SELECTION_ONLY' | 'FREE_TEXT';
}

interface ItemSpecificsFormProps {
  categoryId: string;
  initialValues?: Record<string, string | string[]>;
  onChange: (specifics: Record<string, string | string[]>) => void;
  errors?: Record<string, string>;
}

export default function ItemSpecificsForm({
  categoryId,
  initialValues = {},
  onChange,
  errors = {}
}: ItemSpecificsFormProps) {
  const [specifics, setSpecifics] = useState<ItemSpecific[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formValues, setFormValues] = useState<Record<string, string | string[]>>(initialValues);

  useEffect(() => {
    if (categoryId) {
      fetchItemSpecifics(categoryId);
    }
  }, [categoryId]);

  useEffect(() => {
    setFormValues(initialValues);
  }, [initialValues]);

  const fetchItemSpecifics = async (catId: string) => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/ebay/categories/${catId}/item-specifics`
      );

      if (!response.ok) {
        // If endpoint doesn't exist (404), treat as no specifics available
        if (response.status === 404) {
          console.log('Item specifics endpoint not available - skipping');
          setSpecifics([]);
          setError(null);
          setLoading(false);
          return;
        }

        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch item specifics');
      }

      const data = await response.json();
      setSpecifics(data.item_specifics || []);
    } catch (err: any) {
      console.error('Failed to fetch item specifics:', err);
      // Only set error for non-404 errors
      if (!err.message?.includes('404')) {
        setError(err.message || 'Failed to load item specifics for this category');
      }
      setSpecifics([]);
    } finally {
      setLoading(false);
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

  const renderInput = (specific: ItemSpecific) => {
    const value = formValues[specific.name] || (specific.cardinality === 'MULTI' ? [] : '');
    const isRequired = specific.usage === 'REQUIRED';
    const hasError = errors[specific.name];

    // Single value with predefined options
    if (specific.cardinality === 'SINGLE' && specific.values && specific.values.length > 0) {
      return (
        <select
          value={value as string}
          onChange={(e) => handleInputChange(specific.name, e.target.value)}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            hasError ? 'border-red-500' : 'border-gray-300'
          }`}
          required={isRequired}
        >
          <option value="">Select {specific.name}</option>
          {specific.values.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
      );
    }

    // Single value with free text
    if (specific.cardinality === 'SINGLE') {
      return (
        <input
          type="text"
          value={value as string}
          onChange={(e) => handleInputChange(specific.name, e.target.value)}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            hasError ? 'border-red-500' : 'border-gray-300'
          }`}
          placeholder={`Enter ${specific.name}`}
          required={isRequired}
        />
      );
    }

    // Multi-value with predefined options
    if (specific.cardinality === 'MULTI' && specific.values && specific.values.length > 0) {
      const multiValues = (value as string[]) || [];
      return (
        <div className="space-y-2">
          <select
            onChange={(e) => {
              if (e.target.value && !multiValues.includes(e.target.value)) {
                handleInputChange(specific.name, [...multiValues, e.target.value]);
              }
              e.target.value = '';
            }}
            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              hasError ? 'border-red-500' : 'border-gray-300'
            }`}
          >
            <option value="">Add {specific.name}</option>
            {specific.values.map((option) => (
              <option key={option} value={option} disabled={multiValues.includes(option)}>
                {option}
              </option>
            ))}
          </select>
          {multiValues.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {multiValues.map((val) => (
                <span
                  key={val}
                  className="inline-flex items-center gap-2 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                >
                  {val}
                  <button
                    type="button"
                    onClick={() => handleInputChange(specific.name, multiValues.filter(v => v !== val))}
                    className="hover:text-blue-900"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      );
    }

    // Multi-value with free text
    const multiValues = (value as string[]) || [];
    return (
      <div className="space-y-2">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder={`Enter ${specific.name} and press Enter`}
            className={`flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              hasError ? 'border-red-500' : 'border-gray-300'
            }`}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                const input = e.currentTarget;
                if (input.value.trim() && !multiValues.includes(input.value.trim())) {
                  handleInputChange(specific.name, [...multiValues, input.value.trim()]);
                  input.value = '';
                }
              }
            }}
          />
        </div>
        {multiValues.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {multiValues.map((val) => (
              <span
                key={val}
                className="inline-flex items-center gap-2 px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
              >
                {val}
                <button
                  type="button"
                  onClick={() => handleInputChange(specific.name, multiValues.filter(v => v !== val))}
                  className="hover:text-blue-900"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        )}
      </div>
    );
  };

  if (!categoryId) {
    return (
      <div className="p-8 text-center text-gray-500">
        <AlertCircle className="w-12 h-12 mx-auto mb-3 text-gray-400" />
        <p>Please select a category first to see item specifics</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-8 text-center">
        <Loader2 className="w-12 h-12 mx-auto mb-3 text-blue-600 animate-spin" />
        <p className="text-gray-600">Loading item specifics...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <div className="flex items-center gap-2 text-red-800 mb-2">
          <AlertCircle className="w-5 h-5" />
          <span className="font-medium">Error Loading Item Specifics</span>
        </div>
        <p className="text-sm text-red-700">{error}</p>
        <button
          onClick={() => fetchItemSpecifics(categoryId)}
          className="mt-3 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium"
        >
          Try Again
        </button>
      </div>
    );
  }

  if (specifics.length === 0) {
    return (
      <div className="p-8 text-center">
        <p className="text-gray-600">No item specifics required for this category</p>
        <p className="text-sm text-gray-500 mt-2">You can proceed to the next step</p>
      </div>
    );
  }

  // Separate required and optional specifics
  const requiredSpecifics = specifics.filter(s => s.usage === 'REQUIRED');
  const recommendedSpecifics = specifics.filter(s => s.usage === 'RECOMMENDED');
  const optionalSpecifics = specifics.filter(s => s.usage === 'OPTIONAL');

  return (
    <div className="space-y-6">
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm font-medium text-blue-900 mb-1">About Item Specifics</p>
        <p className="text-sm text-blue-700">
          Item specifics are product attributes that help buyers find your listing.
          Fill in as many as possible to improve your listing's visibility.
        </p>
      </div>

      {/* Required Specifics */}
      {requiredSpecifics.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Required Information *
          </h3>
          <div className="space-y-4">
            {requiredSpecifics.map((specific) => (
              <div key={specific.name}>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {specific.name} *
                </label>
                {renderInput(specific)}
                {errors[specific.name] && (
                  <p className="mt-1 text-sm text-red-600">{errors[specific.name]}</p>
                )}
                {specific.max_values && specific.cardinality === 'MULTI' && (
                  <p className="mt-1 text-xs text-gray-500">
                    Maximum {specific.max_values} value(s)
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommended Specifics */}
      {recommendedSpecifics.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Recommended Information
          </h3>
          <p className="text-sm text-gray-600 mb-4">
            These attributes are highly recommended to improve your listing's visibility
          </p>
          <div className="space-y-4">
            {recommendedSpecifics.map((specific) => (
              <div key={specific.name}>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {specific.name}
                </label>
                {renderInput(specific)}
                {errors[specific.name] && (
                  <p className="mt-1 text-sm text-red-600">{errors[specific.name]}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Optional Specifics */}
      {optionalSpecifics.length > 0 && (
        <details className="border border-gray-200 rounded-lg">
          <summary className="px-4 py-3 cursor-pointer font-medium text-gray-900 hover:bg-gray-50">
            Optional Information ({optionalSpecifics.length} fields)
          </summary>
          <div className="px-4 py-3 space-y-4 border-t border-gray-200">
            {optionalSpecifics.map((specific) => (
              <div key={specific.name}>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {specific.name}
                </label>
                {renderInput(specific)}
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}
