import { Outlet } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from './lib/queryClient';

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-slate-900 text-slate-50">
        <div className="max-w-7xl mx-auto">
          <Outlet />
        </div>
      </div>
    </QueryClientProvider>
  );
}
