import { Outlet } from 'react-router-dom';

export default function App() {
  return (
    <div className="min-h-screen bg-slate-900 text-slate-50">
      <div className="max-w-7xl mx-auto">
        <Outlet />
      </div>
    </div>
  );
}
