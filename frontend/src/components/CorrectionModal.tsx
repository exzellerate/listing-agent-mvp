import { useState } from 'react';
import { AnalysisResult } from '../types';

interface CorrectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (corrections: CorrectionData) => void;
  currentResult: AnalysisResult;
  action: 'edited' | 'rejected';
}

export interface CorrectionData {
  user_product_name?: string;
  user_brand?: string;
  user_category?: string;
  user_title?: string;
  user_description?: string;
  user_price?: number;
  user_notes?: string;
}

export default function CorrectionModal({
  isOpen,
  onClose,
  onSubmit,
  currentResult,
  action,
}: CorrectionModalProps) {
  const [corrections, setCorrections] = useState<CorrectionData>({
    user_product_name: currentResult.product_name,
    user_brand: currentResult.brand || '',
    user_category: currentResult.category || '',
    user_title: currentResult.suggested_title,
    user_description: currentResult.suggested_description,
    user_notes: '',
  });

  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);

    try {
      await onSubmit(corrections);
      onClose();
    } catch (error) {
      console.error('Failed to submit corrections:', error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (field: keyof CorrectionData, value: string | number) => {
    setCorrections((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black bg-opacity-50 transition-opacity"
        onClick={onClose}
      ></div>

      {/* Modal */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative w-full max-w-3xl bg-white rounded-2xl shadow-2xl transform transition-all">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-4 rounded-t-2xl">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {action === 'edited' ? '✏️ Edit & Correct' : '❌ Reject & Correct'}
                </h2>
                <p className="text-sm text-blue-100 mt-1">
                  {action === 'edited'
                    ? 'Make corrections to improve future results'
                    : 'Tell us what the correct information should be'}
                </p>
              </div>
              <button
                onClick={onClose}
                className="text-white hover:text-gray-200 transition-colors"
                aria-label="Close modal"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-6 max-h-[calc(100vh-200px)] overflow-y-auto">
            {/* Product Name - Most Important */}
            <div className="bg-yellow-50 border-2 border-yellow-300 rounded-lg p-4">
              <label className="block text-sm font-bold text-gray-900 mb-2">
                Product Name <span className="text-red-500">*</span>
                <span className="ml-2 text-xs font-normal text-gray-600">
                  (This is the most important correction)
                </span>
              </label>
              <input
                type="text"
                value={corrections.user_product_name || ''}
                onChange={(e) => handleChange('user_product_name', e.target.value)}
                className="w-full px-4 py-3 border-2 border-yellow-400 rounded-lg focus:ring-2 focus:ring-yellow-500 focus:border-transparent text-lg font-semibold"
                placeholder="Enter the correct product name"
                required
              />
              <p className="text-xs text-gray-600 mt-2">
                AI detected: <span className="font-semibold">{currentResult.product_name}</span>
              </p>
            </div>

            {/* Brand */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Brand
              </label>
              <input
                type="text"
                value={corrections.user_brand || ''}
                onChange={(e) => handleChange('user_brand', e.target.value)}
                className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter the correct brand"
              />
              <p className="text-xs text-gray-500 mt-1">
                AI detected: {currentResult.brand || 'None'}
              </p>
            </div>

            {/* Category */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Category
              </label>
              <input
                type="text"
                value={corrections.user_category || ''}
                onChange={(e) => handleChange('user_category', e.target.value)}
                className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter the correct category"
              />
              <p className="text-xs text-gray-500 mt-1">
                AI detected: {currentResult.category || 'None'}
              </p>
            </div>

            {/* Title */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Listing Title
              </label>
              <input
                type="text"
                value={corrections.user_title || ''}
                onChange={(e) => handleChange('user_title', e.target.value)}
                className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter the correct listing title"
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Description
              </label>
              <textarea
                value={corrections.user_description || ''}
                onChange={(e) => handleChange('user_description', e.target.value)}
                rows={4}
                className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter the correct description"
              />
            </div>

            {/* Price */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Price (optional)
              </label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 font-semibold">
                  $
                </span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={corrections.user_price || ''}
                  onChange={(e) => handleChange('user_price', parseFloat(e.target.value))}
                  className="w-full pl-8 pr-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="0.00"
                />
              </div>
            </div>

            {/* Notes */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Additional Notes (optional)
              </label>
              <textarea
                value={corrections.user_notes || ''}
                onChange={(e) => handleChange('user_notes', e.target.value)}
                rows={2}
                className="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Any additional feedback about why the AI was incorrect..."
              />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4 border-t">
              <button
                type="button"
                onClick={onClose}
                disabled={submitting}
                className="flex-1 px-6 py-3 bg-gray-100 hover:bg-gray-200 rounded-lg font-semibold text-gray-700 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || !corrections.user_product_name}
                className={`
                  flex-1 px-6 py-3 rounded-lg font-semibold text-white transition-all shadow-lg
                  ${
                    submitting || !corrections.user_product_name
                      ? 'bg-gray-400 cursor-not-allowed'
                      : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 hover:shadow-xl'
                  }
                `}
              >
                {submitting ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                        fill="none"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Submitting...
                  </span>
                ) : (
                  `Submit ${action === 'edited' ? 'Edits' : 'Corrections'}`
                )}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
