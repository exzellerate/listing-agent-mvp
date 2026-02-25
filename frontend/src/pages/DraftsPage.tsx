import { useState, useEffect } from 'react';
import { DraftListingSummary, Platform } from '../types';
import { listDrafts, deleteDraft } from '../services/api';
import Layout from '../components/Layout';
import { Check, MoreVertical, AlertCircle, ImageIcon } from 'lucide-react';

export default function DraftsPage() {
  const [drafts, setDrafts] = useState<DraftListingSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterPlatform, setFilterPlatform] = useState<Platform | 'all'>('all');
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [openMenuId, setOpenMenuId] = useState<number | null>(null);

  useEffect(() => {
    loadDrafts();
  }, [filterPlatform]);

  const loadDrafts = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await listDrafts(filterPlatform === 'all' ? undefined : filterPlatform);
      setDrafts(data);
    } catch (err) {
      console.error('Failed to load drafts:', err);
      setError('Failed to load drafts. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (draftId: number) => {
    if (!confirm('Are you sure you want to delete this draft?')) {
      return;
    }

    try {
      setDeletingId(draftId);
      await deleteDraft(draftId);
      setDrafts(drafts.filter(d => d.id !== draftId));
      setOpenMenuId(null);
    } catch (err) {
      console.error('Failed to delete draft:', err);
      alert('Failed to delete draft. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  const getConditionBadge = (condition: string | null) => {
    if (!condition) return null;
    const normalized = condition.toLowerCase();
    let colorClass = 'bg-gray-100 text-gray-700';
    if (normalized.includes('new') && !normalized.includes('like') && !normalized.includes('used')) {
      colorClass = 'bg-green-100 text-green-800';
    } else if (normalized.includes('like new') || normalized.includes('excellent')) {
      colorClass = 'bg-blue-100 text-blue-800';
    } else if (normalized.includes('good') || normalized.includes('very good')) {
      colorClass = 'bg-yellow-100 text-yellow-800';
    } else if (normalized.includes('used') || normalized.includes('acceptable')) {
      colorClass = 'bg-gray-100 text-gray-700';
    }
    return (
      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${colorClass}`}>
        {condition}
      </span>
    );
  };

  const isDraftReady = (draft: DraftListingSummary) => {
    return !!(draft.title && draft.price && draft.condition && draft.image_paths && draft.image_paths.length > 0);
  };

  const readyCount = drafts.filter(isDraftReady).length;

  const getMissingFields = (draft: DraftListingSummary): string[] => {
    const missing: string[] = [];
    if (!draft.price) missing.push('Price');
    if (!draft.condition) missing.push('Condition');
    if (!draft.image_paths || draft.image_paths.length === 0) missing.push('Images');
    return missing;
  };

  return (
    <Layout
      title="Drafts"
      subtitle={`${readyCount} of ${drafts.length} ready to list`}
    >
      <div className="space-y-6">
        {/* Header with dropdown */}
        <div className="flex justify-end">
          <select
            value={filterPlatform}
            onChange={(e) => setFilterPlatform(e.target.value as Platform | 'all')}
            className="px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-black"
          >
            <option value="all">All Drafts</option>
            <option value="ebay">eBay Only</option>
            <option value="amazon">Amazon Only</option>
            <option value="walmart">Walmart Only</option>
          </select>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
            <p className="mt-4 text-gray-600">Loading drafts...</p>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <p className="text-red-800 font-medium">{error}</p>
            <button
              onClick={loadDrafts}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg font-medium transition-colors"
            >
              Retry
            </button>
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && drafts.length === 0 && (
          <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
            <svg
              className="mx-auto h-24 w-24 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className="mt-4 text-xl font-bold text-gray-900">No drafts yet</h3>
            <p className="mt-2 text-gray-600">
              Analyze a product image and save it as a draft to see it here.
            </p>
            <a
              href="/"
              className="mt-6 inline-block px-6 py-3 bg-black text-white rounded-lg font-medium hover:bg-gray-800 transition-colors"
            >
              Analyze Product
            </a>
          </div>
        )}

        {/* Drafts Table */}
        {!loading && !error && drafts.length > 0 && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-x-auto pb-24">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-20">
                    Image
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider min-w-[250px]">
                    Product
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-28">
                    Price
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-28">
                    Condition
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32 hidden lg:table-cell">
                    Platform
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-24 hidden md:table-cell">
                    Status
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-44">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {drafts.map((draft) => {
                  const missing = getMissingFields(draft);
                  const ready = isDraftReady(draft);
                  const imageCount = draft.image_paths?.length || 0;

                  return (
                    <tr key={draft.id} className="hover:bg-gray-50">
                      {/* Image with count overlay */}
                      <td className="px-4 py-4 whitespace-nowrap">
                        {imageCount > 0 ? (
                          <div className="relative w-12 h-12">
                            <img
                              src={draft.image_paths![0]}
                              alt={draft.title || 'Product'}
                              className="w-12 h-12 rounded-md object-cover"
                            />
                            {imageCount > 1 && (
                              <span className="absolute -top-1 -right-1 bg-gray-800 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                                {imageCount}
                              </span>
                            )}
                          </div>
                        ) : (
                          <div className="w-12 h-12 bg-gray-100 rounded-md flex items-center justify-center flex-shrink-0">
                            <ImageIcon className="w-5 h-5 text-gray-400" />
                          </div>
                        )}
                      </td>

                      {/* Product: title + category */}
                      <td className="px-4 py-4">
                        <div className="text-sm font-medium text-gray-900 truncate max-w-[250px] lg:max-w-[400px]">
                          {draft.title || 'Untitled Draft'}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          {draft.category && (
                            <span className="text-xs text-gray-500 truncate max-w-[200px]">
                              {draft.category}
                            </span>
                          )}
                          {!draft.category && draft.product_name && (
                            <span className="text-xs text-gray-500 truncate max-w-[200px]">
                              {draft.product_name}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Price */}
                      <td className="px-4 py-4 whitespace-nowrap">
                        {draft.price ? (
                          <div className="text-sm font-medium text-gray-900">
                            ${draft.price.toFixed(2)}
                          </div>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-800">
                            Set Price
                          </span>
                        )}
                      </td>

                      {/* Condition */}
                      <td className="px-4 py-4 whitespace-nowrap">
                        {draft.condition ? (
                          getConditionBadge(draft.condition)
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>

                      {/* Platform */}
                      <td className="px-4 py-4 whitespace-nowrap hidden lg:table-cell">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                          {draft.platform.charAt(0).toUpperCase() + draft.platform.slice(1)}
                        </span>
                      </td>

                      {/* Readiness Status */}
                      <td className="px-4 py-4 whitespace-nowrap hidden md:table-cell">
                        {ready ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-800">
                            <Check className="w-3 h-3" />
                            Ready
                          </span>
                        ) : (
                          <span
                            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-orange-100 text-orange-700 cursor-help"
                            title={`Missing: ${missing.join(', ')}`}
                          >
                            <AlertCircle className="w-3 h-3" />
                            {missing.length} missing
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium relative">
                        <div className="flex items-center justify-end gap-2">
                          <a
                            href={`/upload?draftId=${draft.id}`}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-black text-white rounded-md text-sm font-medium hover:bg-gray-800 transition-colors whitespace-nowrap"
                          >
                            <Check className="w-4 h-4" />
                            List
                          </a>
                          <div className="relative">
                            <button
                              onClick={() => setOpenMenuId(openMenuId === draft.id ? null : draft.id)}
                              className="p-1.5 hover:bg-gray-100 rounded-md transition-colors"
                              aria-label="More options"
                            >
                              <MoreVertical className="w-5 h-5 text-gray-600" />
                            </button>
                            {openMenuId === draft.id && (
                              <>
                                <div
                                  className="fixed inset-0 z-10"
                                  onClick={() => setOpenMenuId(null)}
                                />
                                <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-md shadow-lg border border-gray-200 z-20">
                                  <div className="py-1">
                                    <a
                                      href={`/upload?draftId=${draft.id}`}
                                      className="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 text-left"
                                    >
                                      Edit Draft
                                    </a>
                                    <button
                                      onClick={() => handleDelete(draft.id)}
                                      disabled={deletingId === draft.id}
                                      className="flex items-center w-full text-left px-4 py-2 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
                                    >
                                      {deletingId === draft.id ? 'Deleting...' : 'Delete Draft'}
                                    </button>
                                  </div>
                                </div>
                              </>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}
