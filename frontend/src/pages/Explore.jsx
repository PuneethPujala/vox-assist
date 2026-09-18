import React, { useEffect, useState, useRef } from 'react';
import api, { API_BASE_URL } from '../lib/api';
import { formatDistanceToNow } from 'date-fns';
import gsap from 'gsap';
import { Skeleton } from '../components/ui/skeleton';
import { AlertCircle, RefreshCw } from 'lucide-react';

const Explore = () => {
    const [designs, setDesigns] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [loadingSeconds, setLoadingSeconds] = useState(0);
    const containerRef = useRef(null);
    const headerRef = useRef(null);

    // Track loading time to give friendly cold-start feedback
    useEffect(() => {
        let timer;
        if (loading) {
            timer = setInterval(() => {
                setLoadingSeconds(s => s + 1);
            }, 1000);
        } else {
            setLoadingSeconds(0);
        }
        return () => clearInterval(timer);
    }, [loading]);

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
        setLoading(true);
        setError(null);
        setLoadingSeconds(0);
        try {
            const response = await api.get('/api/v1/designs');
            setDesigns(response.data || []);
        } catch (err) {
            console.error("Error fetching designs:", err);
            setError(err.friendlyMessage || err.response?.data?.detail || "Failed to load community designs.");
        } finally {
            setLoading(false);
        }
    };

    const handleCardMouseEnter = (e) => {
        const isDark = document.documentElement.classList.contains('dark');
        gsap.to(e.currentTarget, {
            y: -6,
            scale: 1.015,
            boxShadow: isDark ? '0 20px 25px -5px rgba(0, 0, 0, 0.4)' : '0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            borderColor: isDark ? '#57534e' : '#78716c',
            duration: 0.4,
            ease: 'power2.out'
        });
        const thumb = e.currentTarget.querySelector('.card-thumb');
        if (thumb) {
            gsap.to(thumb, { scale: 1.05, duration: 0.4, ease: 'power2.out' });
        }
    };

    const handleCardMouseLeave = (e) => {
        const isDark = document.documentElement.classList.contains('dark');
        gsap.to(e.currentTarget, {
            y: 0,
            scale: 1,
            boxShadow: 'none',
            borderColor: isDark ? '#292524' : '#e7e5e4',
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
            <div className="page-container">
                <div className="max-w-7xl mx-auto">
                    <div className="flex justify-between items-center mb-6">
                        <Skeleton className="h-10 w-48" />
                        {loadingSeconds >= 4 && (
                            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300 text-xs font-mono animate-pulse">
                                <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                                Backend waking up ({loadingSeconds}s)...
                            </div>
                        )}
                    </div>

                    {loadingSeconds >= 5 && (
                        <div className="mb-8 p-4 rounded-2xl bg-amber-50/90 dark:bg-amber-950/40 border border-amber-200/80 dark:border-amber-900/60 text-xs text-amber-900 dark:text-amber-200 flex items-start gap-3">
                            <span className="text-base">⚡</span>
                            <div>
                                <p className="font-semibold mb-0.5">Waking up cloud server from sleep</p>
                                <p className="text-amber-700 dark:text-amber-300/80 text-[11px] font-sans">
                                    Free cloud instances (Render) spin down after inactivity. Cold starts take ~40–60 seconds. Community designs will appear shortly!
                                </p>
                            </div>
                        </div>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {[1, 2, 3, 4, 5, 6].map((i) => (
                            <div key={i} className="glass-card h-80 flex flex-col justify-between">
                                <Skeleton className="h-40 w-full rounded-2xl mb-4" />
                                <Skeleton className="h-6 w-3/4 mb-3" />
                                <Skeleton className="h-4 w-1/2" />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        );
    }
 
    return (
        <div className="page-container">
            <div ref={headerRef} className="max-w-7xl mx-auto mb-8 opacity-0 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-light text-charcoal dark:text-stone-100 mb-1">Explore Layouts</h1>
                    <p className="text-stone-500 dark:text-stone-400 text-xs font-light font-sans">Discover and download architectural configurations generated by the community.</p>
                </div>
                <div className="flex gap-2 flex-wrap items-center">
                    <span className="badge-premium bg-stone-900 text-stone-100 dark:bg-stone-100 dark:text-stone-900 border border-stone-900 dark:border-stone-100">All</span>
                    <span className="badge-premium bg-white dark:bg-stone-900 hover:bg-stone-50 dark:hover:bg-stone-850 text-stone-400 dark:text-stone-400 hover:text-stone-600 dark:hover:text-stone-200 border border-stone-200/50 dark:border-stone-800 cursor-pointer">Minimalist</span>
                    <span className="badge-premium bg-white dark:bg-stone-900 hover:bg-stone-50 dark:hover:bg-stone-850 text-stone-400 dark:text-stone-400 hover:text-stone-600 dark:hover:text-stone-200 border border-stone-200/50 dark:border-stone-800 cursor-pointer">3BHK</span>
                    <span className="badge-premium bg-white dark:bg-stone-900 hover:bg-stone-50 dark:hover:bg-stone-850 text-stone-400 dark:text-stone-400 hover:text-stone-600 dark:hover:text-stone-200 border border-stone-200/50 dark:border-stone-800 cursor-pointer">Modern</span>
                </div>
            </div>
 
            <div ref={containerRef} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-7xl mx-auto">
                {designs.map((design, idx) => (
                    <div
                        key={design._id || idx}
                        onMouseEnter={handleCardMouseEnter}
                        onMouseLeave={handleCardMouseLeave}
                        className="bg-white/85 dark:bg-stone-900/85 border border-stone-200/60 dark:border-stone-800 rounded-3xl shadow-lg hover:shadow-2xl transition-all duration-300 flex flex-col h-full opacity-0 overflow-hidden backdrop-blur-md cursor-pointer"
                    >
                        {/* Thumbnail Placeholder */}
                        <div className="h-48 bg-[#fbfbf9] dark:bg-stone-950 bg-[linear-gradient(rgba(0,0,0,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(0,0,0,0.02)_1px,transparent_1px)] dark:bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:18px_18px] flex items-center justify-center relative overflow-hidden group border-b border-stone-150 dark:border-stone-800">
                            <div className="card-thumb w-full h-full flex items-center justify-center transition-transform duration-500">
                                {design.spec_data?.rooms ? (
                                    <div className="flex gap-2 items-center justify-center w-full px-6">
                                        {design.spec_data.rooms.slice(0, 4).map((r, i) => (
                                            <div 
                                                key={i} 
                                                className="border rounded-xl shadow-[inset_0_2px_4px_rgba(0,0,0,0.02)] flex items-center justify-center text-[8px] font-bold font-mono"
                                                style={{ 
                                                    width: Math.max(34, (r.size?.[0] || 12) * 2.8), 
                                                    height: Math.max(34, (r.size?.[1] || 12) * 2.8),
                                                    backgroundColor: `${r.color || '#e5e7eb'}18`,
                                                    borderColor: r.color || '#d6d3d1',
                                                    color: r.color || '#78716c'
                                                }}
                                            >
                                                <span className="opacity-60">{r.type.substring(0, 2).toUpperCase()}</span>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <span className="text-stone-300 dark:text-stone-600 text-xs font-bold font-mono tracking-widest uppercase">3D Mesh Preview</span>
                                )}
                            </div>
 
                            <div className="absolute inset-0 bg-black/30 backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity duration-250 flex items-center justify-center">
                                {design.model_url && (
                                    <a
                                        href={`${API_BASE_URL}${design.model_url}`}
                                        className="btn-primary text-xs"
                                        download
                                    >
                                        Download .PLY
                                    </a>
                                )}
                            </div>
                        </div>
 
                        <div className="p-6 flex-1 flex flex-col justify-between">
                            <p className="text-stone-700 dark:text-stone-300 text-xs font-light line-clamp-3 mb-4 leading-relaxed font-sans">
                                "{design.prompt}"
                            </p>
 
                            <div className="flex justify-between items-center text-[10px] font-mono text-stone-400 dark:text-stone-500 border-t border-stone-150 dark:border-stone-800 pt-4 mt-auto">
                                <span>
                                    {design.created_at ? formatDistanceToNow(new Date(design.created_at), { addSuffix: true }) : 'Recently'}
                                </span>
 
                                {design.spec_data && (
                                    <span className="bg-stone-50 dark:bg-stone-850 border border-stone-200/50 dark:border-stone-800 px-2.5 py-0.5 rounded-full text-stone-600 dark:text-stone-300 font-bold uppercase tracking-wider">
                                        {design.spec_data.rooms.length} Rooms
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
 
                {error ? (
                    <div className="col-span-full py-16 flex flex-col items-center justify-center text-center glass-card border border-red-200/70 dark:border-red-900/60 p-8 max-w-lg mx-auto bg-red-50/20 dark:bg-red-950/20 rounded-3xl">
                        <div className="w-14 h-14 bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400 rounded-2xl flex items-center justify-center mb-4">
                            <AlertCircle size={26} />
                        </div>
                        <h3 className="text-lg font-medium text-charcoal dark:text-stone-100 mb-2">Unable to Load Layouts</h3>
                        <p className="text-xs text-stone-500 dark:text-stone-400 mb-6 max-w-sm font-sans">
                            {error} <br />
                            Free cloud instances go to sleep when idle and can take up to a minute to wake up.
                        </p>
                        <button
                            onClick={fetchDesigns}
                            className="btn-primary flex items-center gap-2"
                        >
                            <RefreshCw size={14} /> Retry Connection
                        </button>
                    </div>
                ) : designs.length === 0 && (
                    <div className="col-span-full py-16 text-center text-xs font-mono text-stone-400 dark:text-stone-500 border border-dashed border-stone-300/80 dark:border-stone-700 rounded-3xl bg-white/50 dark:bg-stone-900/50">
                        No designs found. Create the first one!
                    </div>
                )}
            </div>
        </div>
    );
};

export default Explore;
