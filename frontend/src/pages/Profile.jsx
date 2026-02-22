import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { auth, storage } from '../firebase';
import { updateProfile, updatePassword, updateEmail, deleteUser } from 'firebase/auth';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { User, Mail, Calendar, Box, Activity, ArrowRight, Settings as SettingsIcon, LayoutTemplate, AlertTriangle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';

const Profile = () => {
    const { currentUser } = useAuth();
    const navigate = useNavigate();
    const [designs, setDesigns] = useState([]);
    const [mongoUser, setMongoUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'settings'

    const [stats, setStats] = useState({
        totalDesigns: 0,
        avgScore: 0,
        totalRooms: 0
    });

    // Settings State
    const [displayName, setDisplayName] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [message, setMessage] = useState({ type: '', text: '' });
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [uploadingAvatar, setUploadingAvatar] = useState(false);

    useEffect(() => {
        if (currentUser) {
            setDisplayName(currentUser.displayName || '');
            fetchUserData();
        }
    }, [currentUser]);

    const fetchUserData = async () => {
        try {
            const token = await currentUser.getIdToken();
            const [designsRes, userRes] = await Promise.all([
                axios.get(`${import.meta.env.VITE_API_URL}/api/v1/my-designs`, { headers: { Authorization: `Bearer ${token}` } }),
                axios.get(`${import.meta.env.VITE_API_URL}/api/v1/user/me`, { headers: { Authorization: `Bearer ${token}` } }).catch(() => ({ data: { exists: false } }))
            ]);

            const designData = designsRes.data;
            setDesigns(designData);

            if (userRes.data.exists) {
                setMongoUser(userRes.data.data);
            }

            const totalDesigns = designData.length;
            const totalScore = designData.reduce((acc, curr) => acc + (curr.score || 0), 0);
            const avgScore = totalDesigns > 0 ? Math.round(totalScore / totalDesigns) : 0;
            const totalRooms = designData.reduce((acc, curr) => acc + (curr.spec_data?.rooms?.length || 0), 0);

            setStats({ totalDesigns, avgScore, totalRooms });
        } catch (error) {
            console.error("Error fetching profile data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleUpdateProfile = async (e) => {
        e.preventDefault();
        setMessage({ type: '', text: '' });
        try {
            if (displayName !== currentUser.displayName) {
                await updateProfile(auth.currentUser, { displayName });

                // Also update in mongo
                const token = await currentUser.getIdToken();
                await axios.post(`${import.meta.env.VITE_API_URL}/api/v1/user/profile`, {
                    email: currentUser.email,
                    full_name: displayName,
                    photo_url: currentUser.photoURL,
                    firebase_uid: currentUser.uid
                }, { headers: { Authorization: `Bearer ${token}` } });
            }
            if (newPassword) {
                await updatePassword(auth.currentUser, newPassword);
                setNewPassword('');
            }
            setMessage({ type: 'success', text: 'Profile updated successfully!' });
        } catch (error) {
            if (error.code === 'auth/requires-recent-login') {
                setMessage({ type: 'error', text: 'Please sign out and log back in to change your password.' });
            } else {
                setMessage({ type: 'error', text: error.message.replace("Firebase: ", "") });
            }
        }
    };

    const handleAvatarUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        try {
            setUploadingAvatar(true);
            const avatarRef = ref(storage, `avatars/${currentUser.uid}/${file.name}`);
            await uploadBytes(avatarRef, file);
            const photoURL = await getDownloadURL(avatarRef);

            await updateProfile(auth.currentUser, { photoURL });

            // Sync with backend
            const token = await currentUser.getIdToken();
            await axios.post(`${import.meta.env.VITE_API_URL}/api/v1/user/profile`, {
                email: currentUser.email,
                full_name: currentUser.displayName,
                photo_url: photoURL,
                firebase_uid: currentUser.uid
            }, { headers: { Authorization: `Bearer ${token}` } });

            setMessage({ type: 'success', text: 'Avatar updated successfully!' });
            // Force a re-render by updating local dummy state or context if needed
            window.location.reload();
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to upload avatar: ' + error.message });
        } finally {
            setUploadingAvatar(false);
        }
    };

    const handleDeleteAccount = async () => {
        try {
            await deleteUser(auth.currentUser);
            navigate('/login');
        } catch (error) {
            if (error.code === 'auth/requires-recent-login') {
                setMessage({ type: 'error', text: 'Please sign out and log back in to delete your account.' });
                setShowDeleteModal(false);
            } else {
                setMessage({ type: 'error', text: error.message });
            }
        }
    };

    if (loading) return (
        <div className="pt-24 px-6 md:px-12 min-h-screen bg-cream">
            <div className="max-w-6xl mx-auto">
                <div className="bg-white rounded-2xl p-8 shadow-sm border border-stone-100 flex flex-col md:flex-row items-center md:items-start gap-8">
                    <Skeleton className="w-32 h-32 rounded-full" />
                    <div className="flex-1 w-full flex flex-col items-center md:items-start space-y-4">
                        <Skeleton className="h-8 w-48" />
                        <Skeleton className="h-4 w-64" />
                        <Skeleton className="h-6 w-32 rounded-full mt-2" />
                    </div>
                </div>
                <div className="flex gap-6 mt-8 border-b border-stone-200 pb-4">
                    <Skeleton className="h-6 w-24" />
                    <Skeleton className="h-6 w-24" />
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
                    <Skeleton className="h-32 w-full rounded-xl" />
                    <Skeleton className="h-32 w-full rounded-xl" />
                    <Skeleton className="h-32 w-full rounded-xl" />
                </div>
            </div>
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
                    <div className="relative group cursor-pointer" onClick={() => document.getElementById('avatar-upload').click()}>
                        <div className={`w-32 h-32 rounded-full overflow-hidden border-4 border-white shadow-lg bg-stone-200 ${uploadingAvatar ? 'opacity-50' : 'group-hover:opacity-80'} transition-opacity`}>
                            {currentUser.photoURL ? (
                                <img src={currentUser.photoURL} alt="Profile" className="w-full h-full object-cover" />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center bg-charcoal text-white text-4xl font-light">
                                    {currentUser.email?.[0].toUpperCase()}
                                </div>
                            )}
                        </div>
                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <span className="text-white text-xs font-medium bg-black/50 px-2 py-1 rounded">Change</span>
                        </div>
                        <input
                            type="file"
                            id="avatar-upload"
                            className="hidden"
                            accept="image/*"
                            onChange={handleAvatarUpload}
                            disabled={uploadingAvatar}
                        />
                    </div>

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
                        {mongoUser && (
                            <div className="mt-4 inline-block bg-stone-100 text-charcoal px-3 py-1 rounded-full text-xs font-medium uppercase tracking-wider">
                                Current Plan: {mongoUser.role}
                            </div>
                        )}
                    </div>
                </motion.div>

                {/* Tabs */}
                <div className="flex gap-6 mt-8 border-b border-stone-200">
                    <button
                        onClick={() => setActiveTab('overview')}
                        className={`pb-4 flex items-center gap-2 transition-colors ${activeTab === 'overview' ? 'border-b-2 border-charcoal text-charcoal' : 'text-stone-500 hover:text-charcoal'}`}
                    >
                        <LayoutTemplate size={18} /> Overview
                    </button>
                    <button
                        onClick={() => setActiveTab('settings')}
                        className={`pb-4 flex items-center gap-2 transition-colors ${activeTab === 'settings' ? 'border-b-2 border-charcoal text-charcoal' : 'text-stone-500 hover:text-charcoal'}`}
                    >
                        <SettingsIcon size={18} /> Settings
                    </button>
                </div>

                {/* Content */}
                <div className="mt-8 mb-12">
                    {activeTab === 'overview' ? (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                                <StatCard icon={<Box />} label="Total Designs" value={stats.totalDesigns} delay={0.1} />
                                <StatCard icon={<Activity />} label="Avg. Efficiency" value={`${stats.avgScore}%`} delay={0.2} />
                                <StatCard icon={<Box />} label="Rooms Planned" value={stats.totalRooms} delay={0.3} />
                            </div>

                            <div className="flex justify-between items-center mb-6">
                                <h2 className="text-2xl font-light text-charcoal">Recent Activity</h2>
                                <Link to="/my-designs" className="text-stone-500 hover:text-charcoal flex items-center gap-1 text-sm">
                                    View All <ArrowRight size={16} />
                                </Link>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                {designs.slice(0, 3).map((design, idx) => (
                                    <Card key={idx}>
                                        <CardContent className="p-4">
                                            <h3 className="font-medium truncate">{design.prompt || "Untitled Project"}</h3>
                                            <p className="text-sm text-stone-500 mt-2">{formatDistanceToNow(new Date(design.created_at), { addSuffix: true })}</p>
                                        </CardContent>
                                    </Card>
                                ))}
                                {designs.length === 0 && (
                                    <div className="col-span-full py-12 text-center text-stone-500 bg-stone-50 rounded-xl border border-dashed border-stone-200">
                                        No designs yet. <Link to="/create" className="underline text-charcoal">Create one.</Link>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    ) : (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-2xl bg-white p-8 rounded-2xl shadow-sm border border-stone-100">
                            <h2 className="text-2xl font-light text-charcoal mb-6">Account Settings</h2>

                            {message.text && (
                                <div className={`mb-6 p-4 rounded-lg text-sm border ${message.type === 'error' ? 'bg-red-50 text-red-600 border-red-100' : 'bg-green-50 text-green-600 border-green-100'}`}>
                                    {message.text}
                                </div>
                            )}

                            <form onSubmit={handleUpdateProfile} className="space-y-6">
                                <div>
                                    <label className="block text-sm font-medium text-stone-700 mb-2">Display Name</label>
                                    <Input
                                        value={displayName}
                                        onChange={(e) => setDisplayName(e.target.value)}
                                        placeholder="Your Name"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-stone-700 mb-2">Email Address (Read-only)</label>
                                    <Input
                                        type="email"
                                        value={currentUser.email}
                                        readOnly
                                        disabled
                                        className="bg-stone-50"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-stone-700 mb-2">New Password (leave blank to keep current)</label>
                                    <Input
                                        type="password"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        placeholder="••••••••"
                                    />
                                </div>

                                <Button type="submit">
                                    Save Changes
                                </Button>
                            </form>

                            <hr className="my-8 border-stone-200" />

                            <div>
                                <h3 className="text-red-600 font-medium mb-2 flex items-center gap-2"><AlertTriangle size={18} /> Danger Zone</h3>
                                <p className="text-sm text-stone-500 mb-4">Once you delete your account, there is no going back. Please be certain.</p>
                                <Button
                                    variant="destructive"
                                    onClick={(e) => { e.preventDefault(); setShowDeleteModal(true); }}
                                >
                                    Delete Account
                                </Button>
                            </div>
                        </motion.div>
                    )}
                </div>
            </div>

            {/* Delete Confirmation Modal */}
            <AnimatePresence>
                {showDeleteModal && (
                    <motion.div
                        initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                        className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
                    >
                        <motion.div
                            initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
                            className="bg-white p-6 rounded-2xl max-w-md w-full shadow-2xl"
                        >
                            <h3 className="text-xl font-medium text-charcoal mb-4">Delete Account?</h3>
                            <p className="text-stone-500 mb-6">Are you sure you want to permanently delete your account? All your designs and data will be lost.</p>
                            <div className="flex gap-4 justify-end mt-6">
                                <Button variant="secondary" onClick={() => setShowDeleteModal(false)}>Cancel</Button>
                                <Button variant="destructive" onClick={handleDeleteAccount}>Yes, Delete</Button>
                            </div>
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};

const StatCard = ({ icon, label, value, delay }) => (
    <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay }}
    >
        <Card>
            <CardContent className="flex items-center gap-4 p-6 text-left w-full h-full">
                <div className="p-3 bg-stone-50 text-stone-900 rounded-lg shadow-sm border border-stone-100">
                    {React.cloneElement(icon, { size: 24 })}
                </div>
                <div>
                    <div className="text-2xl font-light text-stone-900">{value}</div>
                    <div className="text-xs text-stone-500 uppercase tracking-wide font-medium">{label}</div>
                </div>
            </CardContent>
        </Card>
    </motion.div>
);

export default Profile;
