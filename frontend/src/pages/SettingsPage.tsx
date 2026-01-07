import Layout from '../components/Layout';
import ConnectionsPage from './ConnectionsPage';

const SettingsPage = () => {
  return (
    <Layout
      title="Settings"
      subtitle="Manage your account and integrations"
    >
      <ConnectionsPage />
    </Layout>
  );
};

export default SettingsPage;
