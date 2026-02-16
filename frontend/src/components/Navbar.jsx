import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';
import { auth } from '../firebase';

const NavLink = ({ to, active, children }) => (
    <Link to={to} className="relative py-1 group">
        <span className={`text-sm font-medium transition-colors ${active ? 'text-charcoal' : 'text-stone-500 group-hover:text-charcoal'}`}>
            {children}
        </span>
        {active && (
            <motion.div
                layoutId="underline"
                className="absolute bottom-0 left-0 right-0 h-0.5 bg-charcoal"
            />
        )}
    </Link>
);

const Navbar = () => {
    const location = useLocation();
    const { currentUser } = useAuth();

    const isActive = (path) => location.pathname === path;

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 backdrop-blur-md border-b border-stone-200 h-16">
            <div className="max-w-7xl mx-auto px-6 h-full flex items-center justify-between">
                <Link to="/" className="text-2xl font-light tracking-tighter text-charcoal">
                    VOX<span className="font-semibold">ASSIST</span>
                </Link>

                <div className="hidden md:flex items-center space-x-8">
                    <NavLink to="/dashboard" active={isActive('/dashboard')}>Dashboard</NavLink>
                    <NavLink to="/explore" active={isActive('/explore')}>Explore</NavLink>
                    {currentUser && <NavLink to="/create" active={isActive('/create')}>Create</NavLink>}
                    {currentUser && <NavLink to="/my-designs" active={isActive('/my-designs')}>Portfolio</NavLink>}
                </div>

                <div className="flex items-center space-x-4">
                    {currentUser ? (
                        <div className="flex items-center space-x-4">
                            <span className="text-sm text-stone-500 hidden sm:inline">{currentUser.email}</span>
                            <button
                                onClick={() => auth.signOut()}
                                className="px-4 py-2 text-sm font-medium text-stone-600 hover:text-charcoal transition-colors"
                            >
                                Sign Out
                            </button>
                            <Link to="/profile" className="w-8 h-8 rounded-full bg-charcoal text-cream flex items-center justify-center text-xs border border-stone-200">
                                {currentUser.email ? currentUser.email[0].toUpperCase() : 'U'}
                            </Link>
                        </div>
                    ) : (
                        <Link
                            to="/login"
                            className="px-6 py-2 bg-charcoal text-cream rounded-full text-sm font-medium hover:bg-stone-800 transition-colors"
                        >
                            Sign In
                        </Link>
                    )}
                </div>
            </div>
        </nav>
    );
};

export default Navbar;
