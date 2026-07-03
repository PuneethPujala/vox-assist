import React, { useEffect, useState, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { auth, storage } from '../firebase';
import { updateProfile, updatePassword } from 'firebase/auth';
import { ref, uploadBytes, getDownloadURL } from 'firebase/storage';
import axios from 'axios';
import { AnimatePresence, motion } from 'framer-motion';
import { User, Mail, Calendar, Box, Activity, ArrowRight, Settings as SettingsIcon, LayoutTemplate, AlertTriangle } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { formatDistanceToNow } from 'date-fns';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Card, CardContent } from '../components/ui/card';
import { Skeleton } from '../components/ui/skeleton';
import gsap from 'gsap';

const Profile = () => {
    const { currentUser } = useAuth();
    const navigate = useNavigate();
    const [designs, setDesigns] = useState([]);
    const [mongoUser, setMongoUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'settings'

    const profileHeaderRef = useRef(null);
    const statsGridRef = useRef(null);
    const activityGridRef = useRef(null);
    const settingsFormRef = useRef(null);

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

    useEffect(() => {
        if (!loading) {
            // Profile header fade in
            gsap.fromTo(profileHeaderRef.current,
                { opacity: 0, y: -15 },
                { opacity: 1, y: 0, duration: 0.6, ease: 'power3.out' }
            );
        }
    }, [loading]);

    useEffect(() => {
        if (!loading) {
            if (activeTab === 'overview') {
                if (statsGridRef.current) {
                    gsap.fromTo(statsGridRef.current.children,
                        { opacity: 0, scale: 0.95, y: 15 },
                        { opacity: 1, scale: 1, y: 0, duration: 0.5, stagger: 0.08, ease: 'power2.out' }
                    );
                }
                if (activityGridRef.current) {
                    gsap.fromTo(activityGridRef.current.children,
                        { opacity: 0, y: 20 },
                        { opacity: 1, y: 0, duration: 0.6, stagger: 0.06, ease: 'power3.out', delay: 0.2 }
                    );
                }
            } else if (activeTab === 'settings') {
                if (settingsFormRef.current) {
                    gsap.fromTo(settingsFormRef.current.children,
                        { opacity: 0, y: 15 },
                        { opacity: 1, y: 0, duration: 0.6, stagger: 0.05, ease: 'power3.out' }
                    );
                }
            }
        }
    }, [activeTab, loading]);

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
            window.location.reload();
        } catch (error) {
            setMessage({ type: 'error', text: 'Failed to upload avatar: ' + error.message });
        } finally {
            setUploadingAvatar(false);
        }
    };

    const handleDeleteAccount = async () => {
        try {
            const { deleteUser: firebaseDeleteUser } = await import("firebase/auth");
            await firebaseDeleteUser(auth.currentUser);
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
        <div className="page-container">
            <div className="max-w-6xl mx-auto">
                <div className="glass-card flex flex-col md:flex-row items-center md:items-start gap-8">
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
        <div className="page-container">
            <div className="max-w-6xl mx-auto">
                {/* Header Section */}
                <div
                    ref={profileHeaderRef}
                    className="glass-card flex flex-col md:flex-row items-center md:items-start gap-8 opacity-0"
                >
                    <div className="relative group cursor-pointer" onClick={() => document.getElementById('avatar-upload').click()}>
                        <div className={`w-32 h-32 rounded-full overflow-hidden border-4 border-white shadow-lg bg-stone-200 ${uploadingAvatar ? 'opacity-50' : 'group-hover:opacity-85'} transition-opacity`}>
                            {currentUser.photoURL ? (
                                <img src={currentUser.photoURL} alt="Profile" className="w-full h-full object-cover" />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center bg-charcoal text-white text-4xl font-light font-mono">
                                    {currentUser.email?.[0].toUpperCase()}
                                </div>
                            )}
                        </div>
                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <span className="text-white text-[10px] font-bold uppercase tracking-wider bg-black/60 px-2.5 py-1 rounded-xl">Change</span>
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
                        <h1 className="text-2xl font-light text-charcoal mb-2">
                            {currentUser.displayName || "Architect"}
                        </h1>
                        <div className="flex flex-col md:flex-row gap-4 text-stone-500 text-xs md:items-center font-mono">
                            <span className="flex items-center gap-2 justify-center md:justify-start">
                                <Mail size={14} className="text-stone-400" /> {currentUser.email}
                            </span>
                            <span className="hidden md:inline text-stone-300">•</span>
                            <span className="flex items-center gap-2 justify-center md:justify-start">
                                <Calendar size={14} className="text-stone-400" /> Joined {currentUser.metadata.creationTime ? new Date(currentUser.metadata.creationTime).toLocaleDateString() : 'Recently'}
                            </span>
                        </div>
                        {mongoUser && (
                            <div className="mt-4 inline-block bg-stone-100 border border-stone-200/50 text-charcoal px-3.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider font-mono">
                                Role: {mongoUser.role}
                            </div>
                        )}
                    </div>
                </div>
 
                {/* Tabs */}
                <div className="flex gap-6 mt-8 border-b border-stone-200">
                    <button
                        onClick={() => setActiveTab('overview')}
                        className={`pb-3 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all border-b-2 ${activeTab === 'overview' ? 'border-charcoal text-charcoal' : 'border-transparent text-stone-400 hover:text-charcoal'}`}
                    >
                        <LayoutTemplate size={14} /> Overview
                    </button>
                    <button
                        onClick={() => setActiveTab('settings')}
                        className={`pb-3 text-xs font-bold uppercase tracking-wider flex items-center gap-2 transition-all border-b-2 ${activeTab === 'settings' ? 'border-charcoal text-charcoal' : 'border-transparent text-stone-400 hover:text-charcoal'}`}
                    >
                        <SettingsIcon size={14} /> Settings
                    </button>
                </div>
 
                {/* Content */}
                <div className="mt-8 mb-12">
                    {activeTab === 'overview' ? (
                        <div className="space-y-8">
                            <div ref={statsGridRef} className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <StatCard icon={<Box />} label="Total Designs" value={stats.totalDesigns} />
                                <StatCard icon={<Activity />} label="Avg. Score" value={`${stats.avgScore}%`} />
                                <StatCard icon={<Box />} label="Rooms Planned" value={stats.totalRooms} />
                            </div>
 
                            <div className="flex justify-between items-center">
                                <h2 className="text-xl font-light text-charcoal">Recent Activity</h2>
                                <Link to="/my-designs" className="text-stone-500 hover:text-charcoal flex items-center gap-1 text-xs font-bold uppercase tracking-wider">
                                    View All <ArrowRight size={14} />
                                </Link>
                            </div>
 
                            <div ref={activityGridRef} className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                {designs.slice(0, 3).map((design, idx) => (
                                    <div key={idx} className="glass-card-interactive opacity-0">
                                        <h3 className="font-semibold text-charcoal truncate">{design.prompt || "Untitled Project"}</h3>
                                        <p className="text-[10px] font-mono text-stone-400 mt-2 font-medium">{formatDistanceToNow(new Date(design.created_at), { addSuffix: true })}</p>
                                    </div>
                                ))}
                                {designs.length === 0 && (
                                    <div className="col-span-full py-12 text-center text-xs font-mono text-stone-400 bg-stone-50/50 rounded-3xl border border-dashed border-stone-200">
                                        No configurations saved yet. <Link to="/create" className="underline font-bold text-stone-700">Start wizard</Link>
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div ref={settingsFormRef} className="max-w-2xl glass-card">
                            <h2 className="text-xl font-light text-charcoal mb-6 opacity-0">Profile Configuration</h2>
 
                            {message.text && (
                                <div className={`mb-6 p-4 rounded-xl text-xs font-mono border opacity-0 ${message.type === 'success' ? 'bg-stone-50 text-stone-700 border-stone-200' : 'bg-red-50 text-red-600 border-red-100'}`}>
                                    {message.text}
                                </div>
                            )}
 
                            <form onSubmit={handleUpdateProfile} className="space-y-6 opacity-0">
                                <div>
                                    <h3 className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3">Overview</h3>
                                    <label className="block text-xs font-bold text-stone-600 mb-2">Display Name</label>
                                    <input
                                        type="text"
                                        value={displayName}
                                        onChange={(e) => setDisplayName(e.target.value)}
                                        placeholder="Your Name"
                                        className="input-field"
                                    />
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-stone-600 mb-2">Email Address (Read-only)</label>
                                    <input
                                        type="email"
                                        value={currentUser.email}
                                        readOnly
                                        disabled
                                        className="input-field bg-stone-100/50 text-stone-400 cursor-not-allowed"
                                    />
                                </div>
                                
                                <hr className="border-stone-150 my-6" />

                                <div>
                                    <h3 className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3">Preferences</h3>
                                    <label className="block text-xs font-bold text-stone-600 mb-2">New Password (leave blank to keep current)</label>
                                    <input
                                        type="password"
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        placeholder="••••••••"
                                        className="input-field font-mono"
                                    />
                                </div>
 
                                <button type="submit" className="btn-primary">
                                    Save Changes
                                </button>
                            </form>
 
                            <hr className="my-8 border-stone-200 opacity-0" />
 
                            <div className="opacity-0">
                                <h3 className="text-red-600 font-bold text-xs uppercase tracking-wider mb-2 flex items-center gap-2">
                                    <AlertTriangle size={14} /> Danger Zone
                                </h3>
                                <p className="text-xs text-stone-500 mb-4">Once you delete your account, there is no going back. All stored layouts will be deleted permanently.</p>
                                <button
                                    onClick={(e) => { e.preventDefault(); setShowDeleteModal(true); }}
                                    className="btn-secondary border-red-200 text-red-600 hover:text-red-700 hover:bg-red-50/50"
                                >
                                    Delete Account
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
 
            {/* Delete Confirmation Modal */}
            <AnimatePresence>
                {showDeleteModal && (
                    <motion.div
                         initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                         className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50 backdrop-blur-sm"
                    >
                         <motion.div
                             initial={{ scale: 0.95 }} animate={{ scale: 1 }} exit={{ scale: 0.95 }}
                             className="glass-card max-w-md w-full shadow-2xl border border-stone-200"
                         >
                             <h3 className="text-lg font-light text-charcoal mb-3">Delete Account?</h3>
                             <p className="text-xs text-stone-500 mb-6">Are you sure you want to permanently delete your account? This action cannot be undone.</p>
                             <div className="flex gap-4 justify-end">
                                 <button className="btn-secondary" onClick={() => setShowDeleteModal(false)}>Cancel</button>
                                 <button className="btn-primary bg-red-600 hover:bg-red-700 border-red-600" onClick={handleDeleteAccount}>Yes, Delete Account</button>
                             </div>
                         </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
 };
 
 const StatCard = ({ icon, label, value }) => (
     <div className="metric-card opacity-0">
         <div className="p-3 bg-stone-50/50 text-stone-900 border border-stone-200/60 rounded-2xl mb-3 shadow-sm flex items-center justify-center">
             {React.cloneElement(icon, { size: 22 })}
         </div>
         <div className="text-3xl font-light text-stone-900 font-mono tracking-tight mb-1">{value}</div>
         <div className="text-[10px] text-stone-400 uppercase tracking-wider font-bold">{label}</div>
     </div>
 );

export default Profile;
