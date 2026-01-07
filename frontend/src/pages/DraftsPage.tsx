import { useState, useEffect } from 'react';
import { DraftListingSummary, Platform } from '../types';
import { listDrafts, deleteDraft } from '../services/api';
import Layout from '../components/Layout';
import { Check, MoreVertical } from 'lucide-react';

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

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: '2-digit',
      day: '2-digit',
      year: 'numeric',
    }).format(date);
  };

  const getPlatformBadgeClass = (platform: Platform) => {
    switch (platform) {
      case 'ebay':
        return 'bg-gray-100 text-gray-800';
      case 'amazon':
        return 'bg-gray-100 text-gray-800';
      case 'walmart':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getPlatformLabel = (platform: Platform) => {
    return platform.charAt(0).toUpperCase() + platform.slice(1);
  };

  // Count drafts ready for listing (has price and title)
  const readyCount = drafts.filter(d => d.price && d.title).length;

  return (
    <Layout
      title="Drafts"
      subtitle={`${readyCount} of ${drafts.length} drafts ready for listing`}
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
                    Title
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-28">
                    Price
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32">
                    Platform
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-32 hidden md:table-cell">
                    Updated
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider w-44">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {drafts.map((draft) => (
                  <tr key={draft.id} className="hover:bg-gray-50">
                    <td className="px-4 py-4 whitespace-nowrap">
                      {draft.image_paths && draft.image_paths.length > 0 ? (
                        <img
                          src={draft.image_paths[0]}
                          alt={draft.title || 'Product'}
                          className="w-12 h-12 rounded-md object-cover"
                        />
                      ) : (
                        <div className="w-12 h-12 bg-gray-100 rounded-md flex items-center justify-center flex-shrink-0">
                          <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                          </svg>
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <div className="text-sm font-medium text-gray-900 truncate max-w-[250px] lg:max-w-[400px]">
                        {draft.title || 'Untitled Draft'}
                      </div>
                      {draft.product_name && (
                        <div className="text-xs text-gray-500 truncate max-w-[250px] lg:max-w-[400px]">
                          {draft.product_name}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      {draft.price ? (
                        <div className="text-sm font-medium text-gray-900">
                          ${draft.price.toFixed(2)}
                        </div>
                      ) : (
                        <div className="text-sm text-gray-400">—</div>
                      )}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-medium ${getPlatformBadgeClass(draft.platform)}`}>
                        {getPlatformLabel(draft.platform)}
                      </span>
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500 hidden md:table-cell">
                      {formatDate(draft.updated_at)}
                    </td>
                    <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium relative">
                      <div className="flex items-center justify-end gap-2">
                        <a
                          href={`/?draftId=${draft.id}`}
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
                                    href={`/?draftId=${draft.id}`}
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
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  );
}
