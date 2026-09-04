import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowUp, List, Target, BarChart3, Settings, HelpCircle, Zap, MessageSquare, LogOut } from 'lucide-react';
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
      icon: ArrowUp,
    },
    {
      name: 'Drafts',
      path: '/drafts',
      icon: List,
      badge: draftCount,
    },
    {
      name: 'Active Listings',
      path: '/listings',
      icon: Target,
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
    <div className="w-24 bg-white border-r border-gray-200 flex flex-col h-screen">
      {/* Logo */}
      <div className="py-6 flex justify-center border-b border-gray-200">
        <Link to="/" aria-label="exzellerate home">
          <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-green-600 rounded-2xl flex items-center justify-center">
            <Zap className="w-6 h-6 text-white" />
          </div>
        </Link>
      </div>

      {/* Navigation Items */}
      <nav className="flex-1 py-6 overflow-y-auto">
        <div className="flex flex-col items-center gap-6">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);

            return (
              <Link
                key={item.path}
                to={item.path}
                className="w-full flex flex-col items-center gap-1 px-1 group"
              >
                <div
                  className={`
                    relative flex items-center justify-center w-12 h-12 rounded-2xl transition-colors
                    ${active ? 'bg-green-100' : 'group-hover:bg-gray-100'}
                  `}
                >
                  <Icon className={`w-5 h-5 ${active ? 'text-green-700' : 'text-gray-500 group-hover:text-gray-700'}`} />
                  {item.badge !== undefined && item.badge > 0 && (
                    <span className="absolute -top-1 -right-1 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 bg-red-600 text-white text-[10px] font-bold rounded-full leading-none">
                      {item.badge > 99 ? '99+' : item.badge}
                    </span>
                  )}
                </div>
                <span
                  className={`text-[11px] text-center leading-tight ${
                    active ? 'text-green-700 font-semibold' : 'text-gray-500 group-hover:text-gray-700'
                  }`}
                >
                  {item.name}
                </span>
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Bottom Section */}
      <div className="py-6 border-t border-gray-200 flex flex-col items-center gap-3">
        <Link to="/settings" aria-label="Settings" title="Settings" className="group">
          <div
            className={`
              flex items-center justify-center w-12 h-12 rounded-2xl transition-colors
              ${isActive('/settings') ? 'bg-green-100' : 'group-hover:bg-gray-100'}
            `}
          >
            <Settings className={`w-5 h-5 ${isActive('/settings') ? 'text-green-700' : 'text-gray-500 group-hover:text-gray-700'}`} />
          </div>
        </Link>
        <button onClick={() => signOut(() => navigate('/'))} aria-label="Sign Out" title="Sign Out" className="group">
          <div className="flex items-center justify-center w-12 h-12 rounded-2xl transition-colors group-hover:bg-red-50">
            <LogOut className="w-5 h-5 text-gray-500 group-hover:text-red-600" />
          </div>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
