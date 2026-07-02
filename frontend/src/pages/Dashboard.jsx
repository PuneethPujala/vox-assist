import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    ArrowRight,
    Mic,
    Layout,
    Box,
    Sparkles,
    Cpu,
    Zap,
    Activity,
    Database,
    Layers,
    ChevronRight,
    Plus,
    Trash2,
    Download,
    Maximize2,
    Eye,
    RefreshCw,
    Play,
    Sliders,
    Text,
    FileText,
    CheckCircle2,
    Info,
    HelpCircle
} from 'lucide-react';
import { Link } from 'react-router-dom';
import toast, { Toaster } from 'react-hot-toast';

// Assets
import voxHeroImage from '../assets/vox_architectural_render.png';
import vox2DBlueprint from '../assets/vox_2d_blueprint.png';
import vox3DStructure from '../assets/vox_3d_structure.png';

const Dashboard = () => {
    // Scroll Opacity State for "Scroll to Explore"
    const [scrollOpacity, setScrollOpacity] = useState(1);

    // Hero Auto-Animation States
    const [heroPhase, setHeroPhase] = useState('typing'); // 'typing', 'loading', 'building', 'complete'
    const [heroText, setHeroText] = useState('');
    const [buildingStep, setBuildingStep] = useState(0);

    const autoPrompt = "Create a modern 3BHK layout with a 350sqft Living Room, an open Kitchen, and two Bedrooms adjacent to a Bathroom.";

    // Interactive Playground (Sandbox) State
    const [activeTab, setActiveTab] = useState('builder'); // 'builder' or 'prompt'
    const [rooms, setRooms] = useState([
        { id: 1, type: 'Living Room', area: 300 },
        { id: 2, type: 'Bedroom', area: 150 },
        { id: 3, type: 'Bathroom', area: 100 },
        { id: 4, type: 'Kitchen', area: 120 },
        { id: 5, type: 'Bedroom', area: 300 }
    ]);
    const [promptText, setPromptText] = useState("I have 2000 sqft, I want a 3bhk layout with a 400sqft living room, a kitchen adjacent to a small dining area, and a master bedroom next to a bathroom.");
    const [compileState, setCompileState] = useState('idle'); // 'idle', 'compiling', 'compiled'
    const [compileProgress, setCompileProgress] = useState(0);
    const [compileMessage, setCompileMessage] = useState('');

    // Output Panel State
    const [outputTab, setOutputTab] = useState('blueprint'); // 'blueprint' or 'structure'
    const [selectedCandidate, setSelectedCandidate] = useState('candidate-1');
    const [stats, setStats] = useState({ efficiency: 88, daylight: 91, privacy: 83, circulation: 90 });

    // SVG Donut Chart Calculation
    const totalArea = rooms.reduce((sum, r) => sum + r.area, 0);
    const radius = 38;
    const circ = 2 * Math.PI * radius; // ~238.76

    const roomColors = [
        '#f59e0b', // Amber
        '#3b82f6', // Blue
        '#ec4899', // Pink
        '#10b981', // Emerald
        '#8b5cf6', // Violet
        '#06b6d4', // Cyan
        '#f43f5e'  // Rose
    ];

    const roomTypes = ['Living Room', 'Bedroom', 'Kitchen', 'Bathroom', 'Dining Room', 'Hallway'];

    // Helper to compute room positions dynamically (Realistic House Layout matching house_3d_minimal.png)
    const computedRects = React.useMemo(() => {
        if (!rooms || rooms.length === 0) return [];

        // Distribute rooms into structural categories
        const livingRooms = rooms.filter(r => r.type === 'Living Room');
        const kitchens = rooms.filter(r => r.type === 'Kitchen');
        const bathrooms = rooms.filter(r => r.type === 'Bathroom');
        const bedrooms = rooms.filter(r => r.type.includes('Bedroom') || r.type === 'Dining Room' || r.type === 'Hallway');
        const others = rooms.filter(r => !livingRooms.includes(r) && !kitchens.includes(r) && !bathrooms.includes(r) && !bedrooms.includes(r));

        const sortedRooms = [...livingRooms, ...kitchens, ...bathrooms, ...bedrooms, ...others];
        const count = sortedRooms.length;

        const padding = 15;
        const w = 480;
        const h = 280;
        const innerW = w - 2 * padding;
        const innerH = h - 2 * padding;

        const rects = [];

        // Pastel floor colors matching house_3d_minimal.png floors
        const floorColors = [
            '#bfdbfe', // 0: Light blue (Living Room)
            '#dcfce7', // 1: Light green (Kitchen)
            '#fef9c3', // 2: Light yellow (Bedroom 1 / Top extension)
            '#f3e8ff', // 3: Light purple (Bathroom / Left bottom)
            '#e0f2fe', // 4: Light blue-teal (Bedroom 2 / Left top)
            '#fce7f3', // 5: Light pink (Bedroom 3 / Right top)
            '#ffedd5'  // 6: Light orange (Dining / Right bottom)
        ];

        if (count <= 2) {
            const splitW = innerW / 2;
            sortedRooms.forEach((room, idx) => {
                rects.push({
                    ...room,
                    x: padding + idx * splitW,
                    y: padding,
                    width: splitW,
                    height: innerH,
                    color: floorColors[idx % floorColors.length]
                });
            });
        } else if (count === 3) {
            rects.push({
                ...sortedRooms[0],
                x: padding,
                y: padding + innerH / 2,
                width: innerW,
                height: innerH / 2,
                color: floorColors[0]
            });
            rects.push({
                ...sortedRooms[1],
                x: padding,
                y: padding,
                width: innerW / 2,
                height: innerH / 2,
                color: floorColors[1]
            });
            rects.push({
                ...sortedRooms[2],
                x: padding + innerW / 2,
                y: padding,
                width: innerW / 2,
                height: innerH / 2,
                color: floorColors[2]
            });
        } else if (count === 4) {
            const rw = innerW / 2;
            const rh = innerH / 2;
            const positions = [
                { x: padding, y: padding + rh },
                { x: padding + rw, y: padding + rh },
                { x: padding, y: padding },
                { x: padding + rw, y: padding }
            ];
            sortedRooms.forEach((room, idx) => {
                rects.push({
                    ...room,
                    ...positions[idx],
                    width: rw,
                    height: rh,
                    color: floorColors[idx % floorColors.length]
                });
            });
        } else {
            // >= 5 rooms: Realistic branched house layout template matching house_3d_minimal.png
            const templates = [
                { x: 200, y: 70,  w: 80, h: 140 }, // 0: Living Room (Center corridor / Light Blue)
                { x: 200, y: 210, w: 80, h: 70 },  // 1: Kitchen (Bottom extension / Green)
                { x: 200, y: 0,   w: 80, h: 70 },  // 2: Bedroom 1 (Top extension / Yellow)
                { x: 120, y: 140, w: 80, h: 70 },  // 3: Bathroom (Left bottom / Purple)
                { x: 120, y: 70,  w: 80, h: 70 },  // 4: Bedroom 2 (Left top / Blue)
                { x: 280, y: 70,  w: 80, h: 70 },  // 5: Bedroom 3 (Right top / Pink)
                { x: 280, y: 140, w: 80, h: 70 }   // 6: Dining / Other (Right bottom / Orange)
            ];



            sortedRooms.forEach((room, idx) => {
                if (idx < templates.length) {
                    rects.push({
                        ...room,
                        x: templates[idx].x,
                        y: templates[idx].y,
                        width: templates[idx].w,
                        height: templates[idx].h,
                        color: floorColors[idx % floorColors.length]
                    });
                }
            });
        }

        return rects;
    }, [rooms]);

    const projectIso = React.useCallback((x, y, z) => {
        const scale = 0.95;
        const dx = (x - 240) * scale;
        const dy = (y - 150) * scale;
        const px = (dx - dy) * 0.866;
        const py = (dx + dy) * 0.5 - z;
        return {
            x: 300 + px,
            y: 160 + py
        };
    }, []);

    // Scroll opacity calculation
    useEffect(() => {
        const handleScroll = () => {
            const opacity = Math.max(0, 1 - window.scrollY / 180);
            setScrollOpacity(opacity);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    // Hero Loop Auto-Animation
    useEffect(() => {
        let isCancelled = false;

        const runHeroAnimation = async () => {
            while (!isCancelled) {
                // 1. Typing Phase
                setHeroPhase('typing');
                setHeroText('');
                setBuildingStep(0);

                for (let i = 0; i <= autoPrompt.length; i++) {
                    if (isCancelled) return;
                    setHeroText(autoPrompt.slice(0, i));
                    await new Promise(r => setTimeout(r, 35));
                }

                if (isCancelled) return;
                await new Promise(r => setTimeout(r, 1200));

                // 2. Loading Phase
                if (isCancelled) return;
                setHeroPhase('loading');
                await new Promise(r => setTimeout(r, 2000));

                // 3. Building Phase (Step-by-step room appearance)
                if (isCancelled) return;
                setHeroPhase('building');
                for (let step = 1; step <= 5; step++) {
                    if (isCancelled) return;
                    setBuildingStep(step);
                    await new Promise(r => setTimeout(r, 800));
                }

                // 4. Complete / Final Showcase State
                if (isCancelled) return;
                setHeroPhase('complete');
                await new Promise(r => setTimeout(r, 4000));
            }
        };

        runHeroAnimation();

        return () => {
            isCancelled = true;
        };
    }, []);

    // Handle Area Sliders
    const handleAreaChange = (id, newArea) => {
        setRooms(rooms.map(r => r.id === id ? { ...r, area: parseInt(newArea) || 50 } : r));
    };

    // Handle Room Type Dropdown
    const handleTypeChange = (id, newType) => {
        setRooms(rooms.map(r => r.id === id ? { ...r, type: newType } : r));
    };

    // Add new room
    const addRoom = () => {
        if (rooms.length >= 7) {
            toast.error("Maximum 7 rooms for the sandbox demo.");
            return;
        }
        const newId = rooms.length > 0 ? Math.max(...rooms.map(r => r.id)) + 1 : 1;
        const randomType = roomTypes[Math.floor(Math.random() * roomTypes.length)];
        setRooms([...rooms, { id: newId, type: randomType, area: 150 }]);
        toast.success(`Added a new ${randomType}!`);
    };

    // Remove room
    const removeRoom = (id) => {
        if (rooms.length <= 2) {
            toast.error("Sandbox requires at least 2 rooms to compute adjacency.");
            return;
        }
        setRooms(rooms.filter(r => r.id !== id));
    };

    // Prompt templates
    const applyTemplate = (text) => {
        setPromptText(text);
        toast.success("Prompt template loaded!");
    };

    // Run compile layout simulation
    const handleCompile = () => {
        setCompileState('compiling');
        setCompileProgress(0);
        setCompileMessage('Extracting room constraints...');

        const messages = [
            { t: 0, m: 'Initializing local LLM parsing pipeline...' },
            { t: 600, m: 'Ollama parsed 5 room nodes and 4 adjacency relations.' },
            { t: 1200, m: 'Executing vox-architect floorplan reasoning solver...' },
            { t: 1800, m: 'Generating wall structural volumes and partitions...' },
            { t: 2200, m: 'Compiling 3D mesh plane & CAD files...' },
            { t: 2500, m: 'Compilation complete!' }
        ];

        messages.forEach(step => {
            setTimeout(() => {
                setCompileMessage(step.m);
                setCompileProgress(prev => Math.min(prev + 20, 100));
            }, step.t);
        });

        setTimeout(() => {
            setCompileState('compiled');
            setCompileProgress(100);

            const variance = Math.floor(Math.random() * 6) - 3; // -3 to +3
            setStats({
                efficiency: Math.min(96, Math.max(80, 88 + variance)),
                daylight: Math.min(98, Math.max(82, 91 - variance)),
                privacy: Math.min(95, Math.max(75, 83 + Math.floor(variance / 2))),
                circulation: Math.min(97, Math.max(84, 90 + Math.floor(variance * 1.5)))
            });

            toast.success("Floorplan generated successfully!");
        }, 2600);
    };

    const handleReset = () => {
        setCompileState('idle');
        setCompileProgress(0);
        setCompileMessage('');
    };

    const handleDownloadWarning = (type) => {
        toast((t) => (
            <div className="flex flex-col gap-2.5">
                <p className="text-sm font-medium text-stone-900 font-['Plus_Jakarta_Sans']">
                    <strong>Sandbox Preview Only</strong> <br />
                    To download the full {type} and custom CAD data, you need to sign in and run a project.
                </p>
                <div className="flex gap-2">
                    <Link
                        to="/login"
                        onClick={() => toast.dismiss(t.id)}
                        className="px-3 py-1.5 bg-charcoal text-cream text-xs font-semibold rounded-lg hover:bg-stone-850 text-center flex-1 font-['Plus_Jakarta_Sans']"
                    >
                        Sign In
                    </Link>
                    <button
                        onClick={() => toast.dismiss(t.id)}
                        className="px-3 py-1.5 border border-stone-200 text-stone-600 text-xs font-semibold rounded-lg hover:bg-stone-50 flex-1 font-['Plus_Jakarta_Sans']"
                    >
                        Close
                    </button>
                </div>
            </div>
        ), {
            duration: 5000,
            position: 'bottom-center'
        });
    };

    return (
        <div className="min-h-screen bg-cream text-charcoal overflow-x-hidden selection:bg-stone-200 font-['Plus_Jakarta_Sans']">
            <Toaster />

            {/* Custom Google Fonts Import & CSS keyframes */}
            <style>{`
                @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
                
                @keyframes scan {
                    0% { top: 0%; opacity: 0.8; }
                    50% { top: 100%; opacity: 0.8; }
                    100% { top: 0%; opacity: 0.8; }
                }
                .scanline {
                    animation: scan 4s linear infinite;
                }
                @keyframes pulse-slow {
                    0%, 100% { opacity: 0.2; }
                    50% { opacity: 0.4; }
                }
                .pulse-slow {
                    animation: pulse-slow 3s ease-in-out infinite;
                }
            `}</style>

            {/* Redesigned Hero Section (Split View, Typewriter & Built-out layout preview) */}
            <div className="relative h-screen min-h-[650px] flex items-center justify-center pt-24 pb-16 px-4 md:px-8 overflow-hidden">
                {/* Background ambient lighting */}
                <div className="absolute top-1/3 left-1/3 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-gradient-to-tr from-amber-100/30 via-orange-100/10 to-stone-150/30 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-indigo-50/10 rounded-full blur-3xl pointer-events-none" />

                <div className="max-w-7xl w-full mx-auto grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center relative z-10">

                    {/* LEFT COLUMN: HERO TEXT */}
                    <div className="lg:col-span-5 flex flex-col items-start text-left">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-stone-100 text-stone-700 mb-6 tracking-wide uppercase border border-stone-200/50 shadow-sm select-none">
                            <Sparkles size={12} className="text-amber-500 animate-pulse" /> AI Architectural Compiler
                        </span>

                        <h1 className="text-4xl sm:text-5xl md:text-6xl font-light text-charcoal mb-6 tracking-tight leading-[1.12] font-['Space_Grotesk']">
                            Architectural Intelligence <br />
                            <span className="font-semibold bg-gradient-to-r from-stone-900 via-stone-800 to-amber-700 bg-clip-text text-transparent">
                                Generated Instantly.
                            </span>
                        </h1>

                        <p className="text-base md:text-lg text-stone-500 mb-10 leading-relaxed font-light max-w-xl">
                            VoxAssist converts conversational spatial descriptions into precise 2D blueprints and clean 3D structure wireframes in seconds. No manual CAD drafts needed.
                        </p>

                        <div className="flex flex-col sm:flex-row gap-4 w-full sm:w-auto">
                            <Link
                                to="/create"
                                className="inline-flex items-center justify-center px-8 py-4 bg-charcoal text-cream rounded-full text-base font-semibold hover:bg-stone-850 transition-all duration-300 hover:scale-[1.03] shadow-lg group"
                            >
                                Start Creating <ArrowRight className="ml-2 group-hover:translate-x-1 transition-transform" size={18} />
                            </Link>
                            <a
                                href="#sandbox"
                                className="inline-flex items-center justify-center px-8 py-4 bg-white/80 backdrop-blur-sm text-charcoal border border-stone-200 rounded-full text-base font-medium hover:bg-stone-50 transition-all duration-300"
                            >
                                Try Interactive Sandbox
                            </a>
                        </div>
                    </div>

                    {/* RIGHT COLUMN: INTERACTIVE ANIMATION PANEL */}
                    <div className="lg:col-span-7 w-full flex items-center justify-center">
                        <div className="w-full bg-stone-950/95 border border-stone-800/80 rounded-3xl p-1.5 shadow-2xl relative overflow-hidden aspect-[4/3] flex flex-col justify-between font-mono text-xs">
                            {/* Browser Bar */}
                            <div className="flex items-center justify-between px-4 py-2.5 bg-stone-900/80 border-b border-stone-850 rounded-t-2xl">
                                <div className="flex items-center gap-1.5">
                                    <div className="w-2.5 h-2.5 rounded-full bg-red-500/60" />
                                    <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/60" />
                                    <div className="w-2.5 h-2.5 rounded-full bg-green-500/60" />
                                </div>
                                <div className="px-6 py-0.5 bg-stone-950/80 border border-stone-800/40 rounded text-[9px] text-stone-500 tracking-wider font-mono">
                                    vox-compiler-terminal.log
                                </div>
                                <div className="w-8" />
                            </div>

                            {/* Main Screen */}
                            <div className="flex-1 p-5 relative flex flex-col justify-between overflow-hidden bg-stone-950/40">
                                {/* State: Typing */}
                                {heroPhase === 'typing' && (
                                    <div className="flex-1 flex flex-col gap-3">
                                        <div className="flex items-center gap-2 text-stone-500">
                                            <span className="text-emerald-500">$</span>
                                            <span>voxassist --compile</span>
                                        </div>
                                        <div className="text-white leading-relaxed text-sm font-light select-none">
                                            {heroText}
                                            <span className="w-1.5 h-4 bg-emerald-400 inline-block animate-pulse ml-0.5" />
                                        </div>
                                    </div>
                                )}

                                {/* State: Loading */}
                                {heroPhase === 'loading' && (
                                    <div className="flex-1 flex flex-col items-center justify-center text-center gap-4 relative">
                                        <div className="relative w-16 h-16 flex items-center justify-center">
                                            <div className="absolute inset-0 border border-amber-500/20 rounded-full" />
                                            <div className="absolute inset-0 border-t-2 border-amber-500 rounded-full animate-spin" style={{ animationDuration: '0.8s' }} />
                                            <Cpu size={24} className="text-amber-500 animate-pulse" />
                                        </div>
                                        <div className="flex flex-col gap-1">
                                            <span className="text-xs font-bold text-white font-mono uppercase tracking-wider">Parsing Relational Logic</span>
                                            <span className="text-[10px] text-amber-500 font-mono animate-pulse">Running Adjacency Solvers...</span>
                                        </div>
                                    </div>
                                )}

                                {/* State: Building & Complete */}
                                {(heroPhase === 'building' || heroPhase === 'complete') && (
                                    <div className="flex-1 flex flex-col gap-4">
                                        <div className="flex items-center justify-between border-b border-stone-850 pb-2 text-[10px] text-stone-400">
                                            <span className="flex items-center gap-1 font-mono">
                                                <Activity size={10} className="text-emerald-500 animate-pulse" /> Floorplan Compilation (Draft Candidates)
                                            </span>
                                            {heroPhase === 'complete' ? (
                                                <span className="text-emerald-400 font-bold flex items-center gap-0.5 font-mono">
                                                    <CheckCircle2 size={10} /> DONE
                                                </span>
                                            ) : (
                                                <span className="text-amber-500 animate-pulse font-mono">BUILDING ROOMS...</span>
                                            )}
                                        </div>

                                        {/* Dynamic SVG Blueprint Canvas */}
                                        <div className="flex-1 relative border border-stone-850 rounded-xl overflow-hidden bg-stone-900/30 flex items-center justify-center p-3">
                                            <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: 'linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)', backgroundSize: '16px 16px' }} />

                                            <svg viewBox="0 0 400 240" className="w-full h-full">
                                                <AnimatePresence>
                                                    {/* Room 1: Living Room */}
                                                    {buildingStep >= 1 && (
                                                        <motion.g initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                                                            <rect x="20" y="20" width="210" height="110" rx="6" fill="#f59e0b" fillOpacity="0.15" stroke="#f59e0b" strokeWidth="1.5" />
                                                            <text x="125" y="70" fill="#f59e0b" fontSize="9" fontWeight="bold" textAnchor="middle" fontFamily="monospace">Living Room</text>
                                                            <text x="125" y="85" fill="#f59e0b" fontSize="8" fillOpacity="0.7" textAnchor="middle" fontFamily="monospace">350 sqft</text>
                                                        </motion.g>
                                                    )}

                                                    {/* Room 2: Kitchen */}
                                                    {buildingStep >= 2 && (
                                                        <motion.g initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                                                            <rect x="240" y="20" width="140" height="65" rx="6" fill="#10b981" fillOpacity="0.15" stroke="#10b981" strokeWidth="1.5" />
                                                            <text x="310" y="50" fill="#10b981" fontSize="9" fontWeight="bold" textAnchor="middle" fontFamily="monospace">Kitchen</text>
                                                            <text x="310" y="63" fill="#10b981" fontSize="8" fillOpacity="0.7" textAnchor="middle" fontFamily="monospace">150 sqft</text>
                                                        </motion.g>
                                                    )}

                                                    {/* Room 3: Bedroom 1 */}
                                                    {buildingStep >= 3 && (
                                                        <motion.g initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                                                            <rect x="20" y="140" width="210" height="80" rx="6" fill="#3b82f6" fillOpacity="0.15" stroke="#3b82f6" strokeWidth="1.5" />
                                                            <text x="125" y="175" fill="#3b82f6" fontSize="9" fontWeight="bold" textAnchor="middle" fontFamily="monospace">Bedroom 1</text>
                                                            <text x="125" y="190" fill="#3b82f6" fontSize="8" fillOpacity="0.7" textAnchor="middle" fontFamily="monospace">250 sqft</text>
                                                        </motion.g>
                                                    )}

                                                    {/* Room 4: Bedroom 2 */}
                                                    {buildingStep >= 4 && (
                                                        <motion.g initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                                                            <rect x="240" y="140" width="140" height="80" rx="6" fill="#ec4899" fillOpacity="0.15" stroke="#ec4899" strokeWidth="1.5" />
                                                            <text x="310" y="175" fill="#ec4899" fontSize="9" fontWeight="bold" textAnchor="middle" fontFamily="monospace">Bedroom 2</text>
                                                            <text x="310" y="190" fill="#ec4899" fontSize="8" fillOpacity="0.7" textAnchor="middle" fontFamily="monospace">200 sqft</text>
                                                        </motion.g>
                                                    )}

                                                    {/* Room 5: Bathroom */}
                                                    {buildingStep >= 5 && (
                                                        <motion.g initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}>
                                                            <rect x="240" y="95" width="140" height="35" rx="6" fill="#8b5cf6" fillOpacity="0.15" stroke="#8b5cf6" strokeWidth="1.5" />
                                                            <text x="310" y="116" fill="#8b5cf6" fontSize="8" fontWeight="bold" textAnchor="middle" fontFamily="monospace">Bathroom (100 sqft)</text>
                                                        </motion.g>
                                                    )}

                                                    {/* Outer wall outline in complete state */}
                                                    {heroPhase === 'complete' && (
                                                        <motion.g initial={{ opacity: 0 }} animate={{ opacity: 0.8 }} exit={{ opacity: 0 }}>
                                                            <rect x="16" y="16" width="368" height="208" rx="8" fill="none" stroke="#6b7280" strokeWidth="2.5" strokeDasharray="30 10 20 10" />
                                                        </motion.g>
                                                    )}
                                                </AnimatePresence>
                                            </svg>
                                        </div>
                                    </div>
                                )}
                            </div>

                            {/* Terminal Footer */}
                            <div className="px-4 py-2 border-t border-stone-850 bg-stone-900/60 rounded-b-2xl flex items-center justify-between text-[9px] text-stone-500 font-mono select-none">
                                <span>Compiler candidates: 3 compiled</span>
                                <span>Efficiency: 92%</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Bouncing Scroll-to-Explore Indicator (Fades out dynamically on scroll) */}
                <div
                    className="absolute bottom-6 left-1/2 -translate-x-1/2 flex flex-col items-center gap-1.5 transition-opacity duration-300 pointer-events-none select-none"
                    style={{ opacity: scrollOpacity }}
                >
                    <span className="text-[10px] uppercase tracking-[0.2em] font-semibold text-stone-400">
                        Scroll to Explore
                    </span>
                    <motion.div
                        animate={{ y: [0, 6, 0] }}
                        transition={{ repeat: Infinity, duration: 1.5 }}
                        className="text-stone-400"
                    >
                        <ChevronRight size={16} className="rotate-90" />
                    </motion.div>
                </div>
            </div>

            {/* Removed Tech Stack badges */}

            {/* Interactive Sandbox Playground */}
            <div id="sandbox" className="py-20 px-4 max-w-7xl mx-auto relative z-25 scroll-mt-20">
                <div className="text-center mb-12">
                    <h2 className="text-3xl md:text-5xl font-light text-charcoal tracking-tight mb-3">
                        Interactive <span className="font-semibold">Design Sandbox</span>
                    </h2>
                    <p className="text-stone-500 max-w-xl mx-auto font-light">
                        Test the generator layout engine. Configure your rooms or write a prompt below, then hit compile to build your structural layout.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                    {/* LEFT PANEL - CONFIGURATOR */}
                    <div className="lg:col-span-5 bg-white/80 border border-stone-200/60 rounded-3xl p-6 shadow-xl relative backdrop-blur-md flex flex-col gap-6">
                        <div className="flex items-center justify-between border-b border-stone-100 pb-4">
                            <div className="flex items-center gap-2">
                                <Sliders size={18} className="text-stone-600" />
                                <h3 className="font-semibold text-stone-900 text-lg">Configurator Wizard</h3>
                            </div>
                            <span className="px-2.5 py-1 text-[10px] font-semibold text-amber-700 bg-amber-50 rounded-full uppercase tracking-wider">
                                Demo Mode
                            </span>
                        </div>

                        {/* Configurator Mode Tabs */}
                        <div className="grid grid-cols-2 p-1 bg-stone-100 rounded-xl">
                            <button
                                onClick={() => { setActiveTab('builder'); handleReset(); }}
                                className={`py-2 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1.5 ${activeTab === 'builder' ? 'bg-white text-charcoal shadow-sm' : 'text-stone-500 hover:text-stone-900'
                                    }`}
                            >
                                <Layout size={14} /> Room Builder
                            </button>
                            <button
                                onClick={() => { setActiveTab('prompt'); handleReset(); }}
                                className={`py-2 text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-1.5 ${activeTab === 'prompt' ? 'bg-white text-charcoal shadow-sm' : 'text-stone-500 hover:text-stone-900'
                                    }`}
                            >
                                <Text size={14} /> Text Prompt
                            </button>
                        </div>

                        {/* Room Builder View */}
                        {activeTab === 'builder' && (
                            <div className="flex flex-col gap-5">
                                {/* SVG Donut and Total Info */}
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center bg-stone-50 p-4 rounded-2xl border border-stone-150">
                                    <div className="flex justify-center relative">
                                        <svg width="110" height="110" viewBox="0 0 100 100">
                                            <circle cx="50" cy="50" r={radius} fill="transparent" stroke="#e5e7eb" strokeWidth="8" />
                                            {(() => {
                                                let accumulatedPercent = 0;
                                                return rooms.map((room, idx) => {
                                                    const strokeDasharray = `${(room.area / totalArea) * circ} ${circ}`;
                                                    const strokeDashoffset = -accumulatedPercent * circ;
                                                    accumulatedPercent += room.area / totalArea;
                                                    return (
                                                        <circle
                                                            key={room.id}
                                                            cx="50"
                                                            cy="50"
                                                            r={radius}
                                                            fill="transparent"
                                                            stroke={roomColors[idx % roomColors.length]}
                                                            strokeWidth="8"
                                                            strokeDasharray={strokeDasharray}
                                                            strokeDashoffset={strokeDashoffset}
                                                            transform="rotate(-90 50 50)"
                                                            className="transition-all duration-500 ease-out"
                                                        />
                                                    );
                                                });
                                            })()}
                                        </svg>
                                        <div className="absolute inset-0 flex flex-col items-center justify-center">
                                            <span className="text-[10px] text-stone-400 font-semibold uppercase tracking-wider">Total</span>
                                            <span className="text-base font-bold text-stone-900 font-mono">{totalArea}</span>
                                            <span className="text-[9px] text-stone-400">sqft</span>
                                        </div>
                                    </div>

                                    <div className="flex flex-col gap-1.5">
                                        <span className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Area Distribution</span>
                                        <div className="flex flex-wrap gap-1.5 max-h-[80px] overflow-y-auto pr-1">
                                            {rooms.map((room, idx) => (
                                                <span
                                                    key={room.id}
                                                    className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border border-stone-200/50 bg-white shadow-sm font-medium"
                                                >
                                                    <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: roomColors[idx % roomColors.length] }} />
                                                    {room.type}: {room.area}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                {/* Room Slider List */}
                                <div className="flex flex-col gap-3 max-h-[260px] overflow-y-auto pr-1">
                                    {rooms.map((room, idx) => (
                                        <div
                                            key={room.id}
                                            className="flex flex-col gap-1.5 p-3.5 bg-white border border-stone-150 rounded-xl shadow-sm hover:border-stone-300 transition-colors"
                                        >
                                            <div className="flex items-center justify-between gap-2">
                                                <div className="flex items-center gap-1.5">
                                                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: roomColors[idx % roomColors.length] }} />
                                                    <select
                                                        value={room.type}
                                                        onChange={(e) => handleTypeChange(room.id, e.target.value)}
                                                        className="text-xs font-semibold text-stone-800 bg-stone-50 hover:bg-stone-100 border border-stone-200 px-2 py-1 rounded-md focus:outline-none focus:ring-1 focus:ring-stone-400 min-w-[125px]"
                                                    >
                                                        {roomTypes.map(type => (
                                                            <option key={type} value={type}>{type}</option>
                                                        ))}
                                                    </select>
                                                </div>

                                                <div className="flex items-center gap-2">
                                                    <span className="text-xs font-bold text-stone-700 font-mono w-14 text-right">
                                                        {room.area} <span className="font-light text-[10px] text-stone-400">sqft</span>
                                                    </span>
                                                    <button
                                                        onClick={() => removeRoom(room.id)}
                                                        className="text-stone-400 hover:text-red-500 p-1 rounded-md hover:bg-red-50 transition-colors"
                                                    >
                                                        <Trash2 size={13} />
                                                    </button>
                                                </div>
                                            </div>

                                            <input
                                                type="range"
                                                min="50"
                                                max="500"
                                                step="10"
                                                value={room.area}
                                                onChange={(e) => handleAreaChange(room.id, e.target.value)}
                                                className="w-full accent-charcoal cursor-pointer h-1.5 bg-stone-100 rounded-lg appearance-none"
                                            />
                                        </div>
                                    ))}
                                </div>

                                <button
                                    onClick={addRoom}
                                    className="w-full py-2.5 border border-dashed border-stone-300 hover:border-stone-500 rounded-xl text-xs font-medium text-stone-600 hover:text-stone-900 transition-colors flex items-center justify-center gap-1"
                                >
                                    <Plus size={14} /> Add Custom Room
                                </button>
                            </div>
                        )}

                        {/* Text Prompt View */}
                        {activeTab === 'prompt' && (
                            <div className="flex flex-col gap-4">
                                <div className="flex flex-col gap-1.5">
                                    <label className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Describe Your Layout Constraints</label>
                                    <textarea
                                        value={promptText}
                                        onChange={(e) => setPromptText(e.target.value)}
                                        rows="4"
                                        placeholder="Describe details, rooms, adjacencies, and total square footage..."
                                        className="w-full border border-stone-200 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-stone-400 resize-none font-light leading-relaxed bg-stone-50/50"
                                    />
                                </div>

                                <div className="flex flex-col gap-2">
                                    <span className="text-[10px] font-semibold text-stone-400 uppercase tracking-wider">Or Use Presets:</span>
                                    <div className="flex flex-wrap gap-2">
                                        <button
                                            onClick={() => applyTemplate("I have 1000sqft, I want a 2bhk layout with a 300sqft Living Room, 150sqft Bedroom, 120sqft Kitchen and a small Bathroom next to the bedroom.")}
                                            className="px-2.5 py-1 text-xs bg-stone-50 hover:bg-stone-100 border border-stone-200 text-stone-700 rounded-lg transition-colors font-medium"
                                        >
                                            2BHK Layout
                                        </button>
                                        <button
                                            onClick={() => applyTemplate("I have 600sqft, open-concept studio space, large kitchen partition, private bathroom, and plenty of natural daylight.")}
                                            className="px-2.5 py-1 text-xs bg-stone-50 hover:bg-stone-100 border border-stone-200 text-stone-700 rounded-lg transition-colors font-medium"
                                        >
                                            Studio Layout
                                        </button>
                                        <button
                                            onClick={() => applyTemplate("I have 1500sqft, 3 rooms, large living area, open kitchen space, and bedrooms sharing a wall with the bathroom.")}
                                            className="px-2.5 py-1 text-xs bg-stone-50 hover:bg-stone-100 border border-stone-200 text-stone-700 rounded-lg transition-colors font-medium"
                                        >
                                            Cabin Structure
                                        </button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Compilation Button Trigger */}
                        <div className="pt-2 border-t border-stone-100">
                            {compileState === 'idle' && (
                                <button
                                    onClick={handleCompile}
                                    className="w-full py-4 bg-charcoal text-cream font-semibold rounded-2xl hover:bg-stone-850 hover:shadow-lg transition-all flex items-center justify-center gap-2 group text-sm shadow-md"
                                >
                                    <Play size={15} fill="currentColor" className="group-hover:scale-110 transition-transform" /> Compile Layout Draft
                                </button>
                            )}

                            {compileState === 'compiling' && (
                                <div className="w-full p-4 bg-stone-50 rounded-2xl border border-stone-200 flex flex-col gap-3">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="font-semibold text-stone-700 flex items-center gap-1.5">
                                            <RefreshCw size={12} className="animate-spin text-charcoal" /> {compileMessage}
                                        </span>
                                        <span className="font-mono font-bold text-stone-900">{compileProgress}%</span>
                                    </div>
                                    <div className="w-full bg-stone-200 h-1.5 rounded-full overflow-hidden">
                                        <div
                                            className="bg-charcoal h-full rounded-full transition-all duration-300"
                                            style={{ width: `${compileProgress}%` }}
                                        />
                                    </div>
                                </div>
                            )}

                            {compileState === 'compiled' && (
                                <button
                                    onClick={handleReset}
                                    className="w-full py-3.5 border border-stone-300 hover:border-stone-850 text-stone-700 hover:text-stone-950 font-semibold rounded-2xl transition-all flex items-center justify-center gap-2 text-sm"
                                >
                                    <RefreshCw size={14} /> Adjust Config & Reset Sandbox
                                </button>
                            )}
                        </div>
                    </div>

                    {/* RIGHT PANEL - LIVE VISUALIZATION */}
                    <div className="lg:col-span-7 bg-white/60 border border-stone-200/40 rounded-3xl shadow-xl overflow-hidden min-h-[520px] flex flex-col justify-between backdrop-blur-sm relative animate-fade-in">
                        {/* Blueprint grid background */}
                        <div
                            className="absolute inset-0 opacity-[0.03] pointer-events-none"
                            style={{
                                backgroundImage: 'radial-gradient(#000 1px, transparent 1px), linear-gradient(to right, #000 1px, transparent 1px), linear-gradient(to bottom, #000 1px, transparent 1px)',
                                backgroundSize: '24px 24px'
                            }}
                        />

                        {/* BEFORE COMPILATION (IDLE STATE) */}
                        {compileState === 'idle' && (
                            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 relative z-10">
                                <div className="w-16 h-16 bg-stone-100 border border-stone-200 rounded-2xl flex items-center justify-center text-stone-500 mb-6 shadow-sm relative overflow-hidden group">
                                    <Layout size={30} className="relative z-10 text-stone-600" />
                                    <div className="absolute inset-0 bg-stone-200/50 pulse-slow" />
                                </div>
                                <h4 className="text-xl font-semibold text-stone-900 mb-2">Design Canvas Sandbox</h4>
                                <p className="text-sm text-stone-500 max-w-sm font-light leading-relaxed">
                                    Configure your rooms or text description in the wizard, then click **Compile Layout Draft** to see the 2D layout and 3D structural model.
                                </p>
                            </div>
                        )}

                        {/* DURING COMPILATION (LOADING STATE) */}
                        {compileState === 'compiling' && (
                            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 relative z-10 overflow-hidden bg-stone-950">
                                {/* Glowing Scanning laser line */}
                                <div className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-cyan-400 to-transparent shadow-[0_0_8px_rgba(34,211,238,0.8)] scanline" />

                                {/* Scanning grid overlay */}
                                <div
                                    className="absolute inset-0 opacity-[0.15]"
                                    style={{
                                        backgroundImage: 'linear-gradient(to right, #06b6d4 1px, transparent 1px), linear-gradient(to bottom, #06b6d4 1px, transparent 1px)',
                                        backgroundSize: '20px 20px'
                                    }}
                                />

                                <div className="w-16 h-16 rounded-full border border-cyan-500/30 flex items-center justify-center mb-6 animate-pulse relative">
                                    <Cpu size={28} className="text-cyan-400 animate-spin" style={{ animationDuration: '6s' }} />
                                    <div className="absolute inset-0 bg-cyan-500/10 rounded-full blur-md" />
                                </div>
                                <h4 className="text-xl font-bold text-white mb-2 tracking-wide font-mono">COMPILING SPATIAL LAYOUT</h4>
                                <p className="text-xs text-cyan-400 font-mono tracking-widest uppercase animate-pulse">
                                    {compileMessage}
                                </p>
                            </div>
                        )}

                        {/* AFTER COMPILATION (COMPILED OUTPUT STATE) */}
                        {compileState === 'compiled' && (
                            <div className="flex-1 flex flex-col relative z-10">
                                {/* Navigation and Tab Selector */}
                                <div className="flex flex-wrap items-center justify-between border-b border-stone-150 p-4 bg-white/40 gap-4">
                                    <div className="flex items-center gap-1.5 p-1 bg-stone-100 rounded-lg">
                                        <button
                                            onClick={() => setOutputTab('blueprint')}
                                            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${outputTab === 'blueprint' ? 'bg-white text-charcoal shadow-sm' : 'text-stone-500 hover:text-stone-900'
                                                }`}
                                        >
                                            2D Blueprint
                                        </button>
                                        <button
                                            onClick={() => setOutputTab('structure')}
                                            className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-colors ${outputTab === 'structure' ? 'bg-white text-charcoal shadow-sm' : 'text-stone-500 hover:text-stone-900'
                                                }`}
                                        >
                                            3D Structure
                                        </button>
                                    </div>

                                    <div className="flex gap-2">
                                        <button
                                            onClick={() => handleDownloadWarning('2D PDF Blueprint')}
                                            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold bg-white border border-stone-200 hover:bg-stone-50 rounded-lg shadow-sm transition-colors text-stone-700"
                                        >
                                            <FileText size={13} /> Export PDF
                                        </button>
                                        <button
                                            onClick={() => handleDownloadWarning('3D STL Mesh')}
                                            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold bg-charcoal text-cream hover:bg-stone-850 rounded-lg shadow-sm transition-colors"
                                        >
                                            <Box size={13} /> Export STL
                                        </button>
                                    </div>
                                </div>

                                {/* Content Canvas */}
                                <div className="flex-1 min-h-[300px] flex items-center justify-center p-6 bg-stone-50 relative group">
                                     {outputTab === 'blueprint' ? (
                                        <div className="relative w-full h-full max-h-[340px] flex items-center justify-center overflow-hidden rounded-xl border border-stone-200 bg-stone-50 p-2">
                                            {/* Dynamic SVG Blueprint Canvas */}
                                            <svg viewBox="0 0 480 280" className="w-full h-full object-contain">
                                                {/* Grid Background */}
                                                <defs>
                                                    <pattern id="blueprint-grid" width="20" height="20" patternUnits="userSpaceOnUse">
                                                        <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(0, 0, 0, 0.03)" strokeWidth="1" />
                                                    </pattern>
                                                </defs>
                                                <rect width="100%" height="100%" fill="#fafaf9" />
                                                <rect width="100%" height="100%" fill="url(#blueprint-grid)" />

                                                {/* Rooms */}
                                                {computedRects.map((room) => (
                                                    <g key={room.id}>
                                                        {/* Filled area */}
                                                        <rect
                                                            x={room.x}
                                                            y={room.y}
                                                            width={room.width}
                                                            height={room.height}
                                                            fill={room.color}
                                                            fillOpacity="0.45"
                                                            stroke="#1c1917"
                                                            strokeWidth="3.5"
                                                        />
                                                        {/* Inner blueprint outline border */}
                                                        <rect
                                                            x={room.x + 2}
                                                            y={room.y + 2}
                                                            width={room.width - 4}
                                                            height={room.height - 4}
                                                            fill="none"
                                                            stroke="#000000"
                                                            strokeWidth="0.75"
                                                            strokeOpacity="0.15"
                                                            strokeDasharray="3 2"
                                                        />
                                                        
                                                        {/* Draw windows on outer walls */}
                                                        {/* Left Wall Window */}
                                                        {room.x === 120 && (
                                                            <g>
                                                                <line x1={room.x} y1={room.y + room.height/2 - 12} x2={room.x} y2={room.y + room.height/2 + 12} stroke="#0ea5e9" strokeWidth="2.5" />
                                                                <line x1={room.x} y1={room.y + room.height/2 - 12} x2={room.x} y2={room.y + room.height/2 + 12} stroke="#ffffff" strokeWidth="1" />
                                                            </g>
                                                        )}
                                                        {/* Right Wall Window */}
                                                        {Math.abs(room.x + room.width - 360) < 1 && (
                                                            <g>
                                                                <line x1={room.x + room.width} y1={room.y + room.height/2 - 12} x2={room.x + room.width} y2={room.y + room.height/2 + 12} stroke="#0ea5e9" strokeWidth="2.5" />
                                                                <line x1={room.x + room.width} y1={room.y + room.height/2 - 12} x2={room.x + room.width} y2={room.y + room.height/2 + 12} stroke="#ffffff" strokeWidth="1" />
                                                            </g>
                                                        )}
                                                        {/* Top Wall Window */}
                                                        {(room.y === 0 || room.y === 70) && room.type !== 'Living Room' && (
                                                            <g>
                                                                <line x1={room.x + room.width/2 - 12} y1={room.y} x2={room.x + room.width/2 + 12} y2={room.y} stroke="#0ea5e9" strokeWidth="2.5" />
                                                                <line x1={room.x + room.width/2 - 12} y1={room.y} x2={room.x + room.width/2 + 12} y2={room.y} stroke="#ffffff" strokeWidth="1" />
                                                            </g>
                                                        )}
                                                        {/* Bottom Wall Window */}
                                                        {(Math.abs(room.y + room.height - 280) < 1 || Math.abs(room.y + room.height - 210) < 1) && room.type !== 'Living Room' && (
                                                            <g>
                                                                <line x1={room.x + room.width/2 - 12} y1={room.y + room.height} x2={room.x + room.width/2 + 12} y2={room.y + room.height} stroke="#0ea5e9" strokeWidth="2.5" />
                                                                <line x1={room.x + room.width/2 - 12} y1={room.y + room.height} x2={room.x + room.width/2 + 12} y2={room.y + room.height} stroke="#ffffff" strokeWidth="1" />
                                                            </g>
                                                        )}

                                                        {/* Room details text inside SVG */}
                                                        <text
                                                            x={room.x + room.width / 2}
                                                            y={room.y + room.height / 2 - 4}
                                                            textAnchor="middle"
                                                            fill="#1c1917"
                                                            fontSize="8.5"
                                                            fontWeight="bold"
                                                            fontFamily="monospace"
                                                            letterSpacing="0.05em"
                                                        >
                                                            {room.type.toUpperCase()}
                                                        </text>
                                                        <text
                                                            x={room.x + room.width / 2}
                                                            y={room.y + room.height / 2 + 8}
                                                            textAnchor="middle"
                                                            fill="#0369a1"
                                                            fontSize="7"
                                                            fontWeight="bold"
                                                            fontFamily="monospace"
                                                        >
                                                            {room.area} SQFT
                                                        </text>
                                                    </g>
                                                ))}

                                                {/* Door swings for horizontal partitions */}
                                                {computedRects.map((room) => {
                                                    const nextRoom = computedRects.find(r => r.x === room.x && Math.abs(r.y - (room.y + room.height)) < 1);
                                                    if (nextRoom) {
                                                        const doorX = room.x + room.width / 3;
                                                        const doorW = 16;
                                                        return (
                                                            <g key={`door-h-${room.id}`}>
                                                                <line x1={doorX} y1={room.y + room.height} x2={doorX + doorW} y2={room.y + room.height} stroke="#fafaf9" strokeWidth="4.5" />
                                                                <line x1={doorX} y1={room.y + room.height} x2={doorX} y2={room.y + room.height - doorW} stroke="#44403c" strokeWidth="1.5" />
                                                                <path d={`M ${doorX} ${room.y + room.height - doorW} A ${doorW} ${doorW} 0 0 1 ${doorX + doorW} ${room.y + room.height}`} fill="none" stroke="#78716c" strokeWidth="1" strokeDasharray="2 2" />
                                                            </g>
                                                        );
                                                    }
                                                    return null;
                                                })}

                                                {/* Door swing connecting left column to center corridor */}
                                                {(() => {
                                                    const leftCol = computedRects.filter(r => r.x === 120);
                                                    const hasCenter = computedRects.some(r => r.x === 200);
                                                    if (leftCol.length > 0 && hasCenter) {
                                                        const doorX = 200;
                                                        const doorY = 140;
                                                        const doorW = 16;
                                                        return (
                                                            <g key="door-v-main">
                                                                <line x1={doorX} y1={doorY - doorW/2} x2={doorX} y2={doorY + doorW/2} stroke="#fafaf9" strokeWidth="4.5" />
                                                                <line x1={doorX} y1={doorY - doorW/2} x2={doorX - doorW} y2={doorY - doorW/2} stroke="#44403c" strokeWidth="1.5" />
                                                                <path d={`M ${doorX - doorW} ${doorY - doorW/2} A ${doorW} ${doorW} 0 0 1 ${doorX} ${doorY + doorW/2}`} fill="none" stroke="#78716c" strokeWidth="1" strokeDasharray="2 2" />
                                                            </g>
                                                        );
                                                    }
                                                    return null;
                                                })()}
                                            </svg>
                                        </div>
                                    ) : (
                                        <div className="relative w-full h-full max-h-[340px] flex flex-col items-center justify-center rounded-xl overflow-hidden border border-stone-200 bg-stone-50 p-2">
                                            {/* Dynamic Isometric Cardboard House Model SVG */}
                                            <svg viewBox="0 0 600 350" className="w-full h-full object-contain">
                                                <rect width="100%" height="100%" fill="#f5f5f4" />
                                                
                                                {/* Ground Bounding Lines matching house_3d_minimal.png */}
                                                <line x1="60" y1="240" x2="380" y2="340" stroke="#a8a29e" strokeWidth="1.2" />
                                                <line x1="380" y1="340" x2="580" y2="180" stroke="#a8a29e" strokeWidth="1.2" />

                                                {/* Painter's algorithm sort for correct layering (back to front) */}
                                                {(() => {
                                                    const sortedForIso = [...computedRects].sort((a, b) => (a.x + a.y) - (b.x + b.y));
                                                    
                                                    return sortedForIso.map((room) => {
                                                        const wallH = 26; // Isometric Wall Height
                                                        
                                                        // 2D Corners
                                                        const p0 = { x: room.x, y: room.y };
                                                        const p1 = { x: room.x + room.width, y: room.y };
                                                        const p2 = { x: room.x + room.width, y: room.y + room.height };
                                                        const p3 = { x: room.x, y: room.y + room.height };

                                                        // Floors (z = 0)
                                                        const f0 = projectIso(p0.x, p0.y, 0);
                                                        const f1 = projectIso(p1.x, p1.y, 0);
                                                        const f2 = projectIso(p2.x, p2.y, 0);
                                                        const f3 = projectIso(p3.x, p3.y, 0);

                                                        // Wall Tops (z = wallH)
                                                        const t0 = projectIso(p0.x, p0.y, wallH);
                                                        const t1 = projectIso(p1.x, p1.y, wallH);
                                                        const t2 = projectIso(p2.x, p2.y, wallH);
                                                        const t3 = projectIso(p3.x, p3.y, wallH);

                                                        // Center for Label
                                                        const c = projectIso(room.x + room.width/2, room.y + room.height/2, 4);

                                                        return (
                                                            <g key={`struct-${room.id}`}>
                                                                {/* Floor Polygon (Solid Pastel Fills) */}
                                                                <polygon
                                                                    points={`${f0.x},${f0.y} ${f1.x},${f1.y} ${f2.x},${f2.y} ${f3.x},${f3.y}`}
                                                                    fill={room.color}
                                                                    fillOpacity="0.85"
                                                                    stroke="#a8a29e"
                                                                    strokeWidth="0.5"
                                                                />

                                                                {/* Beige Solid Cardboard Wall Faces */}
                                                                {/* Wall 0: Back-left */}
                                                                <polygon
                                                                    points={`${f0.x},${f0.y} ${f1.x},${f1.y} ${t1.x},${t1.y} ${t0.x},${t0.y}`}
                                                                    fill="#d6c5b3"
                                                                    stroke="#5c4d3c"
                                                                    strokeWidth="1.2"
                                                                />
                                                                {/* Wall 1: Back-right */}
                                                                <polygon
                                                                    points={`${f1.x},${f1.y} ${f2.x},${f2.y} ${t2.x},${t2.y} ${t1.x},${t1.y}`}
                                                                    fill="#c8b7a6"
                                                                    stroke="#5c4d3c"
                                                                    strokeWidth="1.2"
                                                                />
                                                                {/* Wall 3: Front-left */}
                                                                <polygon
                                                                    points={`${f3.x},${f3.y} ${f0.x},${f0.y} ${t0.x},${t0.y} ${t3.x},${t3.y}`}
                                                                    fill="#decbb7"
                                                                    stroke="#5c4d3c"
                                                                    strokeWidth="1.2"
                                                                />
                                                                {/* Wall 2: Front-right */}
                                                                <polygon
                                                                    points={`${f2.x},${f2.y} ${f3.x},${f3.y} ${t3.x},${t3.y} ${t2.x},${t2.y}`}
                                                                    fill="#bfaea0"
                                                                    stroke="#5c4d3c"
                                                                    strokeWidth="1.2"
                                                                />

                                                                {/* Room Labels inside the room floor */}
                                                                <text
                                                                    x={c.x}
                                                                    y={c.y - 2}
                                                                    textAnchor="middle"
                                                                    fill="#292524"
                                                                    fontSize="8"
                                                                    fontWeight="bold"
                                                                    fontFamily="monospace"
                                                                >
                                                                    {room.type.toUpperCase()}
                                                                </text>
                                                                <text
                                                                    x={c.x}
                                                                    y={c.y + 6}
                                                                    textAnchor="middle"
                                                                    fill="#0369a1"
                                                                    fontSize="6.5"
                                                                    fontWeight="bold"
                                                                    fontFamily="monospace"
                                                                >
                                                                    {room.area} SQFT
                                                                </text>
                                                            </g>
                                                        );
                                                    });
                                                })()}
                                            </svg>

                                            {/* Hover info overlay to highlight that only structures are generated */}
                                            <div className="absolute bottom-3 left-3 right-3 bg-white/90 border border-stone-200 rounded-xl p-2 flex items-start gap-1.5 backdrop-blur-sm pointer-events-none z-20">
                                                <Info size={12} className="text-stone-600 shrink-0 mt-0.5" />
                                                <p className="text-[9px] text-stone-500 leading-normal">
                                                     <strong>Architectural Model:</strong> Solid cardboard partition models showing exact offsets, shared walls, and room layout branches.
                                                </p>
                                            </div>
                                        </div>
                                    )}
                                </div>

                                {/* Performance Analysis Scores */}
                                <div className="border-t border-stone-150 p-4 bg-white/40 grid grid-cols-2 md:grid-cols-4 gap-4 items-center">
                                    <div className="flex flex-col gap-1 select-none">
                                        <span className="text-[9px] text-stone-400 font-bold uppercase tracking-wider">Layout Efficiency</span>
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 bg-stone-200 h-1.5 rounded-full overflow-hidden">
                                                <div className="bg-emerald-500 h-full rounded-full transition-all duration-700" style={{ width: `${stats.efficiency}%` }} />
                                            </div>
                                            <span className="text-xs font-bold text-stone-700 font-mono">{stats.efficiency}%</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col gap-1 select-none">
                                        <span className="text-[9px] text-stone-400 font-bold uppercase tracking-wider">Daylight Index</span>
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 bg-stone-200 h-1.5 rounded-full overflow-hidden">
                                                <div className="bg-amber-500 h-full rounded-full transition-all duration-700" style={{ width: `${stats.daylight}%` }} />
                                            </div>
                                            <span className="text-xs font-bold text-stone-700 font-mono">{stats.daylight}%</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col gap-1 select-none">
                                        <span className="text-[9px] text-stone-400 font-bold uppercase tracking-wider">Privacy Rating</span>
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 bg-stone-200 h-1.5 rounded-full overflow-hidden">
                                                <div className="bg-indigo-500 h-full rounded-full transition-all duration-700" style={{ width: `${stats.privacy}%` }} />
                                            </div>
                                            <span className="text-xs font-bold text-stone-700 font-mono">{stats.privacy}%</span>
                                        </div>
                                    </div>
                                    <div className="flex flex-col gap-1 select-none">
                                        <span className="text-[9px] text-stone-400 font-bold uppercase tracking-wider">Circulation flow</span>
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 bg-stone-200 h-1.5 rounded-full overflow-hidden">
                                                <div className="bg-pink-500 h-full rounded-full transition-all duration-700" style={{ width: `${stats.circulation}%` }} />
                                            </div>
                                            <span className="text-xs font-bold text-stone-700 font-mono">{stats.circulation}%</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Process Timeline section */}
            <div className="py-24 px-4 max-w-7xl mx-auto border-t border-stone-100">
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-5xl font-light text-charcoal tracking-tight mb-4 animate-fade-in">
                        How <span className="font-semibold">VoxAssist Works</span>
                    </h2>
                    <p className="text-stone-500 max-w-xl mx-auto font-light">
                        A clean automated pipeline transforming conversation constraints to structural 3D volumes.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 relative">
                    <StepCard
                        num="01"
                        icon={<Mic size={22} />}
                        title="Speech Input"
                        desc="Provide room criteria (e.g. Living room size, bedroom boundaries) or write structural prompts."
                    />
                    <StepCard
                        num="02"
                        icon={<Cpu size={22} />}
                        title="Ollama Parsing"
                        desc="Extract room listings and relational logic locally using an embedded Ollama-powered pipeline."
                    />
                    <StepCard
                        num="03"
                        icon={<Layers size={22} />}
                        title="ML Adjacency Engine"
                        desc="The vox-architect algorithm executes placement solving, satisfying wall and door constraints."
                    />
                    <StepCard
                        num="04"
                        icon={<Box size={22} />}
                        title="3D Walkthrough View"
                        desc="Compile spatial outputs to walkable 3D wireframe mesh volumes dynamically via React Three Fiber."
                    />
                </div>
            </div>

            {/* Feature Cards Grid */}
            <div className="bg-stone-50/50 py-24 border-t border-stone-100">
                <div className="px-4 max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-5xl font-light text-charcoal tracking-tight mb-4">
                            High Fidelity <span className="font-semibold">Layout Architectures</span>
                        </h2>
                        <p className="text-stone-500 max-w-xl mx-auto font-light">
                            Built for modern architectural workflows, compiling spatial requirements directly into CAD formats.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={<Mic className="text-amber-600" size={26} />}
                            title="Prompt to Floorplan"
                            tag="Ollama Core"
                            desc="Describe room relationships (e.g. 'bedroom adjacent to bathroom') to instantly generate constraints via local LLM parsing."
                        />
                        <FeatureCard
                            icon={<Cpu className="text-stone-855" size={26} />}
                            title="Custom ML Engine"
                            tag="vox-architect"
                            desc="Leverages our localized layout optimization module to satisfy adjacent doors, window illumination, and wall thicknesses."
                        />
                        <FeatureCard
                            icon={<Box className="text-blue-600" size={26} />}
                            title="3D Walkthrough View"
                            tag="React Three Fiber"
                            desc="Generate lightweight 3D wall layouts directly in the client browser. Walk inside the rooms to review dimensions."
                        />
                        <FeatureCard
                            icon={<Activity className="text-emerald-600" size={26} />}
                            title="Keep-Alive Automation"
                            tag="GitHub Workflows"
                            desc="Includes an automated background workflow that maintains server responsiveness, eliminating cold startup lag on free deployment tiers."
                        />
                        <FeatureCard
                            icon={<Database className="text-cyan-600" size={26} />}
                            title="Cloud Syncing & Auth"
                            tag="Firebase"
                            desc="Securely register accounts, compile designs, save project progress in cloud databases, and load blueprints from anywhere."
                        />
                        <FeatureCard
                            icon={<Zap className="text-yellow-600" size={26} />}
                            title="Sleek UI/UX Dark Mode"
                            tag="Tailwind CSS"
                            desc="Clean, premium dashboard with modern dark-mode capabilities, built using Radix and Shadcn UI component design rules."
                        />
                    </div>
                </div>
            </div>

            {/* Ultra-Premium Obsidian Developer Footer */}
            <footer className="relative bg-[#080808] text-stone-300 border-t border-stone-900 pt-20 pb-12 overflow-hidden font-['Plus_Jakarta_Sans']">
                {/* Glowing background ambience */}
                <div className="absolute -top-40 -left-40 w-96 h-96 bg-amber-500/[0.03] rounded-full blur-3xl pointer-events-none" />
                <div className="absolute bottom-0 right-0 w-[500px] h-[500px] bg-indigo-500/[0.01] rounded-full blur-3xl pointer-events-none" />

                <div className="max-w-7xl mx-auto px-6 relative z-10">
                    <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 pb-16 border-b border-stone-900 items-start">

                        {/* Logo Column */}
                        <div className="lg:col-span-6 flex flex-col items-start gap-4">
                            <div className="flex items-center gap-2.5 select-none">
                                <span className="text-2xl font-bold text-cream font-['Space_Grotesk'] tracking-tight">
                                    VoxAssist<span className="text-amber-500">.</span>
                                </span>
                                <span className="px-2 py-0.5 rounded bg-stone-900 border border-stone-850 text-[10px] font-mono text-stone-400 uppercase tracking-widest font-semibold">
                                    v2.0.0
                                </span>
                            </div>
                            <p className="text-sm text-stone-450 font-light leading-relaxed max-w-md">
                                An open-source AI layout compiler turning architectural dimensional bounds and speech prompts into 2D blueprints and structural 3D meshes.
                            </p>
                        </div>

                        {/* Project Resources Column */}
                        <div className="lg:col-span-3 flex flex-col items-start gap-4">
                            <h4 className="text-xs font-semibold text-stone-500 uppercase tracking-widest font-mono">Resources</h4>
                            <div className="flex flex-col gap-3 text-sm">
                                <a
                                    href="https://github.com/PuneethPujala/vox-assist"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-stone-300 hover:text-amber-500 hover:translate-x-1.5 transition-all duration-300 flex items-center gap-2 font-medium"
                                >
                                    <Activity size={14} className="text-amber-500" /> GitHub Repository
                                </a>
                                <a
                                    href="https://drive.google.com/file/d/1dweeA3qDr893B8jhXsGHp6uKbHLqZanF/view"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-stone-300 hover:text-amber-500 hover:translate-x-1.5 transition-all duration-300 flex items-center gap-2 font-medium"
                                >
                                    <FileText size={14} className="text-amber-500" /> Project Document
                                </a>
                            </div>
                        </div>

                        {/* Contact Team Column */}
                        <div className="lg:col-span-3 flex flex-col items-start gap-4">
                            <h4 className="text-xs font-semibold text-stone-500 uppercase tracking-widest font-mono">Connect</h4>
                            <div className="flex flex-col gap-3 text-sm">
                                <a
                                    href="mailto:puneethpujala@gmail.com"
                                    className="text-stone-300 hover:text-amber-500 hover:translate-x-1.5 transition-all duration-300 flex items-center gap-2 font-medium"
                                >
                                    <ChevronRight size={14} className="text-amber-500" /> Contact our Team
                                </a>

                            </div>
                        </div>
                    </div>

                    {/* Bottom Metadata & Signature */}
                    <div className="pt-8 flex flex-col sm:flex-row justify-between items-center gap-6">
                        <div className="flex items-center gap-4 text-xs text-stone-500 font-mono">
                            <span>© {new Date().getFullYear()} VoxAssist Project.</span>

                        </div>

                        <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-stone-900/50 border border-stone-850/80 text-xs text-stone-400 select-none shadow-inner">
                            <span>Made with</span>
                            <motion.span
                                animate={{ scale: [1, 1.25, 1] }}
                                transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
                                className="text-red-500 text-sm"
                            >
                                ❤️
                            </motion.span>
                            <span>by team</span>
                            <span className="font-semibold text-cream">APK</span>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
};

