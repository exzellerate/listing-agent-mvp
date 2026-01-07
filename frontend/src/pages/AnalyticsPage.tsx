import Layout from '../components/Layout';

const AnalyticsPage = () => {
  return (
    <Layout
      title="Analytics"
      subtitle="Track your listing performance and insights"
    >
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-gray-500 text-lg">Analytics - Coming Soon</p>
          <p className="text-gray-400 text-sm mt-2">
            This section will show performance metrics and insights
          </p>
        </div>
      </div>
    </Layout>
  );
};

export default AnalyticsPage;
