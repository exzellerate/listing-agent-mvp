import { useState, useEffect } from 'react';
import { X, ChevronLeft, ChevronRight, Check, AlertCircle } from 'lucide-react';
import SmartAspectForm from './SmartAspectForm';
import BusinessPoliciesSelector from './BusinessPoliciesSelector';
import { EbayCategory } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface WizardStep {
  number: number;
  title: string;
  description: string;
}

const WIZARD_STEPS: WizardStep[] = [
  {
    number: 1,
    title: 'Review Details',
    description: 'Review and edit product information'
  },
  {
    number: 2,
    title: 'Item Specifics',
    description: 'Add required product attributes'
  },
  {
    number: 3,
    title: 'Policies',
    description: 'Set shipping & business policies'
  },
  {
    number: 4,
    title: 'Preview & Publish',
    description: 'Review and publish your listing'
  }
];

interface EbayListingWizardProps {
  isOpen: boolean;
  onClose: () => void;
  productData: {
    title?: string;
    description?: string;
    images?: string[];
    price?: number;
    condition?: string;
    [key: string]: any;
  };
  analysisId?: number;
  ebayCategory?: EbayCategory;
  ebayAspects?: Record<string, string | string[]>;
  onSuccess: (listingId: string) => void;
}

export default function EbayListingWizard({
  isOpen,
  onClose,
  productData,
  analysisId,
  ebayCategory,
  ebayAspects,
  onSuccess
}: EbayListingWizardProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    // Step 1: Product details
    title: productData.title || '',
    description: productData.description || '',
    images: productData.images || [],
    price: productData.price || 0,
    condition: productData.condition || 'NEW',
    quantity: 1,

    // Step 2: Category
    categoryId: '',
    categoryPath: '',

    // Step 3: Item specifics
    itemSpecifics: {} as Record<string, string | string[]>,

    // Step 4: Policies & Shipping
    shippingPolicyId: '',
    returnPolicyId: '',
    paymentPolicyId: '',
    shippingWeightLbs: '' as string | number,
    shippingWeightOz: '' as string | number,
    shippingLength: '' as string | number,
    shippingWidth: '' as string | number,
    shippingHeight: '' as string | number,

    // Step 5: Publishing
    format: 'FIXED_PRICE' as 'FIXED_PRICE' | 'AUCTION',
    duration: 'GTC' // Good 'Til Cancelled
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [, setValidationState] = useState<Record<number, boolean>>({});

  // Initialize form data when product data changes
  useEffect(() => {
    if (productData) {
      setFormData(prev => ({
        ...prev,
        title: productData.title || prev.title,
        description: productData.description || prev.description,
        images: productData.images || prev.images,
        price: productData.price || prev.price,
        condition: productData.condition || prev.condition
      }));
    }
  }, [productData]);

  // Set category from ebayCategory prop when wizard opens
  useEffect(() => {
    if (isOpen && ebayCategory && !formData.categoryId) {
      setFormData(prev => ({
        ...prev,
        categoryId: ebayCategory.category_id,
        categoryPath: ebayCategory.category_path
      }));
    }
  }, [isOpen, ebayCategory]);

  const validateStep = (step: number): boolean => {
    const newErrors: Record<string, string> = {};

    switch (step) {
      case 1:
        if (!formData.title || formData.title.length < 10) {
          newErrors.title = 'Title must be at least 10 characters';
        }
        if (!formData.description || formData.description.length < 20) {
          newErrors.description = 'Description must be at least 20 characters';
        }
        if (!formData.price || formData.price <= 0) {
          newErrors.price = 'Price must be greater than 0';
        }
        if (!formData.images || formData.images.length === 0) {
          newErrors.images = 'At least one image is required';
        }
        break;

      // Steps 2-4: Item Specifics, Policies, Preview - no blocking validation
      // Business policies are optional - they'll be auto-created if not provided
    }

    setErrors(newErrors);
    const isValid = Object.keys(newErrors).length === 0;
    setValidationState(prev => ({ ...prev, [step]: isValid }));
    return isValid;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      if (currentStep < WIZARD_STEPS.length) {
        setCurrentStep(currentStep + 1);
      }
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handlePublish = async () => {
    if (!validateStep(currentStep)) {
      return;
    }

    setLoading(true);
    try {
      // Prepare FormData for backend (it expects Form data, not JSON)
      const formDataToSend = new FormData();

      // Include analysis_id if available (links to AI-generated product analysis)
      if (analysisId) {
        formDataToSend.append('analysis_id', analysisId.toString());
      }

      formDataToSend.append('title', formData.title);
      formDataToSend.append('description', formData.description);
      formDataToSend.append('price', formData.price.toString());
      formDataToSend.append('quantity', formData.quantity.toString());
      formDataToSend.append('condition', formData.condition);

      if (formData.categoryId) {
        formDataToSend.append('category_id', formData.categoryId);
      }

      // Add shipping weight/dimensions if provided
      if (formData.shippingWeightLbs) {
        formDataToSend.append('shipping_weight_lbs', formData.shippingWeightLbs.toString());
      }
      if (formData.shippingWeightOz) {
        formDataToSend.append('shipping_weight_oz', formData.shippingWeightOz.toString());
      }
      if (formData.shippingLength) {
        formDataToSend.append('shipping_length', formData.shippingLength.toString());
      }
      if (formData.shippingWidth) {
        formDataToSend.append('shipping_width', formData.shippingWidth.toString());
      }
      if (formData.shippingHeight) {
        formDataToSend.append('shipping_height', formData.shippingHeight.toString());
      }

      // Add item specifics as JSON
      if (Object.keys(formData.itemSpecifics).length > 0) {
        formDataToSend.append('item_specifics', JSON.stringify(formData.itemSpecifics));
      }

      // Submit listing to backend
      const response = await fetch(`${API_BASE_URL}/api/ebay/listings/create`, {
        method: 'POST',
        body: formDataToSend
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to create listing');
      }

      const result = await response.json();
      onSuccess(result.listing_id);
      onClose();
    } catch (err: any) {
      setErrors({ publish: err.message || 'Failed to publish listing' });
    } finally {
      setLoading(false);
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return renderStep1();
      case 2:
        return renderStep3(); // Item Specifics
      case 3:
        return renderStep4(); // Policies
      case 4:
        return renderStep5(); // Preview & Publish
      default:
        return null;
    }
  };

  const renderStep1 = () => (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Product Title *
        </label>
        <input
          type="text"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.title ? 'border-red-500' : 'border-gray-300'
          }`}
          placeholder="Enter product title (min 10 characters)"
          maxLength={80}
        />
        {errors.title && (
          <p className="mt-1 text-sm text-red-600">{errors.title}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          {formData.title.length}/80 characters
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Description *
        </label>
        <textarea
          value={formData.description}
          onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          rows={6}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.description ? 'border-red-500' : 'border-gray-300'
          }`}
          placeholder="Enter detailed product description"
        />
        {errors.description && (
          <p className="mt-1 text-sm text-red-600">{errors.description}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Price (USD) *
          </label>
          <input
            type="number"
            value={formData.price}
            onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) })}
            className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
              errors.price ? 'border-red-500' : 'border-gray-300'
            }`}
            placeholder="0.00"
            step="0.01"
            min="0"
          />
          {errors.price && (
            <p className="mt-1 text-sm text-red-600">{errors.price}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Condition *
          </label>
          <select
            value={formData.condition}
            onChange={(e) => setFormData({ ...formData, condition: e.target.value })}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="NEW">New</option>
            <option value="LIKE_NEW">Like New</option>
            <option value="USED_EXCELLENT">Used - Excellent</option>
            <option value="USED_GOOD">Used - Good</option>
            <option value="USED_ACCEPTABLE">Used - Acceptable</option>
            <option value="FOR_PARTS_OR_NOT_WORKING">For Parts or Not Working</option>
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Quantity
        </label>
        <input
          type="number"
          value={formData.quantity}
          onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) })}
          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          min="1"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Images *
        </label>
        <div className="grid grid-cols-4 gap-2">
          {formData.images.map((image, index) => (
            <div key={index} className="relative aspect-square">
              <img
                src={image}
                alt={`Product ${index + 1}`}
                className="w-full h-full object-cover rounded-lg border border-gray-300"
              />
            </div>
          ))}
        </div>
        {errors.images && (
          <p className="mt-1 text-sm text-red-600">{errors.images}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          {formData.images.length} image(s) - eBay allows up to 12 images
        </p>
      </div>
    </div>
  );

  const renderStep3 = () => {
    if (!analysisId) {
      return (
        <div className="flex items-center gap-2 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-700">
          <AlertCircle className="w-5 h-5 flex-shrink-0" />
          <span className="text-sm">Analysis ID is required for AI-powered item specifics.</span>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <SmartAspectForm
          analysisId={analysisId}
          categoryId={formData.categoryId}
          categoryName={formData.categoryPath.split(' > ').pop() || formData.categoryPath}
          initialValues={formData.itemSpecifics}
          prefilledValues={ebayAspects}
          onChange={(specifics) => setFormData({ ...formData, itemSpecifics: specifics })}
          errors={errors}
        />
      </div>
    );
  };

  const renderStep4 = () => (
    <div className="space-y-6">
      <BusinessPoliciesSelector
        selectedFulfillmentPolicyId={formData.shippingPolicyId}
        selectedPaymentPolicyId={formData.paymentPolicyId}
        selectedReturnPolicyId={formData.returnPolicyId}
        onPoliciesChange={(policies) => {
          setFormData({
            ...formData,
            shippingPolicyId: policies.fulfillmentPolicyId,
            paymentPolicyId: policies.paymentPolicyId,
            returnPolicyId: policies.returnPolicyId
          });
          // Clear errors when policies are selected
          setErrors({
            ...errors,
            shipping: '',
            return: '',
            payment: ''
          });
        }}
        errors={{
          fulfillment: errors.shipping,
          payment: errors.payment,
          return: errors.return
        }}
      />

      {/* Shipping Package Details */}
      <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
        <h3 className="font-semibold text-gray-900 mb-2">Package Details (Optional)</h3>
        <p className="text-sm text-gray-600 mb-4">
          If your shipping policy uses calculated shipping, you'll need to provide package weight. Otherwise, these fields are optional.
        </p>

        <div className="grid grid-cols-2 gap-4">
          {/* Weight */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Weight (lbs)
            </label>
            <input
              type="number"
              step="0.01"
              min="0"
              value={formData.shippingWeightLbs}
              onChange={(e) => setFormData({ ...formData, shippingWeightLbs: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., 1.5"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Weight (oz)
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="15.9"
              value={formData.shippingWeightOz}
              onChange={(e) => setFormData({ ...formData, shippingWeightOz: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., 8"
            />
          </div>

          {/* Dimensions */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Length (inches)
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.shippingLength}
              onChange={(e) => setFormData({ ...formData, shippingLength: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., 10"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Width (inches)
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.shippingWidth}
              onChange={(e) => setFormData({ ...formData, shippingWidth: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., 8"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Height (inches)
            </label>
            <input
              type="number"
              step="0.1"
              min="0"
              value={formData.shippingHeight}
              onChange={(e) => setFormData({ ...formData, shippingHeight: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              placeholder="e.g., 6"
            />
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep5 = () => (
    <div className="space-y-6">
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm font-medium text-blue-900 mb-1">Ready to Publish</p>
        <p className="text-sm text-blue-700">
          Review your listing details below. Click "Publish Listing" to create your eBay listing.
        </p>
      </div>

      {/* Product Details */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">Product Details</h3>
        </div>
        <div className="p-4 space-y-3">
          <div>
            <p className="text-sm font-medium text-gray-700">Title</p>
            <p className="text-sm text-gray-900 mt-1">{formData.title}</p>
          </div>
          <div>
            <p className="text-sm font-medium text-gray-700">Description</p>
            <p className="text-sm text-gray-900 mt-1 line-clamp-3">{formData.description}</p>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-700">Price</p>
              <p className="text-sm text-gray-900 mt-1">${formData.price.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Condition</p>
              <p className="text-sm text-gray-900 mt-1">{formData.condition.replace(/_/g, ' ')}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-700">Quantity</p>
              <p className="text-sm text-gray-900 mt-1">{formData.quantity}</p>
            </div>
          </div>
          {formData.images.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">Images ({formData.images.length})</p>
              <div className="grid grid-cols-6 gap-2">
                {formData.images.slice(0, 6).map((image, index) => (
                  <img
                    key={index}
                    src={image}
                    alt={`Product ${index + 1}`}
                    className="w-full aspect-square object-cover rounded border border-gray-300"
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Category */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">Category</h3>
        </div>
        <div className="p-4">
          <p className="text-sm text-gray-900">{formData.categoryPath || 'Not selected'}</p>
          <p className="text-xs text-gray-500 mt-1">Category ID: {formData.categoryId || 'N/A'}</p>
        </div>
      </div>

      {/* Item Specifics */}
      {Object.keys(formData.itemSpecifics).length > 0 && (
        <div className="border border-gray-200 rounded-lg overflow-hidden">
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
            <h3 className="font-semibold text-gray-900">Item Specifics</h3>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(formData.itemSpecifics).map(([key, value]) => (
                <div key={key}>
                  <p className="text-sm font-medium text-gray-700">{key}</p>
                  <p className="text-sm text-gray-900 mt-1">
                    {Array.isArray(value) ? value.join(', ') : value}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Business Policies */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900">Business Policies</h3>
        </div>
        <div className="p-4 space-y-2">
          {formData.shippingPolicyId ? (
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium text-gray-700">Shipping Policy:</span>
              <span className="text-gray-900">{formData.shippingPolicyId}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-amber-700">
              <AlertCircle className="w-4 h-4" />
              <span>Default shipping policy will be created automatically</span>
            </div>
          )}
          {formData.paymentPolicyId ? (
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium text-gray-700">Payment Policy:</span>
              <span className="text-gray-900">{formData.paymentPolicyId}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-amber-700">
              <AlertCircle className="w-4 h-4" />
              <span>Default payment policy will be created automatically</span>
            </div>
          )}
          {formData.returnPolicyId ? (
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium text-gray-700">Return Policy:</span>
              <span className="text-gray-900">{formData.returnPolicyId}</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-amber-700">
              <AlertCircle className="w-4 h-4" />
              <span>Default return policy will be created automatically</span>
            </div>
          )}
        </div>
      </div>

      {errors.publish && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-2 text-red-800">
            <AlertCircle className="w-5 h-5" />
            <span className="font-medium">Failed to publish listing</span>
          </div>
          <p className="text-sm text-red-700 mt-2">{errors.publish}</p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={() => { setErrors({}); handlePublish(); }}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
            >
              Retry
            </button>
            <button
              onClick={() => { setErrors({}); setCurrentStep(currentStep - 1); }}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-lg text-sm font-medium transition-colors"
            >
              Go Back
            </button>
          </div>
        </div>
      )}
    </div>
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Create eBay Listing</h2>
            <p className="text-sm text-gray-600 mt-1">
              Step {currentStep} of {WIZARD_STEPS.length}: {WIZARD_STEPS[currentStep - 1].title}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Progress Steps */}
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-center justify-between">
            {WIZARD_STEPS.map((step, index) => (
              <div key={step.number} className="flex items-center flex-1">
                <div className="flex flex-col items-center flex-1">
                  <div
                    className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold transition-colors ${
                      currentStep > step.number
                        ? 'bg-green-500 text-white'
                        : currentStep === step.number
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-600'
                    }`}
                  >
                    {currentStep > step.number ? (
                      <Check className="w-5 h-5" />
                    ) : (
                      step.number
                    )}
                  </div>
                  <div className="mt-2 text-center">
                    <p className={`text-xs font-medium ${
                      currentStep >= step.number ? 'text-gray-900' : 'text-gray-500'
                    }`}>
                      {step.title}
                    </p>
                  </div>
                </div>
                {index < WIZARD_STEPS.length - 1 && (
                  <div
                    className={`h-1 flex-1 mx-2 transition-colors ${
                      currentStep > step.number ? 'bg-green-500' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {renderStepContent()}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between">
          <button
            onClick={handleBack}
            disabled={currentStep === 1}
            className="flex items-center gap-2 px-4 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-5 h-5" />
            Back
          </button>

          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-6 py-2 text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            >
              Cancel
            </button>

            {currentStep < WIZARD_STEPS.length ? (
              <button
                onClick={handleNext}
                className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                Next
                <ChevronRight className="w-5 h-5" />
              </button>
            ) : (
              <button
                onClick={handlePublish}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" />
                    Publishing...
                  </>
                ) : (
                  <>
                    <Check className="w-5 h-5" />
                    Publish Listing
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
