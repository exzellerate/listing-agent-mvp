import { ReactNode } from 'react';
import Sidebar from './Sidebar';

interface LayoutProps {
  children: ReactNode;
  title?: string;
  subtitle?: string;
}

const Layout = ({ children, title, subtitle }: LayoutProps) => {
  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Page Header */}
        {(title || subtitle) && (
          <div className="px-12 py-8 bg-white border-b border-gray-200">
            {title && (
              <h1 className="text-3xl font-semibold text-gray-900">{title}</h1>
            )}
            {subtitle && (
              <p className="mt-2 text-base text-gray-600">{subtitle}</p>
            )}
          </div>
        )}

        {/* Scrollable Content */}
        <main className="flex-1 overflow-y-auto px-12 py-8">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
