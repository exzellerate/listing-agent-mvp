import { useState } from 'react';
import { UserAction } from '../types';

interface FeedbackButtonsProps {
  analysisId?: number;
  onFeedback: (action: UserAction) => void;
  onRequestCorrection: (action: 'edited' | 'rejected') => void;
  disabled?: boolean;
}

export default function FeedbackButtons({
  analysisId,
  onFeedback,
  onRequestCorrection,
  disabled = false,
}: FeedbackButtonsProps) {
  const [selectedAction, setSelectedAction] = useState<UserAction | null>(null);

  if (!analysisId) {
    return null;
  }

  const handleAction = (action: UserAction) => {
    // For edited and rejected, open the correction modal instead
    if (action === 'edited' || action === 'rejected') {
      onRequestCorrection(action);
      return;
    }

    // For accepted, send feedback directly
    setSelectedAction(action);
    onFeedback(action);
  };

  const isSelected = (action: UserAction) => selectedAction === action;

  return (
    <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl p-6 border-2 border-purple-200">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Help Us Learn!</h3>
          <p className="text-sm text-gray-600">
            Your feedback improves future analyses and reduces costs
          </p>
        </div>
        {selectedAction && (
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-semibold">
            ✓ Feedback Sent
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <button
          onClick={() => handleAction('accepted')}
          disabled={disabled || selectedAction !== null}
          className={`
            flex items-center justify-center gap-2 px-6 py-4 rounded-lg font-semibold transition-all duration-200
            ${
              isSelected('accepted')
                ? 'bg-green-600 text-white shadow-lg'
                : 'bg-white hover:bg-green-50 text-gray-700 border-2 border-gray-300 hover:border-green-400 shadow-md'
            }
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        >
          <span className="text-2xl">👍</span>
          <span>Accept</span>
        </button>

        <button
          onClick={() => handleAction('edited')}
          disabled={disabled || selectedAction !== null}
          className={`
            flex items-center justify-center gap-2 px-6 py-4 rounded-lg font-semibold transition-all duration-200
            ${
              isSelected('edited')
                ? 'bg-blue-600 text-white shadow-lg'
                : 'bg-white hover:bg-blue-50 text-gray-700 border-2 border-gray-300 hover:border-blue-400 shadow-md'
            }
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        >
          <span className="text-2xl">✏️</span>
          <span>Edit & Accept</span>
        </button>

        <button
          onClick={() => handleAction('rejected')}
          disabled={disabled || selectedAction !== null}
          className={`
            flex items-center justify-center gap-2 px-6 py-4 rounded-lg font-semibold transition-all duration-200
            ${
              isSelected('rejected')
                ? 'bg-red-600 text-white shadow-lg'
                : 'bg-white hover:bg-red-50 text-gray-700 border-2 border-gray-300 hover:border-red-400 shadow-md'
            }
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
        >
          <span className="text-2xl">❌</span>
          <span>Reject</span>
        </button>
      </div>

      <p className="text-xs text-gray-500 mt-4 text-center">
        Analysis ID: {analysisId} • Your feedback trains the AI to give better results over time
      </p>
    </div>
  );
}
