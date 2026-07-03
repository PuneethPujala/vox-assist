import React, { useEffect, useState, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { AnimatePresence, motion } from 'framer-motion';
import { Loader2, Trash2, Edit2, Copy, MoreVertical, X, Check, LayoutTemplate } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { toast, Toaster } from 'react-hot-toast';
import { Skeleton } from '../components/ui/skeleton';
import gsap from 'gsap';

const YourDesigns = () => {
    const { currentUser } = useAuth();
    const [designs, setDesigns] = useState([]);
    const [loading, setLoading] = useState(true);

    const headerRef = useRef(null);
    const containerRef = useRef(null);

    // Editing state
    const [editingDesign, setEditingDesign] = useState(null);
    const [editForm, setEditForm] = useState({ name: '', description: '' });

    useEffect(() => {
        if (currentUser) {
            fetchMyDesigns();
        }
    }, [currentUser]);

    useEffect(() => {
        if (!loading) {
            // Header animation
            gsap.fromTo(headerRef.current,
                { opacity: 0, y: -15 },
                { opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }
            );

            // Cards stagger entry
            if (designs.length > 0 && containerRef.current) {
                gsap.fromTo(containerRef.current.children,
                    { opacity: 0, y: 25 },
                    { opacity: 1, y: 0, duration: 0.7, stagger: 0.05, ease: 'power3.out', delay: 0.05 }
                );
            }
        }
    }, [loading, designs]);

    const fetchMyDesigns = async () => {
        try {
            const token = await currentUser.getIdToken();
            const response = await axios.get(`${import.meta.env.VITE_API_URL}/api/v1/my-designs`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            setDesigns(response.data);
        } catch (error) {
            console.error("Error fetching designs:", error);
            toast.error("Failed to load designs");
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id) => {
        if (!window.confirm("Are you sure you want to delete this design?")) return;
        try {
            const token = await currentUser.getIdToken();
            await axios.put(`${import.meta.env.VITE_API_URL}/api/v1/designs/${id}`,
                { is_deleted: true },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            toast.success("Design deleted");
            setDesigns(designs.filter(d => d._id !== id));
        } catch (error) {
            toast.error("Failed to delete design");
        }
    };

    const handleDuplicate = async (id) => {
        toast.loading("Duplicating...", { id: 'dup' });
        try {
            const token = await currentUser.getIdToken();
            await axios.post(`${import.meta.env.VITE_API_URL}/api/v1/designs/${id}/duplicate`, {}, {
                headers: { Authorization: `Bearer ${token}` }
            });
            toast.success("Design duplicated", { id: 'dup' });
            fetchMyDesigns();
        } catch (error) {
            toast.error("Failed to duplicate design", { id: 'dup' });
        }
    };

    const openEditModal = (design) => {
        setEditingDesign(design);
        setEditForm({ name: design.name || 'Untitled Project', description: design.description || '' });
    };

    const handleSaveEdit = async () => {
        try {
            const token = await currentUser.getIdToken();
            await axios.put(`${import.meta.env.VITE_API_URL}/api/v1/designs/${editingDesign._id}`,
                { name: editForm.name, description: editForm.description },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            toast.success("Design updated");

            // Update local state
            setDesigns(designs.map(d => d._id === editingDesign._id ? { ...d, name: editForm.name, description: editForm.description } : d));
            setEditingDesign(null);
        } catch (error) {
            toast.error("Failed to update design");
        }
    };

    const handleCardMouseEnter = (e) => {
        gsap.to(e.currentTarget, {
            y: -5,
            scale: 1.015,
            boxShadow: '0 15px 30px -10px rgba(0, 0, 0, 0.08), 0 8px 15px -8px rgba(0, 0, 0, 0.04)',
            borderColor: '#78716c',
            duration: 0.35,
            ease: 'power2.out'
        });
    };

    const handleCardMouseLeave = (e) => {
        gsap.to(e.currentTarget, {
            y: 0,
            scale: 1,
            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)',
            borderColor: '#f5f5f4',
            duration: 0.35,
            ease: 'power2.out'
        });
    };

    if (loading) return (
        <div className="page-container">
            <div className="max-w-7xl mx-auto">
                <Skeleton className="h-10 w-48 mb-8" />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                        <div key={i} className="glass-card">
                            <Skeleton className="h-6 w-3/4 mb-3" />
                            <Skeleton className="h-4 w-1/2 mb-6" />
                            <div className="flex gap-2 mb-4">
                                <Skeleton className="h-6 w-16 rounded-full" />
                                <Skeleton className="h-6 w-16 rounded-full" />
                            </div>
                            <div className="flex justify-between mt-4">
                                <Skeleton className="h-8 w-24 rounded-md" />
                                <div className="flex gap-2">
                                    <Skeleton className="h-8 w-8 rounded-md" />
                                    <Skeleton className="h-8 w-8 rounded-md" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
 
    return (
        <div className="page-container">
            <Toaster position="bottom-right" />
 
            <div ref={headerRef} className="flex justify-between items-center mb-8 max-w-7xl mx-auto opacity-0">
                <h1 className="text-2xl font-light text-charcoal">My Projects</h1>
                <div className="badge-premium bg-stone-50 text-stone-600 border border-stone-200/60 font-mono text-[10px]">
                    {designs.length} Saved Variations
                </div>
            </div>
 
            <div ref={containerRef} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 max-w-7xl mx-auto">
                {designs.map((design, idx) => (
                    <div
                        key={design._id || idx}
                        onMouseEnter={handleCardMouseEnter}
                        onMouseLeave={handleCardMouseLeave}
                        className="bg-white/85 border border-stone-200/60 rounded-3xl shadow-lg hover:shadow-2xl transition-all duration-300 relative group flex flex-col h-full opacity-0 overflow-hidden backdrop-blur-md cursor-pointer"
                    >
                        {/* Thumbnail Generator/Placeholder */}
                        <div className="h-40 bg-stone-50/50 flex flex-col items-center justify-center relative overflow-hidden border-b border-stone-150">
                            <span className="text-stone-300 text-[10px] font-bold tracking-widest uppercase mb-2 font-mono">3D Mesh View</span>
                            {design.spec_data?.rooms && (
                                <div className="flex gap-1 items-center justify-center">
                                    {design.spec_data.rooms.slice(0, 3).map((r, i) => (
                                        <div key={i} className="w-8 h-8 bg-stone-200/50 border border-stone-300/60 rounded-lg shadow-sm"
                                            style={{ width: Math.max(16, (r.size?.[0] || 12) * 2), height: Math.max(16, (r.size?.[1] || 12) * 2) }}></div>
                                    ))}
                                </div>
                            )}
 
                            {/* Hover Actions Overlay */}
                            <div className="absolute inset-0 bg-white/90 opacity-0 group-hover:opacity-100 transition-all duration-250 flex items-center justify-center gap-2 backdrop-blur-sm">
                                {design.model_url && (
                                    <a
                                        href={`${import.meta.env.VITE_API_URL}${design.model_url}`}
                                        className="btn-primary text-xs"
                                        download
                                    >
                                        Download .PLY
                                    </a>
                                )}
                            </div>
 
                            {/* Top Right Quick Actions */}
                            <div className="absolute top-3 right-3 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-all duration-250 z-10">
                                <button onClick={() => handleDuplicate(design._id)} className="icon-btn" title="Duplicate">
                                    <Copy size={13} />
                                </button>
                                <button onClick={() => openEditModal(design)} className="icon-btn" title="Edit Details">
                                    <Edit2 size={13} />
                                </button>
                                <button onClick={() => handleDelete(design._id)} className="icon-btn hover:text-red-600 hover:bg-red-50" title="Delete">
                                    <Trash2 size={13} />
                                </button>
                            </div>
                        </div>
 
                        {/* Card Body */}
                        <div className="p-5 flex flex-col flex-1">
                            <h3 className="font-semibold text-charcoal line-clamp-1 mb-1" title={design.name || design.prompt}>
                                {design.name || "Untitled Project"}
                            </h3>
 
                            <p className="text-stone-500 text-xs line-clamp-2 mb-4 flex-1 font-sans font-light">
                                {design.description || design.prompt}
                            </p>
 
                            {/* Card Footer */}
                            <div className="flex justify-between items-center text-[10px] font-mono text-stone-400 border-t border-stone-150 pt-3 mt-auto">
                                <span className="flex items-center gap-1 font-medium">
                                    {design.created_at ? formatDistanceToNow(new Date(design.created_at), { addSuffix: true }) : 'Recently'}
                                </span>
 
                                <div className="flex items-center gap-2 bg-stone-50 border border-stone-200/50 px-2 py-0.5 rounded-full">
                                    <span className="text-stone-600 font-bold uppercase tracking-wider">
                                        {design.spec_data?.rooms?.length || 0} Rooms
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
 
                {designs.length === 0 && (
                    <div className="col-span-full py-20 flex flex-col items-center justify-center text-center glass-card border border-dashed border-stone-300/80 p-8">
                        <div className="w-16 h-16 bg-stone-50/50 border border-stone-200/60 flex items-center justify-center rounded-2xl mb-4 text-stone-400 shadow-sm">
                            <LayoutTemplate size={28} />
                        </div>
                        <h3 className="text-lg font-light text-charcoal mb-2">No projects compiled yet</h3>
                        <p className="text-xs text-stone-500 mb-6 max-w-sm font-sans font-light">Start your layout architecture by running our dynamic layout wizard.</p>
                        <a href="/create" className="btn-primary">
                            Create New Project
                        </a>
                    </div>
                )}
            </div>
 
            {/* Edit Modal */}
            <AnimatePresence>
                {editingDesign && (
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50"
                    >
                        <motion.div
                            initial={{ scale: 0.95, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.95, y: 20 }}
                            className="glass-card max-w-md w-full border border-stone-200 shadow-2xl"
                        >
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-lg font-light text-charcoal">Edit Project Details</h3>
                                <button onClick={() => setEditingDesign(null)} className="text-stone-400 hover:text-stone-600">
                                    <X size={18} />
                                </button>
                            </div>
 
                            <div className="space-y-4">
                                <div>
                                    <label className="block text-xs font-bold text-stone-600 mb-2">Project Name</label>
                                    <input
                                        type="text"
                                        value={editForm.name}
                                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                                        className="input-field font-sans"
                                        placeholder="e.g. Modern Minimalist Villa"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-stone-600 mb-2">Description (Optional)</label>
                                    <textarea
                                        value={editForm.description}
                                        onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                                        className="input-field font-sans min-h-[100px] resize-none"
                                        placeholder="Add notes about this variation..."
                                    />
                                </div>
                            </div>
 
                            <div className="flex justify-end gap-3 mt-8">
                                <button onClick={() => setEditingDesign(null)} className="btn-secondary">
                                    Cancel
                                </button>
                                <button onClick={handleSaveEdit} className="btn-primary">
                                    <Check size={14} /> Save Changes
                                </button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default YourDesigns;