const TechBadge = ({ label, sub }) => (
    <div className="flex flex-col items-center select-none group">
        <span className="text-sm font-semibold text-charcoal group-hover:text-amber-700 transition-colors duration-300">{label}</span>
        <span className="text-[10px] text-stone-400 uppercase tracking-widest font-mono mt-0.5">{sub}</span>
    </div>
);

const StepCard = ({ num, icon, title, desc }) => (
    <motion.div
        whileHover={{ y: -6, scale: 1.02, boxShadow: "0 20px 40px rgba(0, 0, 0, 0.05)" }}
        className="p-8 bg-white/30 backdrop-blur-md rounded-3xl border border-white/60 shadow-sm relative group transition-all duration-300 hover:bg-white/50 hover:border-white/80"
    >
        <span className="absolute top-6 right-8 text-4xl font-light text-stone-300 group-hover:text-stone-400 font-mono transition-colors duration-300 font-semibold">
            {num}
        </span>
        <div className="w-12 h-12 bg-white/80 rounded-xl flex items-center justify-center text-stone-700 mb-6 group-hover:bg-charcoal group-hover:text-cream transition-all duration-300 border border-white/80 shadow-inner">
            {icon}
        </div>
        <h3 className="text-lg font-semibold text-charcoal mb-2 group-hover:text-amber-800 transition-colors duration-300">{title}</h3>
        <p className="text-stone-500 text-sm leading-relaxed font-light">{desc}</p>
    </motion.div>
);

const FeatureCard = ({ icon, title, tag, desc }) => (
    <motion.div
        whileHover={{ y: -5 }}
        className="p-8 bg-white rounded-2xl shadow-sm hover:shadow-md border border-stone-150 transition-all flex flex-col justify-between h-full"
    >
        <div>
            <div className="w-12 h-12 bg-stone-50 rounded-xl flex items-center justify-center text-charcoal mb-6 border border-stone-100">
                {icon}
            </div>
            <div className="flex items-center gap-2 mb-3">
                <h3 className="text-lg font-semibold text-charcoal">{title}</h3>
                <span className="px-2 py-0.5 rounded bg-stone-100 text-[10px] font-mono text-stone-600 font-medium">
                    {tag}
                </span>
            </div>
            <p className="text-stone-500 text-sm leading-relaxed">{desc}</p>
        </div>
    </motion.div>
);

export default Dashboard;
