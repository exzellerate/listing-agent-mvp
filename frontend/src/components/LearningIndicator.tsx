interface LearningIndicatorProps {
  verificationNotes?: string | null;
  confidenceScore: number;
}

export default function LearningIndicator({
  verificationNotes,
  confidenceScore,
}: LearningIndicatorProps) {
  // Check if this result came from learned data
  const isLearned = verificationNotes && verificationNotes.toLowerCase().includes('learned');
  const isHybrid = verificationNotes && verificationNotes.toLowerCase().includes('hybrid');

  if (!isLearned && !isHybrid) {
    return null;
  }

  return (
    <div
      className={`
        rounded-xl p-4 border-2 mb-6
        ${
          isLearned
            ? 'bg-gradient-to-r from-green-50 to-emerald-50 border-green-300'
            : 'bg-gradient-to-r from-blue-50 to-cyan-50 border-blue-300'
        }
      `}
    >
      <div className="flex items-start gap-3">
        <div className={`
          flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-2xl
          ${isLearned ? 'bg-green-100' : 'bg-blue-100'}
        `}>
          {isLearned ? '🎓' : '🔍'}
        </div>
        <div className="flex-1">
          <h4 className={`font-bold text-sm mb-1 ${isLearned ? 'text-green-900' : 'text-blue-900'}`}>
            {isLearned ? '✨ Instant Result (API Call Saved!)' : '🔄 Hybrid Mode (Verified with AI)'}
          </h4>
          <p className={`text-sm ${isLearned ? 'text-green-700' : 'text-blue-700'}`}>
            {isLearned
              ? `Used learned data from previous analyses (Confidence: ${confidenceScore}%). No AI API call needed!`
              : `Matched learned product but verified with AI for accuracy (Confidence: ${confidenceScore}%).`}
          </p>
          {verificationNotes && (
            <p className="text-xs text-gray-600 mt-2 italic">
              {verificationNotes}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
