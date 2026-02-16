import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Create from './pages/Create';
import Login from './pages/Login';
import Explore from './pages/Explore';
import YourDesigns from './pages/YourDesigns';
import { AuthProvider, useAuth } from './contexts/AuthContext';

// Placeholder Pages
import Profile from './pages/Profile';

const PrivateRoute = () => {
    const { currentUser, loading } = useAuth();
    if (loading) return <div className="pt-24 text-center">Loading...</div>;
    return currentUser ? <Outlet /> : <Navigate to="/login" />;
};

function App() {
    return (
        <AuthProvider>
            <Router>
                <div className="min-h-screen bg-cream text-charcoal selection:bg-stone-200">
                    <Navbar />
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
                </div>
            </Router>
        </AuthProvider>
    );
}

export default App;
