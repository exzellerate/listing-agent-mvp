import { useState, useEffect } from 'react';
import { Platform, AnalysisResult, UserAction } from '../types';
import { analyzeImages, checkHealth, confirmAnalysis, createDraft, getDraft, APIError } from '../services/api';
import ImageUpload from '../components/ImageUpload';
import LoadingState from '../components/LoadingState';
import ResultsForm from '../components/ResultsForm';
import PricingSection from '../components/PricingSection';
import CorrectionModal, { CorrectionData } from '../components/CorrectionModal';
import { EbayPostingSection } from '../components/EbayPostingSection';
import { CategoryAspectsSection } from '../components/CategoryAspectsSection';
import Layout from '../components/Layout';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface ErrorState {
  message: string;
  details?: string;
  statusCode?: number;
}

function UploadPage() {
  const [platform, setPlatform] = useState<Platform>('ebay');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [userContext, setUserContext] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<ErrorState | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [selectedPrice, setSelectedPrice] = useState<number | undefined>(undefined);
  const [showCorrectionModal, setShowCorrectionModal] = useState(false);
  const [correctionAction, setCorrectionAction] = useState<'edited' | 'rejected'>('edited');
  const [savingDraft, setSavingDraft] = useState(false);
  const [loadedFromDraft, setLoadedFromDraft] = useState(false);
  const [ebayEnvironment, setEbayEnvironment] = useState<{ mode: string; isProduction: boolean } | null>(null);
  const [showStartOverConfirmation, setShowStartOverConfirmation] = useState(false);

  // Check backend health on mount
  useEffect(() => {
    const checkBackendHealth = async () => {
      const healthy = await checkHealth();
      setBackendHealthy(healthy);
      if (!healthy) {
        setError({
          message: 'Backend server is not responding',
          details: `Please ensure the backend is running and accessible at ${API_BASE_URL}`,
          statusCode: 0,
        });
      }
    };
    checkBackendHealth();
  }, []);

  // Fetch eBay environment mode on mount
  useEffect(() => {
    const fetchEbayEnvironment = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/ebay/auth/status`);
        if (response.ok) {
          const data = await response.json();
          if (data.environment) {
            setEbayEnvironment({
              mode: data.environment,
              isProduction: data.is_production || false,
            });
          }
        }
      } catch (error) {
        console.log('Could not fetch eBay environment:', error);
        // Silently fail - environment indicator is optional
      }
    };
    fetchEbayEnvironment();
  }, []);

  // Load draft if draftId is provided in URL
  useEffect(() => {
    const loadDraftFromUrl = async () => {
      const params = new URLSearchParams(window.location.search);
      const draftId = params.get('draftId');

      if (draftId) {
        setLoading(true);
        try {
          const draft = await getDraft(parseInt(draftId, 10));

          // Convert draft to AnalysisResult format
          const analysisResult: AnalysisResult = {
            product_name: draft.product_name || '',
            brand: draft.brand,
            category: draft.category,
            condition: draft.condition || 'Used',
            color: draft.color,
            material: draft.material,
            model_number: draft.model_number,
            key_features: draft.features || [],
            suggested_title: draft.title,
            suggested_description: draft.description,
            confidence_score: 1.0,
            images_analyzed: 0,
            individual_analyses: [],
            discrepancies: [],
            verification_notes: null,
            analysis_confidence: 1.0,
            visible_components: [],
            completeness_status: 'unknown',
            missing_components: null,
            ambiguities: [],
            reasoning: null,
            analysis_id: draft.analysis_id || undefined,
          };

          setResult(analysisResult);
          setPlatform(draft.platform);
          if (draft.price) {
            setSelectedPrice(draft.price);
          }
          setLoadedFromDraft(true);

          // Clear the URL parameter
          window.history.replaceState({}, '', '/');
        } catch (err) {
          console.error('Failed to load draft:', err);
          setError({
            message: 'Failed to load draft',
            details: err instanceof Error ? err.message : 'Unknown error',
            statusCode: 500,
          });
        } finally {
          setLoading(false);
        }
      }
    };

    loadDraftFromUrl();
  }, []);

  const handleImagesSelect = (files: File[]) => {
    setSelectedFiles(files);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0) {
      setError({
        message: 'Please select at least one image first',
        statusCode: 400,
      });
      return;
    }

    // Check backend health before analyzing
    if (backendHealthy === false) {
      setError({
        message: 'Cannot analyze: Backend server is not available',
        details: 'Please start the backend server and try again',
        statusCode: 0,
      });
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      console.log(`Analyzing ${selectedFiles.length} image(s) with platform:`, platform);
      console.log('User context:', userContext); // DEBUG
      const analysisResult = await analyzeImages(selectedFiles, platform, userContext);
      console.log('Analysis result:', analysisResult);
      setResult(analysisResult);
    } catch (err) {
      console.error('Analysis error:', err);

      if (err instanceof APIError) {
        setError({
          message: err.message,
          details: err.details,
          statusCode: err.statusCode,
        });
      } else if (err instanceof Error) {
        setError({
          message: err.message,
          statusCode: 500,
        });
      } else {
        setError({
          message: 'An unexpected error occurred',
          details: 'Please try again or contact support if the problem persists',
          statusCode: 500,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFiles([]);
    setResult(null);
    setError(null);
    setSelectedPrice(undefined);
  };

  const handleStartOverWithConfirmation = () => {
    setShowStartOverConfirmation(true);
  };

  const confirmStartOver = () => {
    setShowStartOverConfirmation(false);
    handleReset();
  };

  const cancelStartOver = () => {
    setShowStartOverConfirmation(false);
  };

  const handlePriceSelected = (price: number) => {
    setSelectedPrice(price);
  };

  const handleFeedback = async (action: UserAction) => {
    if (!result?.analysis_id) {
      console.error('No analysis ID available for feedback');
      return;
    }

    try {
      console.log(`Sending feedback: ${action} for analysis ${result.analysis_id}`);

      await confirmAnalysis({
        analysis_id: result.analysis_id,
        user_action: action,
      });

      console.log('Feedback sent successfully');
    } catch (err) {
      console.error('Failed to send feedback:', err);
      // Don't show error to user - feedback is optional
    }
  };

  const handleRequestCorrection = (action: 'edited' | 'rejected') => {
    setCorrectionAction(action);
    setShowCorrectionModal(true);
  };

  const handleSubmitCorrection = async (corrections: CorrectionData) => {
    if (!result?.analysis_id) {
      console.error('No analysis ID available for correction');
      return;
    }

    try {
      console.log(`Submitting corrections with action: ${correctionAction}`);

      await confirmAnalysis({
        analysis_id: result.analysis_id,
        user_action: correctionAction,
        ...corrections,
      });

      console.log('Corrections submitted successfully');
      setShowCorrectionModal(false);
    } catch (err) {
      console.error('Failed to submit corrections:', err);
      throw err; // Re-throw so modal can handle it
    }
  };

  const retryHealthCheck = async () => {
    setError(null);
    const healthy = await checkHealth();
    setBackendHealthy(healthy);
    if (!healthy) {
      setError({
        message: 'Backend server is still not responding',
        details: `Please ensure the backend is running and accessible at ${API_BASE_URL}`,
        statusCode: 0,
      });
    }
  };

  const handleSaveAsDraft = async () => {
    if (!result) {
      console.error('No analysis result to save');
      return;
    }

    setSavingDraft(true);
    try {
      // Convert File objects to base64 data URLs
      const imagePaths = await Promise.all(
        selectedFiles.map(file => {
          return new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result as string);
            reader.onerror = reject;
            reader.readAsDataURL(file);
          });
        })
      );

      await createDraft({
        analysis_id: result.analysis_id,
        title: result.suggested_title,
        description: result.suggested_description,
        price: selectedPrice,
        platform: platform,
        product_name: result.product_name,
        brand: result.brand,
        category: result.category,
        condition: result.condition,
        color: result.color,
        material: result.material,
        model_number: result.model_number,
        features: result.key_features,
        image_paths: imagePaths,
      });

      alert('Draft saved successfully! You can view it from the Drafts page.');
    } catch (err) {
      console.error('Failed to save draft:', err);
      alert('Failed to save draft. Please try again.');
    } finally {
      setSavingDraft(false);
    }
  };

  return (
    <Layout
      title="Upload & Analyze"
      subtitle="Upload your product images and let AI generate optimized listings"
    >
      {/* eBay Environment Indicator */}
      {ebayEnvironment && (
        <div className={`mb-6 inline-block px-3 py-1.5 rounded-lg font-bold text-xs border-2 ${
          ebayEnvironment.isProduction
            ? 'bg-red-50 border-red-500 text-red-700 animate-pulse'
            : 'bg-yellow-50 border-yellow-500 text-yellow-700'
        }`}>
          {ebayEnvironment.isProduction ? '🔴 PRODUCTION' : '🟡 SANDBOX'}
        </div>
      )}

      <div className="space-y-8">
        {/* Image Upload - Only show when no results yet */}
        {!loadedFromDraft && !result && (
          <ImageUpload
            onImagesSelect={handleImagesSelect}
            onContextChange={setUserContext}
            disabled={loading}
            selectedFiles={selectedFiles}
            userContext={userContext}
          />
        )}

        {/* Action Buttons - Only show when no results */}
        {!loadedFromDraft && !result && (
          <div className="flex gap-4">
              <button
                onClick={handleAnalyze}
                disabled={selectedFiles.length === 0 || loading}
                className={`
                  flex-1 px-8 py-4 rounded-xl font-bold text-white text-lg transition-all duration-300 transform
                  ${selectedFiles.length > 0 && !loading
                    ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 hover:scale-105 shadow-lg hover:shadow-xl cursor-pointer'
                    : 'bg-gray-300 cursor-not-allowed opacity-60'
                  }
                `}
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Analyzing {selectedFiles.length} image{selectedFiles.length > 1 ? 's' : ''}...
                  </span>
                ) : `Analyze Image${selectedFiles.length > 1 ? 's' : ''}`}
              </button>

              {(selectedFiles.length > 0 || result) && (
                <button
                  onClick={handleReset}
                  disabled={loading}
                  className="px-6 py-4 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-gray-700 transition-all duration-300 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
                >
                  Start Over
                </button>
              )}
            </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border-2 border-red-200 rounded-xl p-6 shadow-lg animate-fadeIn">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center">
                  <svg
                    className="h-6 w-6 text-red-600"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-lg text-red-900 mb-2">
                  {error.statusCode === 0 && "I couldn't connect to the server"}
                  {error.statusCode === 400 && "I couldn't process your request"}
                  {error.statusCode === 408 && "This is taking too long"}
                  {error.statusCode === 413 && "Your image file is too big"}
                  {error.statusCode === 500 && "I couldn't understand this image"}
                  {error.statusCode === 503 && "I'm temporarily unavailable"}
                  {(!error.statusCode || (error.statusCode > 0 && ![0, 400, 408, 413, 500, 503].includes(error.statusCode))) && 'Something went wrong'}
                </h3>
                <p className="text-red-800">
                  {error.statusCode === 0 && "I'm having trouble connecting to the backend server. Please make sure it's running and try again."}
                  {error.statusCode === 400 && "There was a problem with the image or information you provided. Please check and try again."}
                  {error.statusCode === 408 && "The analysis is taking longer than expected. This usually happens with large files or multiple images."}
                  {error.statusCode === 413 && "The image you uploaded is larger than 10MB. Please use a smaller image file."}
                  {error.statusCode === 500 && "I couldn't analyze this product image. It might be unclear, too dark, or not showing a physical product."}
                  {error.statusCode === 503 && "The service is temporarily busy or under maintenance. Please wait a moment and try again."}
                  {(!error.statusCode || (error.statusCode > 0 && ![0, 400, 408, 413, 500, 503].includes(error.statusCode))) && (error.message || "An unexpected error occurred. Please try again.")}
                </p>

                {/* Helpful suggestions based on error type */}
                {error.statusCode === 500 && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800 font-medium mb-2">💡 What you can try:</p>
                    <ul className="text-sm text-yellow-700 list-disc list-inside space-y-1">
                      <li>Upload a clearer or different image of the product</li>
                      <li>Make sure the product is clearly visible and well-lit</li>
                      <li>Avoid blurry, dark, or low-quality photos</li>
                      <li>Ensure the image shows a physical item (not just text, screenshots, or graphics)</li>
                    </ul>
                  </div>
                )}

                {error.statusCode === 408 && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800 font-medium mb-2">💡 What you can try:</p>
                    <p className="text-sm text-yellow-700">The analysis took too long to complete. Try uploading fewer images at once or compress your images to smaller file sizes.</p>
                  </div>
                )}

                {error.statusCode === 400 && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800 font-medium mb-2">💡 What you can try:</p>
                    <p className="text-sm text-yellow-700">Make sure you've uploaded valid image files (JPG, PNG, WebP, or GIF) and selected a platform.</p>
                  </div>
                )}

                {error.statusCode === 413 && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800 font-medium mb-2">💡 What you can try:</p>
                    <p className="text-sm text-yellow-700">Your image file is too large. Please reduce the file size to under 10MB per image and try again.</p>
                  </div>
                )}

                {error.statusCode === 503 && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800 font-medium mb-2">💡 What you can try:</p>
                    <p className="text-sm text-yellow-700">The server is temporarily busy or under maintenance. Please wait a few moments and try again.</p>
                  </div>
                )}

                {error.statusCode === 0 && (
                  <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <p className="text-sm text-yellow-800 font-medium mb-2">💡 What you can try:</p>
                    <p className="text-sm text-yellow-700">Make sure the backend server is running and you have a stable internet connection. Click "Retry Connection" below to try again.</p>
                  </div>
                )}

                {/* Action buttons */}
                <div className="mt-4 flex gap-2">
                  {error.statusCode === 0 && (
                    <button
                      onClick={retryHealthCheck}
                      className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors shadow-md"
                    >
                      Retry Connection
                    </button>
                  )}
                  {error.statusCode !== 0 && selectedFiles.length > 0 && (
                    <button
                      onClick={handleAnalyze}
                      disabled={loading}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      Try Again
                    </button>
                  )}
                  <button
                    onClick={handleReset}
                    className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded-lg font-medium transition-colors shadow-md"
                  >
                    Start Over
                  </button>
                </div>
              </div>
              <button
                onClick={() => setError(null)}
                className="flex-shrink-0 text-red-400 hover:text-red-600 transition-colors"
                aria-label="Dismiss error"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                </svg>
              </button>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && <LoadingState />}

        {/* Results */}
        {result && !loading && (
          <div className="border-t pt-8 animate-fadeIn space-y-8">

            {/* Analyzed Images Section - Show uploaded images for reference */}
            {!loadedFromDraft && selectedFiles.length > 0 && (
              <div>
                <div className="inline-block bg-blue-100 text-blue-700 text-xs font-medium px-3 py-1.5 rounded-md mb-3">
                  Analyzed Images
                </div>
                <div className="grid grid-cols-6 gap-2">
                  {selectedFiles.map((file, idx) => (
                    <div key={idx} className="relative group">
                      <div className="w-full aspect-square bg-gray-50 rounded-lg border-2 border-gray-200 overflow-hidden">
                        <img
                          src={URL.createObjectURL(file)}
                          alt={`Product ${idx + 1}`}
                          className="w-full h-full object-contain"
                        />
                      </div>
                      {idx === 0 && (
                        <div className="absolute top-1 left-1 bg-black text-white text-[10px] px-1.5 py-0.5 rounded font-medium">
                          Primary
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Draft Mode Badge */}
            {loadedFromDraft && (
              <div className="bg-green-50 border-2 border-green-200 rounded-xl p-4 flex items-center justify-between shadow-md">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-100 rounded-full flex items-center justify-center">
                    <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="font-bold text-green-900">Loaded from Draft</h3>
                    <p className="text-sm text-green-700">Ready to create your listing</p>
                  </div>
                </div>
                <a
                  href="/drafts"
                  className="px-4 py-2 bg-green-100 hover:bg-green-200 text-green-700 rounded-lg font-medium transition-colors flex items-center gap-2"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                  </svg>
                  Back to Drafts
                </a>
              </div>
            )}

            {/* Only show these sections when NOT loaded from draft */}
            {!loadedFromDraft && (
              <>
                {/* Action Buttons */}
                <div className="flex justify-center gap-4">
                  {/* Start Over Button */}
                  <button
                    onClick={handleStartOverWithConfirmation}
                    className="px-6 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-gray-700 transition-all duration-300 hover:scale-105 shadow-md flex items-center gap-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Start Over
                  </button>

                  {/* Save as Draft Button */}
                  <button
                    onClick={handleSaveAsDraft}
                    disabled={savingDraft}
                    className="px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 text-white rounded-xl font-bold transition-all duration-300 transform hover:scale-105 shadow-lg hover:shadow-xl disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none flex items-center gap-2"
                  >
                    {savingDraft ? (
                      <>
                        <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Saving...
                      </>
                    ) : (
                      <>
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                        </svg>
                        Save as Draft
                      </>
                    )}
                  </button>
                </div>
              </>
            )}

            {/* Show Generated Listing - always visible */}
            <div>
              <h2 className="text-3xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mb-6">
                {loadedFromDraft ? 'Listing Details' : 'Generated Listing'}
              </h2>
              <ResultsForm
                result={result}
                price={selectedPrice}
                onPriceChange={handlePriceSelected}
              />
            </div>

            {/* eBay Category & Aspects Section - only for eBay platform and not from draft */}
            {(() => {
              console.log('UploadPage.tsx - Checking CategoryAspectsSection conditions:');
              console.log('  platform:', platform);
              console.log('  platform === "ebay":', platform === 'ebay');
              console.log('  loadedFromDraft:', loadedFromDraft);
              console.log('  !loadedFromDraft:', !loadedFromDraft);
              console.log('  Should render:', platform === 'ebay' && !loadedFromDraft);
              console.log('  result.ebay_category_suggestions:', result?.ebay_category_suggestions);
              console.log('  result.suggested_category_id:', result?.suggested_category_id);
              return null;
            })()}
            {platform === 'ebay' && !loadedFromDraft && (
              <div>
                <h2 className="text-3xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent mb-6">
                  eBay Category & Item Specifics
                </h2>
                <CategoryAspectsSection result={result} />
              </div>
            )}

            {/* Pricing Research Section - only when NOT loaded from draft */}
            {!loadedFromDraft && (
              <div>
                <h2 className="text-3xl font-bold bg-gradient-to-r from-green-600 to-blue-600 bg-clip-text text-transparent mb-6">
                  Pricing Research
                </h2>
                <PricingSection
                  analysis={result}
                  platform={platform}
                  onPriceSelected={handlePriceSelected}
                />
              </div>
            )}

            {/* eBay Posting Section */}
            {platform === 'ebay' && (
              <>
                {loadedFromDraft && (
                  <div className="mb-4 bg-yellow-50 border-2 border-yellow-200 rounded-xl p-4">
                    <div className="flex items-start gap-3">
                      <svg className="w-6 h-6 text-yellow-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <div>
                        <h4 className="font-bold text-yellow-900">Note: Images from Draft</h4>
                        <p className="text-sm text-yellow-800 mt-1">
                          Original images from this draft are not available. You can upload new images in the eBay listing wizard if needed.
                        </p>
                      </div>
                    </div>
                  </div>
                )}
                <EbayPostingSection
                  result={result}
                  pricingData={selectedPrice ? { statistics: { suggested_price: selectedPrice } } as any : undefined}
                  analysisId={result.analysis_id}
                  imageFiles={loadedFromDraft ? [] : selectedFiles}
                />
              </>
            )}
          </div>
        )}
      </div>

      {/* Correction Modal */}
      {result && (
        <CorrectionModal
          isOpen={showCorrectionModal}
          onClose={() => setShowCorrectionModal(false)}
          onSubmit={handleSubmitCorrection}
          currentResult={result}
          action={correctionAction}
        />
      )}

      {/* Start Over Confirmation Modal */}
      {showStartOverConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 transform transition-all">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0">
                <svg className="w-6 h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-gray-900">Start Over?</h3>
                <p className="text-sm text-gray-600 mt-1">This will clear all your current analysis results and uploaded images.</p>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={cancelStartOver}
                className="flex-1 px-4 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-gray-700 transition-all duration-200"
              >
                Cancel
              </button>
              <button
                onClick={confirmStartOver}
                className="flex-1 px-4 py-3 bg-red-600 hover:bg-red-700 rounded-xl font-semibold text-white transition-all duration-200"
              >
                Clear & Start Over
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}

export default UploadPage;
