import { useState } from 'react';
import { TestBatchResponse, TestItemResult } from '../types';
import { runBatchTests, APIError } from '../services/api';

type FilterType = 'all' | 'passed' | 'failed';

export default function TestingPage() {
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<TestBatchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterType>('all');
  const [selectedTest, setSelectedTest] = useState<TestItemResult | null>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.csv')) {
        setError('Please select a CSV file');
        return;
      }
      setCsvFile(file);
      setError(null);
    }
  };

  const handleRunTests = async () => {
    if (!csvFile) {
      setError('Please select a CSV file first');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const testResults = await runBatchTests(csvFile);
      setResults(testResults);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError('Failed to run tests. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  // Sort and filter results (most recent first)
  const filteredAndSortedResults = results?.results
    .filter(result => {
      if (filter === 'all') return true;
      if (filter === 'passed') return result.status === 'passed';
      if (filter === 'failed') return result.status === 'failed' || result.status === 'error';
      return true;
    })
    .sort((a, b) => {
      // Sort by timestamp if available, otherwise by test_id
      if (a.timestamp && b.timestamp) {
        return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
      }
      return b.test_id - a.test_id;
    });

  const exportResults = () => {
    if (!results) return;

    const dataStr = JSON.stringify(results, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,' + encodeURIComponent(dataStr);
    const exportFileDefaultName = `test-results-${new Date().toISOString().split('T')[0]}.json`;

    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const getScoreColor = (score: number) => {
    if (score >= 85) return 'text-green-600 bg-green-100';
    if (score >= 70) return 'text-yellow-600 bg-yellow-100';
    return 'text-red-600 bg-red-100';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'passed':
        return <span className="px-3 py-1 rounded-full text-sm font-bold bg-green-100 text-green-700">✅ Passed</span>;
      case 'failed':
        return <span className="px-3 py-1 rounded-full text-sm font-bold bg-red-100 text-red-700">❌ Failed</span>;
      case 'error':
        return <span className="px-3 py-1 rounded-full text-sm font-bold bg-orange-100 text-orange-700">⚠️ Error</span>;
      default:
        return <span className="px-3 py-1 rounded-full text-sm font-bold bg-gray-100 text-gray-700">{status}</span>;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 via-pink-50 to-blue-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                Testing Dashboard
              </h1>
              <p className="mt-2 text-sm text-gray-600">
                Validate image analysis and pricing accuracy with batch testing
              </p>
            </div>
            <a
              href="/"
              className="px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg font-medium text-gray-700 transition-colors"
            >
              ← Back to App
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Upload Section */}
        <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200 p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Upload Test Data</h2>

          <div className="space-y-4">
            {/* CSV File Upload */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Test CSV File
              </label>
              <div className="flex gap-4">
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileSelect}
                  disabled={loading}
                  className="flex-1 px-4 py-3 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-purple-500 disabled:opacity-50"
                />
                {csvFile && (
                  <div className="flex items-center gap-2 px-4 py-2 bg-green-50 border border-green-200 rounded-lg">
                    <span className="text-green-700 font-medium">✓ {csvFile.name}</span>
                  </div>
                )}
              </div>
              <p className="mt-2 text-sm text-gray-500">
                Upload a CSV file with test cases. Format: image_path, expected values, platform, etc.
              </p>
            </div>

            {/* Run Tests Button */}
            <button
              onClick={handleRunTests}
              disabled={!csvFile || loading}
              className={`
                w-full px-8 py-4 rounded-xl font-bold text-white text-lg transition-all duration-300 transform
                ${csvFile && !loading
                  ? 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 hover:scale-105 shadow-lg hover:shadow-xl cursor-pointer'
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
                  Running Tests...
                </span>
              ) : '🚀 Run Batch Tests'}
            </button>
          </div>

          {/* Error Message */}
          {error && (
            <div className="mt-4 bg-red-50 border-2 border-red-200 rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg className="w-4 h-4 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="flex-1">
                  <p className="text-red-800 font-medium">{error}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Results Section */}
        {results && (
          <div className="space-y-8 animate-fadeIn">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white shadow-lg">
                <div className="text-3xl font-bold">{results.summary.total_tests}</div>
                <div className="text-blue-100 mt-1">Total Tests</div>
              </div>
              <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white shadow-lg">
                <div className="text-3xl font-bold">{results.summary.passed}</div>
                <div className="text-green-100 mt-1">Passed ({results.summary.pass_rate.toFixed(1)}%)</div>
              </div>
              <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl p-6 text-white shadow-lg">
                <div className="text-3xl font-bold">{results.summary.failed}</div>
                <div className="text-red-100 mt-1">Failed</div>
              </div>
              <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white shadow-lg">
                <div className="text-3xl font-bold">{results.summary.avg_score.toFixed(1)}%</div>
                <div className="text-purple-100 mt-1">Avg Score</div>
              </div>
            </div>

            {/* Field Accuracy */}
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200 p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Field Accuracy</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(results.summary.field_accuracy).map(([field, accuracy]) => (
                  <div key={field} className="bg-gray-50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-gray-600 capitalize">
                        {field.replace('_', ' ')}
                      </span>
                      <span className={`text-lg font-bold ${getScoreColor(accuracy)}`}>
                        {accuracy.toFixed(1)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${accuracy >= 85 ? 'bg-green-500' : accuracy >= 70 ? 'bg-yellow-500' : 'bg-red-500'}`}
                        style={{ width: `${accuracy}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Test Results Table */}
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
              <div className="p-6 border-b border-gray-200">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-bold text-gray-900">Test Results</h3>
                  <div className="flex gap-2">
                    {/* Filter Buttons */}
                    <button
                      onClick={() => setFilter('all')}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        filter === 'all'
                          ? 'bg-purple-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      All ({results.results.length})
                    </button>
                    <button
                      onClick={() => setFilter('passed')}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        filter === 'passed'
                          ? 'bg-green-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Passed ({results.summary.passed})
                    </button>
                    <button
                      onClick={() => setFilter('failed')}
                      className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                        filter === 'failed'
                          ? 'bg-red-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      Failed ({results.summary.failed})
                    </button>
                    <button
                      onClick={exportResults}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors ml-4"
                    >
                      📥 Export JSON
                    </button>
                  </div>
                </div>
              </div>

              <div className="divide-y divide-gray-200">
                {filteredAndSortedResults?.map((result) => (
                  <div
                    key={result.test_id}
                    className="p-6 hover:bg-gray-50 transition-colors cursor-pointer"
                    onClick={() => setSelectedTest(result)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-4 mb-2">
                          <span className="text-sm font-bold text-gray-500">Test #{result.test_id}</span>
                          {result.timestamp && (
                            <span className="text-xs font-medium text-blue-600 bg-blue-50 px-2 py-1 rounded">
                              {new Date(result.timestamp).toLocaleString()}
                            </span>
                          )}
                          {getStatusBadge(result.status)}
                          <span className={`px-3 py-1 rounded-full text-sm font-bold ${getScoreColor(result.overall_score)}`}>
                            {result.overall_score.toFixed(1)}%
                          </span>
                        </div>
                        <div className="text-gray-700 font-medium">{result.image_path}</div>
                        <div className="text-sm text-gray-500 mt-1">
                          Duration: {result.duration_seconds.toFixed(2)}s
                        </div>
                        {result.status === 'error' && result.error_type && (
                          <div className="mt-2 text-sm">
                            <span className="font-semibold text-orange-700">Error: </span>
                            <span className="text-orange-600">{result.error_type}</span>
                            {result.error_details && (
                              <div className="text-orange-600 mt-1">{result.error_details}</div>
                            )}
                          </div>
                        )}
                      </div>
                      <button
                        className="px-4 py-2 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded-lg font-medium transition-colors"
                      >
                        View Details →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Test Detail Modal */}
        {selectedTest && (
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50"
            onClick={() => setSelectedTest(null)}
          >
            <div
              className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="sticky top-0 bg-white border-b border-gray-200 p-6 flex items-center justify-between">
                <div>
                  <h3 className="text-2xl font-bold text-gray-900">
                    Test #{selectedTest.test_id} Details
                  </h3>
                  <p className="text-gray-600 mt-1">{selectedTest.image_path}</p>
                </div>
                <button
                  onClick={() => setSelectedTest(null)}
                  className="w-10 h-10 bg-gray-100 hover:bg-gray-200 rounded-full flex items-center justify-center transition-colors"
                >
                  ✕
                </button>
              </div>

              <div className="p-6 space-y-6">
                {/* Overall Stats */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">Status</div>
                    <div className="mt-2">{getStatusBadge(selectedTest.status)}</div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">Overall Score</div>
                    <div className={`mt-2 text-2xl font-bold ${getScoreColor(selectedTest.overall_score)}`}>
                      {selectedTest.overall_score.toFixed(1)}%
                    </div>
                  </div>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <div className="text-sm text-gray-600">Duration</div>
                    <div className="mt-2 text-2xl font-bold text-gray-900">
                      {selectedTest.duration_seconds.toFixed(2)}s
                    </div>
                  </div>
                </div>

                {/* Error Details Section */}
                {selectedTest.status === 'error' && selectedTest.error_type && (
                  <div className="bg-orange-50 border-2 border-orange-200 rounded-xl p-6">
                    <h4 className="text-lg font-bold text-orange-900 mb-4 flex items-center gap-2">
                      <span>⚠️</span> Error Details
                    </h4>
                    <div className="space-y-3">
                      <div>
                        <div className="text-sm font-semibold text-orange-800 mb-1">Error Type:</div>
                        <div className="font-mono text-orange-700 bg-white px-3 py-2 rounded border border-orange-300">
                          {selectedTest.error_type}
                        </div>
                      </div>
                      {selectedTest.error_details && (
                        <div>
                          <div className="text-sm font-semibold text-orange-800 mb-1">Error Message:</div>
                          <div className="text-orange-700 bg-white px-3 py-2 rounded border border-orange-300">
                            {selectedTest.error_details}
                          </div>
                        </div>
                      )}
                      {selectedTest.error_traceback && (
                        <details className="cursor-pointer">
                          <summary className="text-sm font-semibold text-orange-800 mb-1 hover:text-orange-900">
                            Full Traceback (click to expand)
                          </summary>
                          <pre className="mt-2 text-xs font-mono text-orange-700 bg-white px-3 py-2 rounded border border-orange-300 overflow-x-auto whitespace-pre-wrap">
                            {selectedTest.error_traceback}
                          </pre>
                        </details>
                      )}
                    </div>
                  </div>
                )}

                {/* Field-by-Field Analysis */}
                <div>
                  <h4 className="text-lg font-bold text-gray-900 mb-4">Field Analysis</h4>
                  <div className="space-y-4">
                    {Object.entries(selectedTest.analysis).map(([field, data]) => (
                      <div key={field} className={`border-2 rounded-lg p-4 ${data.passed ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-bold text-gray-900 capitalize">
                            {field.replace('_', ' ')}
                          </span>
                          <div className="flex items-center gap-2">
                            <span className={`px-3 py-1 rounded-full text-sm font-bold ${getScoreColor(data.score)}`}>
                              {typeof data.score === 'number' ? `${data.score.toFixed(1)}%` : data.score}
                            </span>
                            {data.passed ? (
                              <span className="text-green-600 font-bold">✓</span>
                            ) : (
                              <span className="text-red-600 font-bold">✗</span>
                            )}
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <div className="text-gray-600 font-medium">Expected:</div>
                            <div className="mt-1 font-mono bg-white p-2 rounded border border-gray-200">
                              {Array.isArray(data.expected) ? data.expected.join(', ') : String(data.expected)}
                            </div>
                          </div>
                          <div>
                            <div className="text-gray-600 font-medium">Actual:</div>
                            <div className="mt-1 font-mono bg-white p-2 rounded border border-gray-200">
                              {Array.isArray(data.actual) ? data.actual.join(', ') : String(data.actual)}
                            </div>
                          </div>
                        </div>
                        {data.details && (
                          <div className="mt-2 text-sm text-gray-600 italic">
                            {data.details}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
