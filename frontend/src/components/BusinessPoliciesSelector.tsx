import { useState, useEffect } from 'react';
import { AlertCircle, Loader2, CheckCircle, Package, CreditCard, RefreshCw } from 'lucide-react';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ShippingOption {
  shippingServiceCode?: string;
  rateType?: string;
  shippingCost?: {
    value?: string;
    currency?: string;
  };
}

interface BusinessPolicy {
  policyId: string;
  name: string;
  description?: string;
  shippingOptions?: ShippingOption[];
  categoryTypes?: Array<{ name: string }>;
}

interface BusinessPoliciesResponse {
  fulfillment_policies: BusinessPolicy[];
  payment_policies: BusinessPolicy[];
  return_policies: BusinessPolicy[];
}

interface BusinessPoliciesSelectorProps {
  selectedFulfillmentPolicyId?: string;
  selectedPaymentPolicyId?: string;
  selectedReturnPolicyId?: string;
  onPoliciesChange: (policies: {
    fulfillmentPolicyId: string;
    paymentPolicyId: string;
    returnPolicyId: string;
  }) => void;
  errors?: {
    fulfillment?: string;
    payment?: string;
    return?: string;
  };
}

export default function BusinessPoliciesSelector({
  selectedFulfillmentPolicyId = '',
  selectedPaymentPolicyId = '',
  selectedReturnPolicyId = '',
  onPoliciesChange,
  errors = {}
}: BusinessPoliciesSelectorProps) {
  const [policies, setPolicies] = useState<BusinessPoliciesResponse>({
    fulfillment_policies: [],
    payment_policies: [],
    return_policies: []
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPolicies();
  }, []);

  const fetchPolicies = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/ebay/business-policies`);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to fetch business policies');
      }

      const data = await response.json();
      setPolicies(data);

      // Auto-select if only one policy of each type exists
      if (data.fulfillment_policies.length === 1 && !selectedFulfillmentPolicyId) {
        handlePolicyChange('fulfillment', data.fulfillment_policies[0].policyId);
      }
      if (data.payment_policies.length === 1 && !selectedPaymentPolicyId) {
        handlePolicyChange('payment', data.payment_policies[0].policyId);
      }
      if (data.return_policies.length === 1 && !selectedReturnPolicyId) {
        handlePolicyChange('return', data.return_policies[0].policyId);
      }
    } catch (err: any) {
      console.error('Failed to fetch business policies:', err);
      setError(err.message || 'Failed to load business policies');
    } finally {
      setLoading(false);
    }
  };

  const handlePolicyChange = (type: 'fulfillment' | 'payment' | 'return', policyId: string) => {
    const newPolicies = {
      fulfillmentPolicyId: type === 'fulfillment' ? policyId : selectedFulfillmentPolicyId,
      paymentPolicyId: type === 'payment' ? policyId : selectedPaymentPolicyId,
      returnPolicyId: type === 'return' ? policyId : selectedReturnPolicyId
    };
    onPoliciesChange(newPolicies);
  };

  if (loading) {
    return (
      <div className="p-8 text-center">
        <Loader2 className="w-12 h-12 mx-auto mb-3 text-blue-600 animate-spin" />
        <p className="text-gray-600">Loading business policies...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 bg-amber-50 border border-amber-200 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-medium text-amber-900 mb-2">Business Policies Required</h3>
            <p className="text-sm text-amber-800 mb-4">{error}</p>
            <div className="space-y-2 text-sm text-amber-800">
              <p className="font-medium">To create listings, you need to set up:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Shipping (Fulfillment) Policy - How you'll ship items</li>
                <li>Payment Policy - How buyers will pay</li>
                <li>Return Policy - Your return terms</li>
              </ul>
              <div className="mt-4 p-3 bg-amber-100 rounded border border-amber-300">
                <p className="font-medium mb-2">The system will automatically create default policies:</p>
                <ul className="list-disc list-inside space-y-1 ml-2 text-xs">
                  <li><strong>Shipping:</strong> USPS Priority Mail, 1 business day handling, $10.00</li>
                  <li><strong>Payment:</strong> Immediate payment required</li>
                  <li><strong>Return:</strong> 30-day returns accepted</li>
                </ul>
              </div>
            </div>
            <div className="mt-4 flex gap-3">
              <button
                onClick={fetchPolicies}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium"
              >
                Try Again
              </button>
              <a
                href="https://www.sandbox.ebay.com/sh/ovw/businessPolicies"
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg text-sm font-medium"
              >
                Open eBay Settings
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const hasNoPolicies =
    policies.fulfillment_policies.length === 0 ||
    policies.payment_policies.length === 0 ||
    policies.return_policies.length === 0;

  if (hasNoPolicies) {
    return (
      <div className="p-6 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-medium text-blue-900 mb-2">Setting Up Business Policies</h3>
            <p className="text-sm text-blue-800 mb-3">
              When you proceed to publish, the system will automatically create default business policies for you.
            </p>
            <div className="space-y-2 text-sm text-blue-800">
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                <span>Default shipping policy (USPS Priority Mail)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                <span>Default payment policy (Immediate payment)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" />
                <span>Default return policy (30-day returns)</span>
              </div>
            </div>
            <p className="text-sm text-blue-700 mt-4">
              You can customize these policies later in your eBay account settings.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm font-medium text-blue-900 mb-1">About Business Policies</p>
        <p className="text-sm text-blue-700">
          Business policies define how you'll ship items, accept payments, and handle returns.
          Select one of each type to use for this listing.
        </p>
      </div>

      {/* Fulfillment (Shipping) Policy */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <Package className="w-4 h-4" />
          Shipping Policy *
        </label>
        <select
          value={selectedFulfillmentPolicyId}
          onChange={(e) => handlePolicyChange('fulfillment', e.target.value)}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.fulfillment ? 'border-red-500' : 'border-gray-300'
          }`}
          required
        >
          <option value="">Select a shipping policy</option>
          {policies.fulfillment_policies.map((policy) => (
            <option key={policy.policyId} value={policy.policyId}>
              {policy.name} {policy.description ? `- ${policy.description}` : ''}
            </option>
          ))}
        </select>
        {errors.fulfillment && (
          <p className="mt-1 text-sm text-red-600">{errors.fulfillment}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Defines shipping methods, costs, and handling time
        </p>

        {/* Show requirements for selected fulfillment policy */}
        {selectedFulfillmentPolicyId && (() => {
          const selectedPolicy = policies.fulfillment_policies.find(
            p => p.policyId === selectedFulfillmentPolicyId
          );

          if (!selectedPolicy) return null;

          // Check if policy uses calculated shipping
          const usesCalculatedShipping = selectedPolicy.shippingOptions?.some(
            option => option.rateType === 'CALCULATED'
          );

          if (usesCalculatedShipping) {
            return (
              <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm">
                    <p className="font-medium text-amber-900 mb-1">Shipping Weight Required</p>
                    <p className="text-amber-800">
                      This policy uses <strong>calculated shipping</strong>, which requires package weight and dimensions.
                      You'll need to provide this information in Step 4 of the wizard.
                    </p>
                  </div>
                </div>
              </div>
            );
          } else {
            return (
              <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm">
                    <p className="font-medium text-green-900 mb-1">Flat Rate Shipping</p>
                    <p className="text-green-800">
                      This policy uses <strong>flat rate shipping</strong>. Package weight is optional.
                    </p>
                  </div>
                </div>
              </div>
            );
          }
        })()}
      </div>

      {/* Payment Policy */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <CreditCard className="w-4 h-4" />
          Payment Policy *
        </label>
        <select
          value={selectedPaymentPolicyId}
          onChange={(e) => handlePolicyChange('payment', e.target.value)}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.payment ? 'border-red-500' : 'border-gray-300'
          }`}
          required
        >
          <option value="">Select a payment policy</option>
          {policies.payment_policies.map((policy) => (
            <option key={policy.policyId} value={policy.policyId}>
              {policy.name} {policy.description ? `- ${policy.description}` : ''}
            </option>
          ))}
        </select>
        {errors.payment && (
          <p className="mt-1 text-sm text-red-600">{errors.payment}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Defines payment methods and terms
        </p>
      </div>

      {/* Return Policy */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <RefreshCw className="w-4 h-4" />
          Return Policy *
        </label>
        <select
          value={selectedReturnPolicyId}
          onChange={(e) => handlePolicyChange('return', e.target.value)}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.return ? 'border-red-500' : 'border-gray-300'
          }`}
          required
        >
          <option value="">Select a return policy</option>
          {policies.return_policies.map((policy) => (
            <option key={policy.policyId} value={policy.policyId}>
              {policy.name} {policy.description ? `- ${policy.description}` : ''}
            </option>
          ))}
        </select>
        {errors.return && (
          <p className="mt-1 text-sm text-red-600">{errors.return}</p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Defines return window and terms
        </p>
      </div>

      {/* Success indicator when all selected */}
      {selectedFulfillmentPolicyId && selectedPaymentPolicyId && selectedReturnPolicyId && (
        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
          <div className="flex items-center gap-2 text-green-800">
            <CheckCircle className="w-5 h-5" />
            <span className="font-medium">All business policies selected</span>
          </div>
          <p className="text-sm text-green-700 mt-1">
            You're ready to proceed to the next step
          </p>
        </div>
      )}
    </div>
  );
}
