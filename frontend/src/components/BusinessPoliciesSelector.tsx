import { useState, useEffect } from 'react';
import { AlertCircle, Loader2, CheckCircle, Package, CreditCard, RefreshCw, Plus, X } from 'lucide-react';
import {
  getBusinessPolicies,
  createFulfillmentPolicy,
  createPaymentPolicy,
  createReturnPolicy,
  optInToBusinessPolicies,
  APIError,
  type BusinessPolicy,
  type BusinessPoliciesResponse,
} from '../services/api';

// eBay returns this (errorId 20403) on every policy call - read or write -
// until the seller account opts into the Business Policies program. Matched
// against both our own friendly message and eBay's raw wording (the latter
// shows up when the read path's error isn't run through our translator).
function isOptInError(message: string | null | undefined): boolean {
  if (!message) return false;
  const lowered = message.toLowerCase();
  return (
    lowered.includes('not eligible for business policy') ||
    lowered.includes("isn't opted in") ||
    lowered.includes('20403')
  );
}

type PolicyType = 'fulfillment' | 'payment' | 'return';

interface FulfillmentFormState {
  name: string;
  handlingTimeDays: number;
  freeShipping: boolean;
  shippingCost: string;
}

interface PaymentFormState {
  name: string;
  immediatePayRequired: boolean;
}

interface ReturnFormState {
  name: string;
  returnsAccepted: boolean;
  returnPeriodDays: number;
  refundMethod: string;
  returnShippingPayer: string;
}

const DEFAULT_FULFILLMENT_FORM: FulfillmentFormState = {
  name: '',
  handlingTimeDays: 1,
  freeShipping: false,
  shippingCost: '10.00',
};

const DEFAULT_PAYMENT_FORM: PaymentFormState = {
  name: '',
  immediatePayRequired: false,
};

