import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';
import AppShell from './components/layout/AppShell';
import { useAuthPersist } from './hooks/useAuthPersist';
// import { useTokenRefresh } from './hooks/useTokenRefresh';

export default function App() {
  // Restore auth from localStorage on mount
  useAuthPersist();

  // TODO: Re-enable token refresh after fixing cookie issue
  // Automatic token refresh every 14 minutes
  // useTokenRefresh();

  return (
    <QueryClientProvider client={queryClient}>
      <AppShell />
    </QueryClientProvider>
  );
}
