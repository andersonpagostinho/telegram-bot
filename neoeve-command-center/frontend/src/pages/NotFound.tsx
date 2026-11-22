import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900">
      <div className="text-center">
        <h1 className="text-4xl font-bold text-slate-50 mb-4">404</h1>
        <p className="text-slate-400 mb-8">Page not found</p>
        <Link to="/" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white">
          Back to Home
        </Link>
      </div>
    </div>
  );
}