const DEFAULT_RETURN_FORM: ReturnFormState = {
  name: '',
  returnsAccepted: true,
  returnPeriodDays: 30,
  refundMethod: 'MONEY_BACK',
  returnShippingPayer: 'BUYER',
};

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

  // Inline "create new policy" form state
  const [creatingType, setCreatingType] = useState<PolicyType | null>(null);
  const [fulfillmentForm, setFulfillmentForm] = useState<FulfillmentFormState>(DEFAULT_FULFILLMENT_FORM);
  const [paymentForm, setPaymentForm] = useState<PaymentFormState>(DEFAULT_PAYMENT_FORM);
  const [returnForm, setReturnForm] = useState<ReturnFormState>(DEFAULT_RETURN_FORM);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [justCreated, setJustCreated] = useState<PolicyType | null>(null);
  const [optingIn, setOptingIn] = useState(false);

  useEffect(() => {
    fetchPolicies();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchPolicies = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await getBusinessPolicies();
      setPolicies(data);

      // Auto-select if only one policy of each type exists (single update so
      // the three selections don't overwrite each other via stale props)
      const autoSelected = {
        fulfillmentPolicyId:
          selectedFulfillmentPolicyId ||
          (data.fulfillment_policies.length === 1 ? data.fulfillment_policies[0].policyId : ''),
        paymentPolicyId:
          selectedPaymentPolicyId ||
          (data.payment_policies.length === 1 ? data.payment_policies[0].policyId : ''),
        returnPolicyId:
          selectedReturnPolicyId ||
          (data.return_policies.length === 1 ? data.return_policies[0].policyId : ''),
      };
      if (
        autoSelected.fulfillmentPolicyId !== selectedFulfillmentPolicyId ||
        autoSelected.paymentPolicyId !== selectedPaymentPolicyId ||
        autoSelected.returnPolicyId !== selectedReturnPolicyId
      ) {
        onPoliciesChange(autoSelected);
      }
    } catch (err: any) {
      console.error('Failed to fetch business policies:', err);
      setError(err.message || 'Failed to load business policies');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Opts the connected eBay account into Business Policies, then retries
   * whatever triggered this (the initial fetch, or an in-progress create
   * form) so the user doesn't have to manually hit "Try Again" themselves.
   */
  const handleOptIn = async (retryCreateType?: PolicyType) => {
    setOptingIn(true);
    try {
      const { verified } = await optInToBusinessPolicies();
      if (!verified) {
        const pending =
          'Business Policies was enabled, but eBay is still activating it. Please wait a minute and try again.';
        if (retryCreateType) {
          setCreateError(pending);
        } else {
          setError(pending);
        }
        return;
      }
      if (retryCreateType) {
        setCreateError(null);
        await handleCreateSubmit(retryCreateType);
      } else {
        await fetchPolicies();
      }
    } catch (err) {
      const message = err instanceof APIError ? err.message : 'Failed to enable Business Policies.';
      if (retryCreateType) {
        setCreateError(message);
      } else {
        setError(message);
      }
    } finally {
      setOptingIn(false);
    }
  };

  const handlePolicyChange = (type: PolicyType, policyId: string) => {
    const newPolicies = {
      fulfillmentPolicyId: type === 'fulfillment' ? policyId : selectedFulfillmentPolicyId,
      paymentPolicyId: type === 'payment' ? policyId : selectedPaymentPolicyId,
      returnPolicyId: type === 'return' ? policyId : selectedReturnPolicyId
    };
    onPoliciesChange(newPolicies);
  };

  const openCreateForm = (type: PolicyType) => {
    setCreatingType(type);
    setCreateError(null);
    setJustCreated(null);
    if (type === 'fulfillment') setFulfillmentForm(DEFAULT_FULFILLMENT_FORM);
    if (type === 'payment') setPaymentForm(DEFAULT_PAYMENT_FORM);
    if (type === 'return') setReturnForm(DEFAULT_RETURN_FORM);
  };

  const closeCreateForm = () => {
    setCreatingType(null);
    setCreateError(null);
  };

  const appendPolicyAndSelect = (type: PolicyType, policy: BusinessPolicy) => {
    setPolicies((prev) => {
      if (type === 'fulfillment') {
        return { ...prev, fulfillment_policies: [...prev.fulfillment_policies, policy] };
      }
      if (type === 'payment') {
        return { ...prev, payment_policies: [...prev.payment_policies, policy] };
      }
      return { ...prev, return_policies: [...prev.return_policies, policy] };
    });
    handlePolicyChange(type, policy.policyId);
    setCreatingType(null);
    setJustCreated(type);
    setTimeout(() => setJustCreated(null), 4000);
  };

  const handleCreateSubmit = async (type: PolicyType) => {
    setCreateError(null);

    if (type === 'fulfillment') {
      if (!fulfillmentForm.name.trim()) {
        setCreateError('Please enter a policy name.');
        return;
      }
      let shippingCost: number | undefined;
      if (!fulfillmentForm.freeShipping) {
        shippingCost = parseFloat(fulfillmentForm.shippingCost);
        if (isNaN(shippingCost) || shippingCost <= 0) {
          setCreateError('Please enter a valid shipping cost greater than $0.');
          return;
        }
      }
      setCreateSubmitting(true);
      try {
        const policy = await createFulfillmentPolicy({
          name: fulfillmentForm.name.trim(),
          handling_time_days: fulfillmentForm.handlingTimeDays,
          free_shipping: fulfillmentForm.freeShipping,
          shipping_cost: shippingCost,
        });
        appendPolicyAndSelect('fulfillment', {
          policyId: (policy as any).fulfillmentPolicyId || (policy as any).policyId,
          name: fulfillmentForm.name.trim(),
        });
      } catch (err) {
        setCreateError(err instanceof APIError ? err.message : 'Failed to create shipping policy.');
      } finally {
        setCreateSubmitting(false);
      }
      return;
    }

    if (type === 'payment') {
      if (!paymentForm.name.trim()) {
        setCreateError('Please enter a policy name.');
        return;
      }
      setCreateSubmitting(true);
      try {
        const policy = await createPaymentPolicy({
          name: paymentForm.name.trim(),
          immediate_pay_required: paymentForm.immediatePayRequired,
        });
        appendPolicyAndSelect('payment', {
          policyId: (policy as any).paymentPolicyId || (policy as any).policyId,
          name: paymentForm.name.trim(),
        });
      } catch (err) {
        setCreateError(err instanceof APIError ? err.message : 'Failed to create payment policy.');
      } finally {
        setCreateSubmitting(false);
      }
      return;
    }

    // return
    if (!returnForm.name.trim()) {
      setCreateError('Please enter a policy name.');
      return;
    }
    setCreateSubmitting(true);
    try {
      const policy = await createReturnPolicy({
        name: returnForm.name.trim(),
        returns_accepted: returnForm.returnsAccepted,
        return_period_days: returnForm.returnPeriodDays,
        refund_method: returnForm.refundMethod,
        return_shipping_payer: returnForm.returnShippingPayer,
      });
      appendPolicyAndSelect('return', {
        policyId: (policy as any).returnPolicyId || (policy as any).policyId,
        name: returnForm.name.trim(),
      });
    } catch (err) {
      setCreateError(err instanceof APIError ? err.message : 'Failed to create return policy.');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const CreateToggle = ({ type, label }: { type: PolicyType; label: string }) => (
    <button
      type="button"
      onClick={() => (creatingType === type ? closeCreateForm() : openCreateForm(type))}
      className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700"
    >
      {creatingType === type ? (
        <>
          <X className="w-4 h-4" /> Cancel
        </>
      ) : (
        <>
          <Plus className="w-4 h-4" /> {label}
        </>
      )}
    </button>
  );

  const CreateFormError = ({ type }: { type: PolicyType }) =>
    createError ? (
      <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
        <p>{createError}</p>
        {isOptInError(createError) && (
          <button
            type="button"
            onClick={() => handleOptIn(type)}
            disabled={optingIn}
            className="mt-2 inline-flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium"
          >
            {optingIn && <Loader2 className="w-4 h-4 animate-spin" />}
            Enable Business Policies
          </button>
        )}
      </div>
    ) : null;

  const inputClass =
    'w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent';

  if (loading) {
    return (
      <div className="p-8 text-center">
        <Loader2 className="w-12 h-12 mx-auto mb-3 text-blue-600 animate-spin" />
        <p className="text-gray-600">Loading business policies...</p>
      </div>
    );
  }

  if (error) {
    const needsOptIn = isOptInError(error);

    return (
      <div className="p-6 bg-amber-50 border border-amber-200 rounded-lg">
        <div className="flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5" />
          <div className="flex-1">
            <h3 className="font-medium text-amber-900 mb-2">Business Policies Required</h3>

            {needsOptIn ? (
              <p className="text-sm text-amber-800 mb-4">
                Your eBay account hasn't been opted in to Business Policies yet - a one-time step
                eBay requires before any shipping, payment, or return policy can be read or created.
                Click below to enable it, right here in the app.
              </p>
            ) : (
              <p className="text-sm text-amber-800 mb-4">{error}</p>
            )}

            <div className="space-y-2 text-sm text-amber-800">
              <p className="font-medium">To create listings, you need to set up:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Shipping (Fulfillment) Policy - How you'll ship items</li>
                <li>Payment Policy - How buyers will pay</li>
                <li>Return Policy - Your return terms</li>
              </ul>
              <div className="mt-4 p-3 bg-amber-100 rounded border border-amber-300">
                <p className="font-medium mb-2">You can create these right here - no need to leave the app:</p>
                <ul className="list-disc list-inside space-y-1 ml-2 text-xs">
                  <li><strong>Shipping:</strong> pick handling time and cost</li>
                  <li><strong>Payment:</strong> choose whether immediate payment is required</li>
                  <li><strong>Return:</strong> choose your return window and terms</li>
                </ul>
              </div>
            </div>
            <div className="mt-4 flex gap-3">
              {needsOptIn && (
                <button
                  onClick={() => handleOptIn()}
                  disabled={optingIn}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium"
                >
                  {optingIn && <Loader2 className="w-4 h-4 animate-spin" />}
                  Enable Business Policies
                </button>
              )}
              <button
                onClick={fetchPolicies}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm font-medium"
              >
                Try Again
              </button>
            </div>
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
          Select one of each type below, or create a new one without leaving the app.
          If you skip this, a default policy will be created for you automatically when you publish.
        </p>
      </div>

      {/* Fulfillment (Shipping) Policy */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <Package className="w-4 h-4" />
          Shipping Policy
        </label>
        <select
          value={selectedFulfillmentPolicyId}
          onChange={(e) => handlePolicyChange('fulfillment', e.target.value)}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.fulfillment ? 'border-red-500' : 'border-gray-300'
          }`}
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

        <CreateToggle type="fulfillment" label="Create new shipping policy" />

        {creatingType === 'fulfillment' && (
          <div className="mt-3 p-4 border border-gray-200 rounded-lg bg-gray-50 space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Policy name</label>
              <input
                type="text"
                className={inputClass}
                placeholder="e.g. Standard Shipping"
                value={fulfillmentForm.name}
                onChange={(e) => setFulfillmentForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Handling time</label>
              <select
                className={inputClass}
                value={fulfillmentForm.handlingTimeDays}
                onChange={(e) => setFulfillmentForm((f) => ({ ...f, handlingTimeDays: Number(e.target.value) }))}
              >
                <option value={1}>1 business day</option>
                <option value={2}>2 business days</option>
                <option value={3}>3 business days</option>
              </select>
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={fulfillmentForm.freeShipping}
                onChange={(e) => setFulfillmentForm((f) => ({ ...f, freeShipping: e.target.checked }))}
              />
              Offer free domestic shipping
            </label>
            {!fulfillmentForm.freeShipping && (
              <div>
                <label className="block text-xs font-medium text-gray-700 mb-1">Domestic shipping cost (USD)</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  className={inputClass}
                  value={fulfillmentForm.shippingCost}
                  onChange={(e) => setFulfillmentForm((f) => ({ ...f, shippingCost: e.target.value }))}
                />
              </div>
            )}
            <CreateFormError type="fulfillment" />
            <button
              type="button"
              disabled={createSubmitting}
              onClick={() => handleCreateSubmit('fulfillment')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium"
            >
              {createSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Create shipping policy
            </button>
          </div>
        )}

        {justCreated === 'fulfillment' && (
          <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded text-sm text-green-800 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" /> Created and selected
          </div>
        )}

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
          Payment Policy
        </label>
        <select
          value={selectedPaymentPolicyId}
          onChange={(e) => handlePolicyChange('payment', e.target.value)}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.payment ? 'border-red-500' : 'border-gray-300'
          }`}
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

        <CreateToggle type="payment" label="Create new payment policy" />

        {creatingType === 'payment' && (
          <div className="mt-3 p-4 border border-gray-200 rounded-lg bg-gray-50 space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Policy name</label>
              <input
                type="text"
                className={inputClass}
                placeholder="e.g. Standard Payment"
                value={paymentForm.name}
                onChange={(e) => setPaymentForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={paymentForm.immediatePayRequired}
                onChange={(e) => setPaymentForm((f) => ({ ...f, immediatePayRequired: e.target.checked }))}
              />
              Require immediate payment
            </label>
            <CreateFormError type="payment" />
            <button
              type="button"
              disabled={createSubmitting}
              onClick={() => handleCreateSubmit('payment')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium"
            >
              {createSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Create payment policy
            </button>
          </div>
        )}

        {justCreated === 'payment' && (
          <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded text-sm text-green-800 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" /> Created and selected
          </div>
        )}
      </div>

      {/* Return Policy */}
      <div>
        <label className="flex items-center gap-2 text-sm font-medium text-gray-700 mb-2">
          <RefreshCw className="w-4 h-4" />
          Return Policy
        </label>
        <select
          value={selectedReturnPolicyId}
          onChange={(e) => handlePolicyChange('return', e.target.value)}
          className={`w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
            errors.return ? 'border-red-500' : 'border-gray-300'
          }`}
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

        <CreateToggle type="return" label="Create new return policy" />

        {creatingType === 'return' && (
          <div className="mt-3 p-4 border border-gray-200 rounded-lg bg-gray-50 space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-700 mb-1">Policy name</label>
              <input
                type="text"
                className={inputClass}
                placeholder="e.g. 30-Day Returns"
                value={returnForm.name}
                onChange={(e) => setReturnForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input
                type="checkbox"
                checked={returnForm.returnsAccepted}
                onChange={(e) => setReturnForm((f) => ({ ...f, returnsAccepted: e.target.checked }))}
              />
              Accept returns
            </label>
            {returnForm.returnsAccepted && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Return period</label>
                  <select
                    className={inputClass}
                    value={returnForm.returnPeriodDays}
                    onChange={(e) => setReturnForm((f) => ({ ...f, returnPeriodDays: Number(e.target.value) }))}
                  >
                    <option value={30}>30 days</option>
                    <option value={60}>60 days</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Who pays return shipping</label>
                  <select
                    className={inputClass}
                    value={returnForm.returnShippingPayer}
                    onChange={(e) => setReturnForm((f) => ({ ...f, returnShippingPayer: e.target.value }))}
                  >
                    <option value="BUYER">Buyer</option>
                    <option value="SELLER">Seller</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 mb-1">Refund method</label>
                  <select
                    className={inputClass}
                    value={returnForm.refundMethod}
                    onChange={(e) => setReturnForm((f) => ({ ...f, refundMethod: e.target.value }))}
                  >
                    <option value="MONEY_BACK">Money back</option>
                    <option value="MERCHANDISE_CREDIT">Merchandise credit</option>
                  </select>
                </div>
              </>
            )}
            <CreateFormError type="return" />
            <button
              type="button"
              disabled={createSubmitting}
              onClick={() => handleCreateSubmit('return')}
              className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white rounded-lg text-sm font-medium"
            >
              {createSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Create return policy
            </button>
          </div>
        )}

        {justCreated === 'return' && (
          <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded text-sm text-green-800 flex items-center gap-2">
            <CheckCircle className="w-4 h-4" /> Created and selected
          </div>
        )}
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
