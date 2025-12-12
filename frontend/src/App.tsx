import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { LoginView } from './views/LoginView';
import { DashboardView } from './views/DashboardView';
import { LectureDetailView } from './views/LectureDetailView';

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem('echo_token');
  return token ? children : <Navigate to="/login" replace />;
}

function RootRedirect() {
  const token = localStorage.getItem('echo_token');
  return <Navigate to={token ? '/dashboard' : '/login'} replace />;
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route path="/login" element={<LoginView />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardView />
            </ProtectedRoute>
          }
        />
        <Route
          path="/lectures/:id"
          element={
            <ProtectedRoute>
              <LectureDetailView />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
