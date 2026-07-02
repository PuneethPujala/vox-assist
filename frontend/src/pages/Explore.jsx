import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import gsap from 'gsap';

const Explore = () => {
    const [designs, setDesigns] = useState([]);
    const [loading, setLoading] = useState(true);
    const containerRef = useRef(null);
    const headerRef = useRef(null);

    useEffect(() => {
        fetchDesigns();
    }, []);

    useEffect(() => {
        if (!loading) {
            // Header animation
            gsap.fromTo(headerRef.current,
                { opacity: 0, y: -20 },
                { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out' }
            );

            // Cards stagger entry
            if (designs.length > 0 && containerRef.current) {
                gsap.fromTo(containerRef.current.children,
                    { opacity: 0, y: 30 },
                    { opacity: 1, y: 0, duration: 0.8, stagger: 0.06, ease: 'power3.out', delay: 0.1 }
                );
            }
        }
    }, [loading, designs]);

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

    const handleCardMouseEnter = (e) => {
        gsap.to(e.currentTarget, {
            y: -6,
            scale: 1.015,
            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            borderColor: '#78716c',
            duration: 0.4,
            ease: 'power2.out'
        });
        const thumb = e.currentTarget.querySelector('.card-thumb');
        if (thumb) {
            gsap.to(thumb, { scale: 1.05, duration: 0.4, ease: 'power2.out' });
        }
    };

    const handleCardMouseLeave = (e) => {
        gsap.to(e.currentTarget, {
            y: 0,
            scale: 1,
            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
            borderColor: '#f5f5f4',
            duration: 0.4,
            ease: 'power2.out'
        });
        const thumb = e.currentTarget.querySelector('.card-thumb');
        if (thumb) {
            gsap.to(thumb, { scale: 1, duration: 0.4, ease: 'power2.out' });
        }
    };

    if (loading) {
        return (
            <div className="pt-24 flex justify-center min-h-screen bg-cream">
                <Loader2 className="animate-spin text-charcoal mt-12" size={32} />
            </div>
        );
    }

    return (
        <div className="pt-24 px-6 md:px-12 min-h-screen bg-cream">
            <h1 ref={headerRef} className="text-3xl font-light text-charcoal mb-8 opacity-0">Explore Designs</h1>

            <div ref={containerRef} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                {designs.map((design, idx) => (
                    <div
                        key={design._id || idx}
                        onMouseEnter={handleCardMouseEnter}
                        onMouseLeave={handleCardMouseLeave}
                        className="bg-white rounded-xl overflow-hidden shadow-sm border border-stone-100/80 transition-all duration-300 flex flex-col h-full opacity-0"
                    >
                        {/* Thumbnail Placeholder */}
                        <div className="h-48 bg-stone-100 flex items-center justify-center relative overflow-hidden group">
                            <div className="card-thumb w-full h-full bg-stone-100 flex items-center justify-center transition-transform duration-500">
                                <span className="text-stone-400 text-sm font-medium tracking-wide">3D Model</span>
                            </div>

                            <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center">
                                {design.model_url && (
                                    <a
                                        href={`${import.meta.env.VITE_API_URL}${design.model_url}`}
                                        className="bg-white text-charcoal px-5 py-2.5 rounded-xl text-xs font-semibold tracking-wide hover:bg-stone-50 transition-colors shadow-lg"
                                        download
                                    >
                                        Download .PLY
                                    </a>
                                )}
                            </div>
                        </div>

                        <div className="p-6 flex-1 flex flex-col justify-between">
                            <p className="text-stone-800 text-sm font-medium line-clamp-3 mb-4 leading-relaxed">
                                "{design.prompt}"
                            </p>

                            <div className="flex justify-between items-center text-xs text-stone-500 border-t border-stone-50 pt-4 mt-auto">
                                <span>
                                    {design.created_at ? formatDistanceToNow(new Date(design.created_at), { addSuffix: true }) : 'Recently'}
                                </span>

                                {design.spec_data && (
                                    <span className="bg-stone-50 border border-stone-200/50 px-2.5 py-1 rounded-full text-stone-600 font-mono text-[10px]">
                                        {design.spec_data.rooms.length} Rooms
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                ))}

                {designs.length === 0 && (
                    <div className="col-span-full text-center py-24 text-stone-400 border border-dashed border-stone-200 rounded-2xl bg-white">
                        No designs found. Create the first one!
                    </div>
                )}
            </div>
        </div>
    );
};

export default Explore;
