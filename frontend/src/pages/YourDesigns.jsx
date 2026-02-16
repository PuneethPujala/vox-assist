import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { motion } from 'framer-motion';
import { Loader2, Trash2, Edit2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const YourDesigns = () => {
    const { currentUser } = useAuth();
    const [designs, setDesigns] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (currentUser) {
            fetchMyDesigns();
        }
    }, [currentUser]);

    const fetchMyDesigns = async () => {
        try {
            const token = await currentUser.getIdToken();
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/v1/my-designs`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setDesigns(response.data);
        } catch (error) {
            console.error("Error fetching designs:", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="pt-24 flex justify-center"><Loader2 className="animate-spin" /></div>;

    return (
        <div className="pt-24 px-6 md:px-12 min-h-screen bg-cream">
            <div className="flex justify-between items-center mb-8">
                <h1 className="text-3xl font-light text-charcoal">Your Portfolio</h1>
                <div className="text-sm text-stone-500">{designs.length} Designs</div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {designs.map((design, idx) => (
                    <motion.div
                        key={design._id || idx}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow border border-stone-100 relative group"
                    >
                        {/* Thumbnail Placeholder */}
                        <div className="h-48 bg-stone-100 flex items-center justify-center relative overflow-hidden">
                            <span className="text-stone-400 text-sm font-medium tracking-wide">3D Model</span>

                            {/* Overlay Actions */}
                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center space-x-3">
                                {design.model_url && (
                                    <a
                                        href={`${import.meta.env.VITE_API_URL}${design.model_url}`}
                                        className="bg-white text-charcoal px-4 py-2 rounded-full text-sm font-medium hover:bg-stone-50 transition-colors"
                                        download
                                    >
                                        Download .PLY
                                    </a>
                                )}
                            </div>

                            {/* Delete Button (Top Right) */}
                            <button className="absolute top-3 right-3 p-2 bg-white/80 hover:bg-red-50 text-stone-400 hover:text-red-500 rounded-full opacity-0 group-hover:opacity-100 transition-all">
                                <Trash2 size={16} />
                            </button>
                        </div>

                        <div className="p-6">
                            <p className="text-stone-800 text-sm font-medium line-clamp-2 mb-4 h-10 leading-relaxed">
                                "{design.prompt}"
                            </p>

                            <div className="flex justify-between items-center text-xs text-stone-500 border-t border-stone-100 pt-4">
                                <span className="flex items-center gap-1">
                                    {design.created_at ? formatDistanceToNow(new Date(design.created_at), { addSuffix: true }) : 'Recently'}
                                </span>

                                <div className="flex items-center gap-2">
                                    {design.spec_data && (
                                        <span className="bg-stone-50 px-2 py-1 rounded text-stone-600 font-mono">
                                            {design.spec_data.rooms.length} Rooms
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </motion.div>
                ))}

                {designs.length === 0 && (
                    <div className="col-span-full py-20 text-center border-2 border-dashed border-stone-100 rounded-2xl">
                        <div className="text-stone-300 mb-4 text-4xl">✨</div>
                        <p className="text-stone-500 font-medium mb-2">Your portfolio is empty</p>
                        <p className="text-sm text-stone-400 mb-6">Create your first architectural design today.</p>
                        <a href="/create" className="inline-block bg-charcoal text-cream px-6 py-3 rounded-xl hover:bg-stone-800 transition-colors">
                            Start Creating
                        </a>
                    </div>
                )}
            </div>
        </div>
    );
};

export default YourDesigns;
