import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Loader2, ExternalLink } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const Explore = () => {
    const [designs, setDesigns] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDesigns();
    }, []);

    const fetchDesigns = async () => {
        try {
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/v1/designs`);
            setDesigns(response.data);
        } catch (error) {
            console.error("Error fetching designs:", error);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="pt-24 flex justify-center">
                <Loader2 className="animate-spin text-charcoal" size={32} />
            </div>
        );
    }

    return (
        <div className="pt-24 px-6 md:px-12 min-h-screen bg-cream">
            <h1 className="text-3xl font-light text-charcoal mb-8">Explore Designs</h1>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {designs.map((design, idx) => (
                    <motion.div
                        key={design._id || idx}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.1 }}
                        className="bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow border border-stone-100"
                    >
                        {/* Thumbnail Placeholder (could be a screenshot if we had one) */}
                        <div className="h-48 bg-stone-100 flex items-center justify-center relative group">
                            <span className="text-stone-400 text-sm">3D Model</span>

                            <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                {design.model_url && (
                                    <a
                                        href={`${import.meta.env.VITE_API_URL}${design.model_url}`}
                                        className="bg-white text-charcoal px-4 py-2 rounded-full text-sm font-medium hover:bg-stone-50"
                                        download
                                    >
                                        Download .PLY
                                    </a>
                                )}
                            </div>
                        </div>

                        <div className="p-6">
                            <p className="text-stone-800 text-sm font-medium line-clamp-2 mb-4">
                                "{design.prompt}"
                            </p>

                            <div className="flex justify-between items-center text-xs text-stone-500">
                                <span>
                                    {design.created_at ? formatDistanceToNow(new Date(design.created_at), { addSuffix: true }) : 'Recently'}
                                </span>

                                {design.spec_data && (
                                    <span className="bg-stone-100 px-2 py-1 rounded text-stone-600">
                                        {design.spec_data.rooms.length} Rooms
                                    </span>
                                )}
                            </div>
                        </div>
                    </motion.div>
                ))}

                {designs.length === 0 && (
                    <div className="col-span-full text-center py-12 text-stone-500">
                        No designs found. Create the first one!
                    </div>
                )}
            </div>
        </div>
    );
};

export default Explore;
