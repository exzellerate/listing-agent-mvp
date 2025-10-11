import { useState } from 'react';
import { Platform, AnalysisResult } from './types';
import { analyzeImage } from './services/api';
import ImageUpload from './components/ImageUpload';
import PlatformSelector from './components/PlatformSelector';
import LoadingState from './components/LoadingState';
import ResultsForm from './components/ResultsForm';

function App() {
  const [platform, setPlatform] = useState<Platform>('ebay');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleImageSelect = (file: File) => {
    setSelectedFile(file);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!selectedFile) {
      setError('Please select an image first');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      console.log('Analyzing image with platform:', platform);
      const analysisResult = await analyzeImage(selectedFile, platform);
      console.log('Analysis result:', analysisResult);
      setResult(analysisResult);
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err instanceof Error ? err.message : 'Failed to analyze image');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setResult(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-gray-900">
            Listing Agent
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            AI-powered marketplace listing generator using Claude Vision
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-white rounded-lg shadow-md p-6 space-y-6">
          {/* Platform Selector */}
          <PlatformSelector
            selected={platform}
            onChange={setPlatform}
            disabled={loading}
          />

          {/* Image Upload */}
          <ImageUpload
            onImageSelect={handleImageSelect}
            disabled={loading}
          />

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleAnalyze}
              disabled={!selectedFile || loading}
              className={`
                flex-1 px-6 py-3 rounded-lg font-semibold text-white transition-all
                ${selectedFile && !loading
                  ? 'bg-blue-600 hover:bg-blue-700 cursor-pointer'
                  : 'bg-gray-300 cursor-not-allowed'
                }
              `}
            >
              {loading ? 'Analyzing...' : 'Analyze Image'}
            </button>

            {(selectedFile || result) && (
              <button
                onClick={handleReset}
                disabled={loading}
                className="px-6 py-3 bg-gray-200 hover:bg-gray-300 rounded-lg font-semibold text-gray-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Start Over
              </button>
            )}
          </div>

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start">
                <svg
                  className="h-5 w-5 text-red-600 mt-0.5 mr-2"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
                <div>
                  <h3 className="font-semibold text-red-900">Error</h3>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
            </div>
          )}

          {/* Loading State */}
          {loading && <LoadingState />}

          {/* Results */}
          {result && !loading && (
            <div className="border-t pt-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                Generated Listing
              </h2>
              <ResultsForm result={result} />
            </div>
          )}
        </div>

        {/* Footer Info */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>
            Powered by Claude AI Vision | Upload a product image to generate optimized marketplace listings
          </p>
        </div>
      </main>
    </div>
  );
}

export default App;
