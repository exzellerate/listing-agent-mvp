import { useState, useEffect } from 'react';
import { AnalysisResult } from '../types';
import CopyButton from './CopyButton';

interface ResultsFormProps {
  result: AnalysisResult;
}

export default function ResultsForm({ result }: ResultsFormProps) {
  const [title, setTitle] = useState(result.suggested_title);
  const [description, setDescription] = useState(result.suggested_description);
  const [category, setCategory] = useState(result.category || '');
  const [condition, setCondition] = useState(result.condition);
  const [features, setFeatures] = useState<string[]>(result.key_features);
  const [newFeature, setNewFeature] = useState('');

  // Update state when result changes
  useEffect(() => {
    setTitle(result.suggested_title);
    setDescription(result.suggested_description);
    setCategory(result.category || '');
    setCondition(result.condition);
    setFeatures(result.key_features);
  }, [result]);

  const addFeature = () => {
    if (newFeature.trim()) {
      setFeatures([...features, newFeature.trim()]);
      setNewFeature('');
    }
  };

  const removeFeature = (index: number) => {
    setFeatures(features.filter((_, i) => i !== index));
  };

  const titleCharCount = title.length;

  return (
    <div className="space-y-6">
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">AI Analysis Complete</h3>
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
      </div>

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

      {/* Category and Condition */}
      <div className="grid grid-cols-2 gap-4">
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
      </div>

      {/* Key Features */}
      <div className="space-y-2">
        <div className="flex justify-between items-center">
          <label className="block text-sm font-medium text-gray-700">
            Key Features
          </label>
          <CopyButton text={features.join('\n• ')} label="Copy All" />
        </div>
        <ul className="space-y-2">
          {features.map((feature, index) => (
            <li
              key={index}
              className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-md"
            >
              <span className="flex-1">{feature}</span>
              <button
                onClick={() => removeFeature(index)}
                className="text-red-600 hover:text-red-700 text-sm font-medium"
                aria-label={`Remove feature: ${feature}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>

        <div className="flex gap-2">
          <input
            type="text"
            value={newFeature}
            onChange={(e) => setNewFeature(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addFeature()}
            placeholder="Add a new feature"
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
            aria-label="New feature input"
          />
          <button
            onClick={addFeature}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-medium"
            aria-label="Add feature"
          >
            Add
          </button>
        </div>
      </div>
    </div>
  );
}
