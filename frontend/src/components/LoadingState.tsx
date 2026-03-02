import { useEffect, useState } from 'react';

interface LoadingStateProps {
  stage?: string;
  stageMessage?: string;
  progress?: number;
  onCancel?: () => void;
}

const STAGE_LABELS: Record<string, string> = {
  validating: 'Validating images...',
  encoding: 'Encoding images...',
  analyzing: 'Analyzing your images...',
  searching: 'Searching for product info...',
  tool_use: 'Researching product details...',
  retrying: 'Retrying connection...',
  parsing: 'Parsing analysis results...',
  categorizing: 'Matching eBay categories...',
  complete: 'Analysis complete!',
};

export default function LoadingState({ stage, stageMessage, progress, onCancel }: LoadingStateProps) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setElapsed(s => s + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  const hasProgress = stage !== undefined && progress !== undefined;
  const displayMessage = stageMessage || STAGE_LABELS[stage || ''] || 'Analyzing your images...';

  return (
    <div className="flex flex-col items-center justify-center py-16 animate-fadeIn">
      {/* Spinner */}
      <div className="relative">
        <div className="animate-spin rounded-full h-20 w-20 border-4 border-blue-200"></div>
        <div className="animate-spin rounded-full h-20 w-20 border-4 border-t-blue-600 border-r-purple-600 absolute top-0 left-0"></div>
      </div>

      {/* Stage message */}
      <div className="mt-6 text-center space-y-2">
        <p className="text-xl font-semibold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
          {displayMessage}
        </p>
        <p className="text-sm text-gray-500">
          Elapsed: {formatTime(elapsed)}
          {!hasProgress && ' — This may take 1-3 minutes'}
        </p>
      </div>

      {/* Progress bar */}
      {hasProgress ? (
        <div className="mt-6 w-80">
          <div className="w-full bg-gray-200 rounded-full h-2.5">
            <div
              className="bg-gradient-to-r from-blue-600 to-purple-600 h-2.5 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${Math.min(progress, 100)}%` }}
            ></div>
          </div>
          <p className="text-xs text-gray-400 text-center mt-1">{progress}%</p>
        </div>
      ) : (
        <div className="mt-6 flex gap-2">
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0s' }}></div>
          <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
        </div>
      )}

      {/* Cancel button */}
      {onCancel && (
        <button
          onClick={onCancel}
          className="mt-6 text-sm text-gray-500 underline hover:text-red-600 transition-colors"
        >
          Cancel Analysis
        </button>
      )}
    </div>
  );
}
