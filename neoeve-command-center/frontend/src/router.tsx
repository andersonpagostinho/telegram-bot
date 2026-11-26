import { createBrowserRouter } from 'react-router-dom';
import App from './App';
import Overview from './pages/Overview';
import AgentMap from './pages/AgentMap';
import ActivityStream from './pages/ActivityStream';
import Login from './pages/Login';
import NotFound from './pages/NotFound';
import ProtectedRoute from './components/ProtectedRoute';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: <App />,
    children: [
      { index: true, element: <ProtectedRoute element={<Overview />} /> },
      { path: 'agents', element: <ProtectedRoute element={<AgentMap />} /> },
      { path: 'activity', element: <ProtectedRoute element={<ActivityStream />} /> },
    ],
    errorElement: <NotFound />,
  },
  {
    path: '*',
    element: <NotFound />,
  },
]);
