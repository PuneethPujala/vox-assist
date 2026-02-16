import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { motion } from 'framer-motion';
import { User, Mail, Calendar, Box, Activity, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';

const Profile = () => {
    const { currentUser } = useAuth();
    const [designs, setDesigns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [stats, setStats] = useState({
        totalDesigns: 0,
        avgScore: 0,
        totalRooms: 0
    });

    useEffect(() => {
        if (currentUser) {
            fetchUserData();
        }
    }, [currentUser]);

    const fetchUserData = async () => {
        try {
            const token = await currentUser.getIdToken();
            const designsResponse = await axios.get(`${import.meta.env.VITE_API_URL}/api/v1/my-designs`, {
                headers: { Authorization: `Bearer ${token}` }
            });

            const designData = designsResponse.data;
            setDesigns(designData);

            // Calculate Stats
            const totalDesigns = designData.length;
            const totalScore = designData.reduce((acc, curr) => acc + (curr.score || 0), 0);
            const avgScore = totalDesigns > 0 ? Math.round(totalScore / totalDesigns) : 0;
            const totalRooms = designData.reduce((acc, curr) => acc + (curr.spec_data?.rooms?.length || 0), 0);

            setStats({
                totalDesigns,
                avgScore,
                totalRooms
            });

        } catch (error) {
            console.error("Error fetching profile data:", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return (
        <div className="pt-24 flex justify-center items-center min-h-screen bg-cream">
            <div className="animate-pulse text-stone-400">Loading Profile...</div>
        </div>
    );

    return (
        <div className="pt-24 px-6 md:px-12 min-h-screen bg-cream">
            <div className="max-w-6xl mx-auto">
                {/* Header Section */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-white rounded-2xl p-8 shadow-sm border border-stone-100 flex flex-col md:flex-row items-center md:items-start gap-8"
                >
                    {/* Avatar */}
                    <div className="relative">
                        <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-white shadow-lg bg-stone-200">
                            {currentUser.photoURL ? (
                                <img src={currentUser.photoURL} alt="Profile" className="w-full h-full object-cover" />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center bg-charcoal text-white text-4xl font-light">
                                    {currentUser.email?.[0].toUpperCase()}
                                </div>
                            )}
                        </div>
                        <div className="absolute bottom-2 right-2 w-6 h-6 bg-green-500 border-2 border-white rounded-full"></div>
                    </div>

                    {/* User Info */}
                    <div className="flex-1 text-center md:text-left">
                        <h1 className="text-3xl font-light text-charcoal mb-2">
                            {currentUser.displayName || "Architect"}
                        </h1>
                        <div className="flex flex-col md:flex-row gap-4 text-stone-500 text-sm md:items-center">
                            <span className="flex items-center gap-2 justify-center md:justify-start">
                                <Mail size={16} /> {currentUser.email}
                            </span>
                            <span className="hidden md:inline text-stone-300">•</span>
                            <span className="flex items-center gap-2 justify-center md:justify-start">
                                <Calendar size={16} /> Member since {currentUser.metadata.creationTime ? new Date(currentUser.metadata.creationTime).toLocaleDateString() : 'Recently'}
                            </span>
                        </div>
                    </div>

                    {/* Quick Action */}
                    <div>
                        <Link
                            to="/create"
                            className="bg-charcoal text-cream px-6 py-3 rounded-xl hover:bg-stone-800 transition-colors inline-block"
                        >
                            New Project
                        </Link>
                    </div>
                </motion.div>

                {/* Stats Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 my-8">
                    <StatCard icon={<Box />} label="Total Designs" value={stats.totalDesigns} delay={0.1} />
                    <StatCard icon={<Activity />} label="Avg. Efficiency" value={`${stats.avgScore}%`} delay={0.2} />
                    <StatCard icon={<Box />} label="Total Rooms Planned" value={stats.totalRooms} delay={0.3} />
                </div>

                {/* Recent Activity */}
                <div className="mb-12">
                    <div className="flex justify-between items-center mb-6">
                        <h2 className="text-2xl font-light text-charcoal">Recent Activity</h2>
                        <Link to="/my-designs" className="text-stone-500 hover:text-charcoal flex items-center gap-1 text-sm">
                            View All <ArrowRight size={16} />
                        </Link>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {designs.slice(0, 3).map((design, idx) => (
                            <motion.div
                                key={design._id || idx}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.1 * idx }}
                                className="bg-white rounded-xl shadow-sm border border-stone-100 p-4 hover:shadow-md transition-all group"
                            >
                                <div className="flex justify-between items-start mb-3">
                                    <div className="bg-stone-100 text-stone-600 text-xs px-2 py-1 rounded">
                                        {design.spec_data?.rooms?.length || "?"} Rooms
                                    </div>
                                    <span className="text-xs text-stone-400">
                                        {formatDistanceToNow(new Date(design.created_at || Date.now()), { addSuffix: true })}
                                    </span>
                                </div>

                                <h3 className="text-stone-800 font-medium mb-1 line-clamp-1">
                                    {design.prompt || "Untitled Project"}
                                </h3>

                                <div className="w-full bg-stone-100 rounded-lg h-32 mb-4 overflow-hidden relative">
                                    {/* Simple Placeholder or Real Thumbnail if available */}
                                    <div className="w-full h-full flex items-center justify-center text-stone-300">
                                        Design Preview
                                    </div>
                                </div>

                                <div className="flex justify-between items-center border-t border-stone-100 pt-3">
                                    <div className="flex gap-2">
                                        <div className="text-xs text-stone-500">
                                            Score: <span className="text-green-600 font-bold">{design.score}</span>
                                        </div>
                                    </div>
                                    <Link to="/my-designs" className="p-2 bg-stone-50 rounded-full hover:bg-stone-200 transition-colors">
                                        <ArrowRight size={14} className="text-stone-600" />
                                    </Link>
                                </div>
                            </motion.div>
                        ))}

                        {designs.length === 0 && (
                            <div className="col-span-full text-center py-12 bg-stone-50 rounded-xl border-2 border-dashed border-stone-200">
                                <p className="text-stone-500 mb-2">No designs yet.</p>
                                <Link to="/create" className="text-charcoal underline hover:text-stone-600">Start your first project</Link>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

const StatCard = ({ icon, label, value, delay }) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay }}
        className="bg-white p-6 rounded-xl shadow-sm border border-stone-100 flex items-center gap-4"
    >
        <div className="p-3 bg-stone-50 text-charcoal rounded-lg">
            {React.cloneElement(icon, { size: 24 })}
        </div>
        <div>
            <div className="text-2xl font-light text-charcoal">{value}</div>
            <div className="text-xs text-stone-500 uppercase tracking-wide">{label}</div>
        </div>
    </motion.div>
);

export default Profile;
