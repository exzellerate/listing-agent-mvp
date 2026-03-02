import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, BarChart3, Settings, HelpCircle, Zap, MessageSquare, LogOut } from 'lucide-react';
import { useState, useEffect } from 'react';
import { useClerk } from '@clerk/clerk-react';
import { listDrafts } from '../services/api';

const Sidebar = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { signOut } = useClerk();
  const [draftCount, setDraftCount] = useState<number>(0);

  // Fetch draft count on mount and when location changes
  useEffect(() => {
    const fetchDraftCount = async () => {
      try {
        const drafts = await listDrafts();
        setDraftCount(drafts.length);
      } catch (error) {
        console.error('Failed to fetch draft count:', error);
      }
    };

    fetchDraftCount();
  }, [location.pathname]);

  const navigationItems = [
    {
      name: 'Upload & Analyze',
      path: '/upload',
      icon: Upload,
    },
    {
      name: 'Drafts',
      path: '/drafts',
      icon: FileText,
      badge: draftCount,
    },
    {
      name: 'Active Listings',
      path: '/listings',
      icon: CheckCircle,
    },
    {
      name: 'Analytics',
      path: '/analytics',
      icon: BarChart3,
    },
    {
      name: 'Feedback',
      path: '/feedback',
      icon: MessageSquare,
    },
    {
      name: 'Help',
      path: '/help',
      icon: HelpCircle,
    },
  ];

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="w-80 bg-white border-r border-gray-200 flex flex-col h-screen">
      {/* Logo and Brand */}
      <div className="px-6 py-6 border-b border-gray-200">
        <Link to="/" className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-green-600 rounded-lg flex items-center justify-center">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <span className="text-xl font-bold text-gray-900">exzellerate</span>
        </Link>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 px-4 py-6">
        <div className="space-y-1">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);

            return (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
                  ${active
                    ? 'bg-gray-100 text-gray-900 font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                <span className="text-sm flex-1">{item.name}</span>
                {item.badge !== undefined && item.badge > 0 && (
                  <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 bg-black text-white text-xs font-medium rounded-full">
                    {item.badge > 99 ? '99+' : item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Bottom Section */}
      <div className="px-4 py-6 border-t border-gray-200 space-y-1">
        <Link
          to="/settings"
          className={`
            flex items-center gap-3 px-4 py-3 rounded-lg transition-colors
            ${isActive('/settings')
              ? 'bg-gray-100 text-gray-900 font-medium'
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
            }
          `}
        >
          <Settings className="w-5 h-5" />
          <span className="text-sm">Settings</span>
        </Link>
        <button
          onClick={() => signOut(() => navigate('/'))}
          className="flex items-center gap-3 px-4 py-3 rounded-lg transition-colors text-gray-600 hover:bg-red-50 hover:text-red-600 w-full"
        >
          <LogOut className="w-5 h-5" />
          <span className="text-sm">Sign Out</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
