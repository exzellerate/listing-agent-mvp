import { useState } from 'react';
import Layout from '../components/Layout';
import { MessageSquare, Bug, Lightbulb, Send, CheckCircle } from 'lucide-react';

type FeedbackType = 'feature' | 'bug' | 'other';

interface FeedbackForm {
  type: FeedbackType;
  subject: string;
  description: string;
  email: string;
}

export default function FeedbackPage() {
  const [formData, setFormData] = useState<FeedbackForm>({
    type: 'feature',
    subject: '',
    description: '',
    email: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      setSubmitted(true);
      setFormData({
        type: 'feature',
        subject: '',
        description: '',
        email: '',
      });

      // Reset success message after 5 seconds
      setTimeout(() => setSubmitted(false), 5000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };


  return (
    <Layout
      title="Feedback"
      subtitle="Help us improve by sharing your ideas and reporting issues"
    >
      <div className="max-w-3xl mx-auto">
        {/* Success Message */}
        {submitted && (
          <div className="mb-6 bg-green-50 border-2 border-green-200 rounded-xl p-4 flex items-center gap-3 animate-fadeIn">
            <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
            <div>
              <h3 className="font-bold text-green-900">Thank you for your feedback!</h3>
              <p className="text-sm text-green-700">We've received your submission and will review it soon.</p>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 bg-red-50 border-2 border-red-200 rounded-xl p-4">
            <h3 className="font-bold text-red-900 mb-1">Error</h3>
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {/* Feedback Form */}
        <div className="bg-white rounded-2xl border-2 border-gray-200 p-8 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Feedback Type */}
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-3">
                What would you like to share?
              </label>
              <div className="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, type: 'feature' })}
                  className={`
                    flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all
                    ${formData.type === 'feature'
                      ? 'border-purple-500 bg-purple-50 shadow-md'
                      : 'border-gray-200 bg-white hover:border-purple-300'
                    }
                  `}
                >
                  <Lightbulb className={`w-6 h-6 ${formData.type === 'feature' ? 'text-purple-600' : 'text-gray-400'}`} />
                  <span className={`text-sm font-semibold ${formData.type === 'feature' ? 'text-purple-900' : 'text-gray-600'}`}>
                    Feature Request
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, type: 'bug' })}
                  className={`
                    flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all
                    ${formData.type === 'bug'
                      ? 'border-red-500 bg-red-50 shadow-md'
                      : 'border-gray-200 bg-white hover:border-red-300'
                    }
                  `}
                >
                  <Bug className={`w-6 h-6 ${formData.type === 'bug' ? 'text-red-600' : 'text-gray-400'}`} />
                  <span className={`text-sm font-semibold ${formData.type === 'bug' ? 'text-red-900' : 'text-gray-600'}`}>
                    Bug Report
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, type: 'other' })}
                  className={`
                    flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all
                    ${formData.type === 'other'
                      ? 'border-blue-500 bg-blue-50 shadow-md'
                      : 'border-gray-200 bg-white hover:border-blue-300'
                    }
                  `}
                >
                  <MessageSquare className={`w-6 h-6 ${formData.type === 'other' ? 'text-blue-600' : 'text-gray-400'}`} />
                  <span className={`text-sm font-semibold ${formData.type === 'other' ? 'text-blue-900' : 'text-gray-600'}`}>
                    Other
                  </span>
                </button>
              </div>
            </div>

            {/* Subject */}
            <div>
              <label htmlFor="subject" className="block text-sm font-bold text-gray-900 mb-2">
                Subject
              </label>
              <input
                id="subject"
                type="text"
                required
                value={formData.subject}
                onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                placeholder="Brief summary of your feedback"
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-black focus:border-transparent transition-all"
              />
            </div>

            {/* Description */}
            <div>
              <label htmlFor="description" className="block text-sm font-bold text-gray-900 mb-2">
                Description
              </label>
              <textarea
                id="description"
                required
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={6}
                placeholder={
                  formData.type === 'feature'
                    ? 'Describe the feature you\'d like to see and how it would help you...'
                    : formData.type === 'bug'
                    ? 'Describe the bug, steps to reproduce, and what you expected to happen...'
                    : 'Tell us what\'s on your mind...'
                }
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-black focus:border-transparent transition-all resize-none"
              />
              <p className="mt-2 text-xs text-gray-500">
                Please be as detailed as possible to help us understand your feedback.
              </p>
            </div>

            {/* Email */}
            <div>
              <label htmlFor="email" className="block text-sm font-bold text-gray-900 mb-2">
                Your Email (Optional)
              </label>
              <input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="your.email@example.com"
                className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-black focus:border-transparent transition-all"
              />
              <p className="mt-2 text-xs text-gray-500">
                We'll only use this to follow up on your feedback if needed.
              </p>
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <button
                type="submit"
                disabled={submitting || !formData.subject || !formData.description}
                className={`
                  w-full flex items-center justify-center gap-2 px-6 py-4 rounded-xl font-bold text-white text-lg transition-all duration-300 transform
                  ${submitting || !formData.subject || !formData.description
                    ? 'bg-gray-300 cursor-not-allowed'
                    : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 hover:scale-105 shadow-lg hover:shadow-xl'
                  }
                `}
              >
                {submitting ? (
                  <>
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="w-5 h-5" />
                    Send Feedback
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Info Box */}
        <div className="mt-6 bg-blue-50 border-2 border-blue-200 rounded-xl p-6">
          <h3 className="font-bold text-blue-900 mb-2 flex items-center gap-2">
            <MessageSquare className="w-5 h-5" />
            Your feedback matters
          </h3>
          <p className="text-sm text-blue-800">
            We read every piece of feedback and use it to improve our product. Whether it's a feature idea, bug report, or general comment,
            we appreciate you taking the time to help us build a better tool.
          </p>
        </div>
      </div>
    </Layout>
  );
}
