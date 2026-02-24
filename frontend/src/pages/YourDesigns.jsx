import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuth } from '../contexts/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { Loader2, Trash2, Edit2, Copy, MoreVertical, X, Check, LayoutTemplate } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { toast, Toaster } from 'react-hot-toast'; // Will install react-hot-toast later
import { Skeleton } from '../components/ui/skeleton';

const YourDesigns = () => {
    const { currentUser } = useAuth();
    const [designs, setDesigns] = useState([]);
    const [loading, setLoading] = useState(true);

    // Editing state
    const [editingDesign, setEditingDesign] = useState(null);
    const [editForm, setEditForm] = useState({ name: '', description: '' });

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

    if (loading) return (
        <div className="pt-24 px-6 md:px-12 min-h-screen bg-cream">
            <div className="max-w-7xl mx-auto">
                <Skeleton className="h-10 w-48 mb-8" />
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {[1, 2, 3, 4, 5, 6].map((i) => (
                        <div key={i} className="bg-white rounded-2xl p-6 shadow-sm border border-stone-100">
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
        <div className="pt-24 px-6 md:px-12 min-h-screen bg-cream">
            <Toaster position="bottom-right" />

            <div className="flex justify-between items-center mb-8 max-w-7xl mx-auto">
                <h1 className="text-3xl font-light text-charcoal">My Projects</h1>
                <div className="text-sm px-3 py-1 bg-stone-100 rounded-full text-stone-600 font-medium tracking-wide">
                    {designs.length} Designs
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 max-w-7xl mx-auto">
                {designs.map((design, idx) => (
                    <motion.div
                        key={design._id || idx}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: Math.min(idx * 0.05, 0.5) }}
                        className="bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all border border-stone-100 relative group flex flex-col h-full"
                    >
                        {/* Thumbnail Generator/Placeholder */}
                        <div className="h-40 bg-stone-50 flex flex-col items-center justify-center relative overflow-hidden border-b border-stone-100">
                            <span className="text-stone-300 text-xs font-medium tracking-widest uppercase mb-2">3D Layout</span>
                            {design.spec_data?.rooms && (
                                <div className="flex gap-1">
                                    {design.spec_data.rooms.slice(0, 3).map((r, i) => (
                                        <div key={i} className="w-8 h-8 bg-stone-200 border border-stone-300 rounded-sm"
                                            style={{ width: (r.size?.[0] || 12) * 2, height: (r.size?.[1] || 12) * 2 }}></div>
                                    ))}
                                </div>
                            )}

                            {/* Hover Actions Overlay */}
                            <div className="absolute inset-0 bg-white/90 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col items-center justify-center gap-2 backdrop-blur-sm">
                                {design.model_url && (
                                    <a
                                        href={`${import.meta.env.VITE_API_URL}${design.model_url}`}
                                        className="bg-stone-100 text-stone-700 border border-stone-200 px-4 py-2 rounded-lg text-sm font-medium hover:bg-stone-50 transition-colors shadow-sm w-3/4 text-center"
                                        download
                                    >
                                        Download .PLY
                                    </a>
                                )}
                                {design.stl_url && (
                                    <a
                                        href={`${import.meta.env.VITE_API_URL}${design.stl_url}`}
                                        className="bg-charcoal text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-stone-800 transition-colors shadow-sm w-3/4 text-center"
                                        download
                                    >
                                        3D Print (.STL)
                                    </a>
                                )}
                            </div>

                            {/* Top Right Quick Actions */}
                            <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                                <button onClick={() => handleDuplicate(design._id)} className="p-2 bg-white/80 hover:bg-white text-stone-500 hover:text-charcoal rounded-md shadow-sm tooltip" title="Duplicate">
                                    <Copy size={14} />
                                </button>
                                <button onClick={() => openEditModal(design)} className="p-2 bg-white/80 hover:bg-white text-stone-500 hover:text-charcoal rounded-md shadow-sm tooltip" title="Edit Details">
                                    <Edit2 size={14} />
                                </button>
                                <button onClick={() => handleDelete(design._id)} className="p-2 bg-white/80 hover:bg-red-50 text-stone-500 hover:text-red-600 rounded-md shadow-sm tooltip" title="Delete">
                                    <Trash2 size={14} />
                                </button>
                            </div>
                        </div>

                        {/* Card Body */}
                        <div className="p-5 flex flex-col flex-1">
                            <h3 className="font-semibold text-charcoal line-clamp-1 mb-1" title={design.name || design.prompt}>
                                {design.name || "Untitled Project"}
                            </h3>

                            <p className="text-stone-500 text-xs line-clamp-2 mb-4 flex-1">
                                {design.description || design.prompt}
                            </p>

                            {/* Card Footer */}
                            <div className="flex justify-between items-center text-xs text-stone-400 border-t border-stone-50 pt-3 mt-auto">
                                <span className="flex items-center gap-1 font-medium">
                                    {design.created_at ? formatDistanceToNow(new Date(design.created_at), { addSuffix: true }) : 'Recently'}
                                </span>

                                <div className="flex items-center gap-2 bg-stone-50 px-2 py-1 rounded border border-stone-100">
                                    <span className="text-stone-600 font-medium">
                                        {design.spec_data?.rooms?.length || 0} Rooms
                                    </span>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                ))}

                {designs.length === 0 && (
                    <div className="col-span-full py-24 flex flex-col items-center justify-center text-center bg-white rounded-2xl border border-stone-100 border-dashed">
                        <div className="w-16 h-16 bg-stone-50 flex items-center justify-center rounded-2xl mb-4 text-stone-300">
                            <LayoutTemplate size={32} />
                        </div>
                        <h3 className="text-xl font-medium text-charcoal mb-2">No projects yet</h3>
                        <p className="text-stone-500 mb-6 max-w-sm">Start your architectural journey by generating your first AI-powered floorplan layout.</p>
                        <a href="/create" className="inline-block bg-charcoal text-cream px-6 py-3 rounded-xl hover:bg-stone-800 transition-colors shadow-sm font-medium">
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
                            className="bg-white p-6 rounded-2xl max-w-md w-full shadow-xl border border-stone-100"
                        >
                            <div className="flex justify-between items-center mb-6">
                                <h3 className="text-lg font-medium text-charcoal">Edit Project Details</h3>
                                <button onClick={() => setEditingDesign(null)} className="text-stone-400 hover:text-stone-600">
                                    <X size={20} />
                                </button>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-stone-700 mb-1">Project Name</label>
                                    <input
                                        type="text"
                                        value={editForm.name}
                                        onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                                        className="w-full p-3 border border-stone-200 rounded-lg focus:ring-2 focus:ring-stone-400 outline-none transition-shadow"
                                        placeholder="e.g. Modern Minimalist Villa"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-stone-700 mb-1">Description (Optional)</label>
                                    <textarea
                                        value={editForm.description}
                                        onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                                        className="w-full p-3 border border-stone-200 rounded-lg focus:ring-2 focus:ring-stone-400 outline-none transition-shadow min-h-[100px] resize-none"
                                        placeholder="Add notes about this variation..."
                                    />
                                </div>
                            </div>

                            <div className="flex justify-end gap-3 mt-8">
                                <button onClick={() => setEditingDesign(null)} className="px-5 py-2.5 text-stone-600 hover:bg-stone-50 rounded-xl font-medium transition-colors">
                                    Cancel
                                </button>
                                <button onClick={handleSaveEdit} className="px-5 py-2.5 bg-charcoal text-white rounded-xl hover:bg-stone-800 transition-colors shadow-sm flex items-center gap-2 font-medium">
                                    <Check size={16} /> Save Changes
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
