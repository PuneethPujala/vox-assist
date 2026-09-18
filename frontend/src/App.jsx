import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom';
import Navbar from './components/Navbar';
import { AuthProvider, useAuth } from './contexts/AuthContext';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Create = lazy(() => import('./pages/Create'));
const Login = lazy(() => import('./pages/Login'));
const Explore = lazy(() => import('./pages/Explore'));
const YourDesigns = lazy(() => import('./pages/YourDesigns'));
const Profile = lazy(() => import('./pages/Profile'));

const PageLoader = () => (
    <div className="min-h-[calc(100vh-80px)] flex flex-col items-center justify-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-stone-300 dark:border-stone-700 border-t-charcoal dark:border-t-stone-100 animate-spin" />
        <span className="text-xs font-mono text-stone-400 dark:text-stone-500">Loading module...</span>
    </div>
);

const PrivateRoute = () => {
    const { currentUser, loading } = useAuth();
    const location = useLocation();

    if (loading) return <PageLoader />;
    return currentUser ? <Outlet /> : <Navigate to="/login" state={{ from: location }} replace />;
};

function App() {
    return (
        <AuthProvider>
            <Router>
                <div className="min-h-screen bg-stone-50 dark:bg-stone-950 text-stone-900 dark:text-stone-100 selection:bg-stone-200 dark:selection:bg-stone-800 transition-colors duration-200">
                    <Navbar />
                    <Suspense fallback={<PageLoader />}>
                        <Routes>
                            <Route path="/" element={<Navigate to="/dashboard" replace />} />
                            <Route path="/login" element={<Login />} />
                            <Route path="/dashboard" element={<Dashboard />} />
                            <Route path="/explore" element={<Explore />} />

                            {/* Protected Routes */}
                            <Route element={<PrivateRoute />}>
                                <Route path="/create" element={<Create />} />
                                <Route path="/my-designs" element={<YourDesigns />} />
                                <Route path="/profile" element={<Profile />} />
                            </Route>
                        </Routes>
                    </Suspense>
                </div>
            </Router>
        </AuthProvider>
    );
}

export default App;
