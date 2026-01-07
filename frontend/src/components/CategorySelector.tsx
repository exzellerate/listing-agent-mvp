import { useState } from 'react';
import { Check, ChevronRight, Sparkles, TrendingUp } from 'lucide-react';
import { CategoryRecommendation } from '../types';

interface CategorySelectorProps {
  categories: CategoryRecommendation[];
  selectedCategoryId?: string;
  onSelect: (categoryId: string, categoryName: string, categoryPath: string) => void;
  loading?: boolean;
}

export default function CategorySelector({
  categories,
  selectedCategoryId,
  onSelect,
  loading = false
}: CategorySelectorProps) {
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-gray-600 mb-4">
          <Sparkles className="w-5 h-5 animate-pulse" />
          <p className="text-sm font-medium">AI is analyzing category recommendations...</p>
        </div>
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="border border-gray-200 rounded-lg p-4 animate-pulse"
          >
            <div className="h-5 bg-gray-200 rounded w-2/3 mb-2"></div>
            <div className="h-4 bg-gray-100 rounded w-full"></div>
          </div>
        ))}
      </div>
    );
  }

  if (!categories || categories.length === 0) {
    return (
      <div className="border border-gray-200 rounded-lg p-8 text-center">
        <div className="text-gray-400 mb-2">
          <TrendingUp className="w-12 h-12 mx-auto" />
        </div>
        <p className="text-gray-600 font-medium">No category recommendations available</p>
        <p className="text-sm text-gray-500 mt-1">
          The AI couldn't determine suitable categories for this product.
        </p>
      </div>
    );
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'bg-green-100 text-green-700 border-green-200';
    if (confidence >= 0.6) return 'bg-yellow-100 text-yellow-700 border-yellow-200';
    return 'bg-gray-100 text-gray-600 border-gray-200';
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return 'High confidence';
    if (confidence >= 0.6) return 'Medium confidence';
    return 'Low confidence';
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-gray-600 mb-4">
        <Sparkles className="w-5 h-5 text-blue-500" />
        <p className="text-sm font-medium">
          AI-Recommended Categories ({categories.length})
        </p>
      </div>

      {categories.map((category, index) => {
        const isSelected = selectedCategoryId === category.category_id;
        const isExpanded = expandedCategory === category.category_id;

        return (
          <div
            key={category.category_id}
            className={`
              border rounded-lg transition-all cursor-pointer
              ${isSelected
                ? 'border-blue-500 bg-blue-50 shadow-sm'
                : 'border-gray-200 hover:border-gray-300 hover:shadow-sm'
              }
            `}
            onClick={() => {
              if (!isSelected) {
                onSelect(
                  category.category_id,
                  category.category_name,
                  category.category_path
                );
              }
            }}
          >
            <div className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  {/* Rank Badge */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`
                      inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold
                      ${index === 0 ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-600'}
                    `}>
                      {index + 1}
                    </span>
                    <span className={`
                      text-xs px-2 py-0.5 rounded-full border font-medium
                      ${getConfidenceColor(category.confidence)}
                    `}>
                      {getConfidenceLabel(category.confidence)} ({Math.round(category.confidence * 100)}%)
                    </span>
                  </div>

                  {/* Category Name */}
                  <h3 className={`
                    text-base font-semibold mb-1
                    ${isSelected ? 'text-blue-900' : 'text-gray-900'}
                  `}>
                    {category.category_name}
                  </h3>

                  {/* Category Path */}
                  <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
                    {category.category_path.split(' > ').map((part, i, arr) => (
                      <span key={i} className="flex items-center gap-1">
                        {part}
                        {i < arr.length - 1 && <ChevronRight className="w-3 h-3" />}
                      </span>
                    ))}
                  </div>

                  {/* Reasoning - Expandable */}
                  <div className="text-sm text-gray-600">
                    {isExpanded ? (
                      <p className="mt-2">{category.reasoning}</p>
                    ) : (
                      <p className="truncate">{category.reasoning}</p>
                    )}
                  </div>

                  {/* Show More/Less Button */}
                  {category.reasoning.length > 100 && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setExpandedCategory(
                          isExpanded ? null : category.category_id
                        );
                      }}
                      className="text-xs text-blue-600 hover:text-blue-700 mt-1 font-medium"
                    >
                      {isExpanded ? 'Show less' : 'Show more'}
                    </button>
                  )}
                </div>

                {/* Selection Indicator */}
                <div className={`
                  flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center
                  ${isSelected
                    ? 'bg-blue-500 border-blue-500'
                    : 'bg-white border-gray-300'
                  }
                `}>
                  {isSelected && <Check className="w-4 h-4 text-white" />}
                </div>
              </div>
            </div>

            {/* Selection Hint for Top Category */}
            {index === 0 && !isSelected && (
              <div className="px-4 pb-3">
                <div className="bg-blue-50 border border-blue-200 rounded-md px-3 py-2 text-xs text-blue-700">
                  <span className="font-medium">Recommended:</span> This is the most relevant category based on your product.
                </div>
              </div>
            )}
          </div>
        );
      })}

      {/* Help Text */}
      <div className="mt-4 p-3 bg-gray-50 rounded-lg border border-gray-200">
        <p className="text-xs text-gray-600">
          <span className="font-medium">Tip:</span> Select the most specific category that matches your product.
          More specific categories often have better visibility and more relevant item specifics.
        </p>
      </div>
    </div>
  );
}
