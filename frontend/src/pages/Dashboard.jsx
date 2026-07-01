import React from 'react';
import { motion } from 'framer-motion';
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
    ChevronRight 
} from 'lucide-react';
import { Link } from 'react-router-dom';
import voxHeroImage from '../assets/vox_architectural_render.png';

const Dashboard = () => {
    return (
        <div className="min-h-screen bg-cream text-charcoal overflow-x-hidden selection:bg-stone-200">
            {/* Hero Section */}
            <div className="relative pt-32 pb-20 px-4 max-w-7xl mx-auto flex flex-col items-center">
                {/* Decorative background glow */}
                <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-gradient-to-tr from-amber-100/40 via-orange-100/20 to-stone-100/50 rounded-full blur-3xl pointer-events-none" />

                <motion.div
                    initial={{ opacity: 0, y: 30 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    className="text-center relative z-10 max-w-4xl"
                >
                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-stone-100 text-stone-700 mb-6 tracking-wide uppercase border border-stone-200/60 shadow-sm">
                        <Sparkles size={12} className="text-amber-500 animate-pulse" /> Next-Gen AI Floorplanner
                    </span>

                    <h1 className="text-5xl md:text-7xl font-extralight text-charcoal mb-6 tracking-tight leading-[1.1]">
                        Architectural Intelligence <br />
                        <span className="font-semibold bg-gradient-to-r from-stone-900 via-stone-800 to-amber-700 bg-clip-text text-transparent">
                            Powered by Voice
                        </span>
                    </h1>

                    <p className="text-lg md:text-xl text-stone-500 max-w-2xl mx-auto mb-10 leading-relaxed font-light">
                        VoxAssist converts speech dimensions and conversational prompts into full-scale 2D floorplans and interactive 3D architectural models in seconds.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
                        <Link
                            to="/create"
                            className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-4 bg-charcoal text-cream rounded-full text-base font-semibold hover:bg-stone-800 hover:shadow-2xl transition-all duration-300 hover:scale-[1.03] shadow-lg group"
                        >
                            Start Creating <ArrowRight className="ml-2 group-hover:translate-x-1 transition-transform" size={18} />
                        </Link>
                        <Link
                            to="/explore"
                            className="w-full sm:w-auto inline-flex items-center justify-center px-8 py-4 bg-white/80 backdrop-blur-sm text-charcoal border border-stone-200 rounded-full text-base font-medium hover:bg-stone-50 transition-all duration-300"
                        >
                            Explore Designs
                        </Link>
                    </div>
                </motion.div>

                {/* Hero Asset: Premium Architectural Render Device Mockup */}
                <motion.div
                    initial={{ opacity: 0, y: 50 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 1, delay: 0.2, ease: "easeOut" }}
                    className="relative z-10 w-full max-w-5xl rounded-2xl p-2 bg-gradient-to-b from-stone-200/50 to-stone-300/30 border border-white/40 shadow-2xl backdrop-blur-sm"
                >
                    <div className="bg-stone-950 rounded-xl overflow-hidden shadow-inner border border-stone-800/80">
                        {/* Browser Bar */}
                        <div className="flex items-center justify-between px-4 py-3 bg-stone-900 border-b border-stone-800/50">
                            <div className="flex items-center gap-1.5">
                                <div className="w-3 h-3 rounded-full bg-red-500/80" />
                                <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                                <div className="w-3 h-3 rounded-full bg-green-500/80" />
                            </div>
                            <div className="px-10 py-1 bg-stone-950/80 border border-stone-800/40 rounded-md text-[11px] text-stone-500 tracking-wide select-none font-mono">
                                voxassist.ai/editor
                            </div>
                            <div className="w-12" />
                        </div>
                        {/* Main Render Image */}
                        <div className="relative group overflow-hidden bg-stone-900/60 aspect-[16/9] flex items-center justify-center">
                            <img 
                                src={voxHeroImage} 
                                alt="VoxAssist 3D Architectural Blueprint Model" 
                                className="w-full h-full object-cover opacity-90 group-hover:opacity-95 transition-opacity duration-700"
                            />
                            {/* Inner ambient shadows and details */}
                            <div className="absolute inset-0 bg-gradient-to-t from-stone-950/20 via-transparent to-transparent pointer-events-none" />
                        </div>
                    </div>

                    {/* Floating Badges */}
                    <div className="absolute -left-4 top-1/4 hidden md:flex items-center gap-3 px-4 py-3 bg-white/90 backdrop-blur-md rounded-2xl shadow-xl border border-stone-100/50 transform -rotate-1 hover:rotate-0 transition-transform duration-300">
                        <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
                        <div>
                            <p className="text-[10px] text-stone-400 font-semibold uppercase tracking-wider">Backend Engine</p>
                            <p className="text-xs font-semibold text-charcoal">FastAPI Orchestration</p>
                        </div>
                    </div>

                    <div className="absolute -right-4 bottom-1/4 hidden md:flex items-center gap-3 px-4 py-3 bg-white/90 backdrop-blur-md rounded-2xl shadow-xl border border-stone-100/50 transform rotate-1 hover:rotate-0 transition-transform duration-300">
                        <div className="w-3 h-3 rounded-full bg-amber-500 animate-pulse" />
                        <div>
                            <p className="text-[10px] text-stone-400 font-semibold uppercase tracking-wider">3D Mesh Plane</p>
                            <p className="text-xs font-semibold text-charcoal">React Three Fiber</p>
                        </div>
                    </div>
                </motion.div>
            </div>

            {/* Tech Stack Horizontal Bar */}
            <div className="border-y border-stone-100 bg-white/50 py-8 px-4">
                <div className="max-w-7xl mx-auto flex flex-wrap justify-center items-center gap-8 md:gap-16 text-center">
                    <p className="text-xs font-semibold tracking-widest text-stone-400 uppercase w-full lg:w-auto mb-2 lg:mb-0">
                        Core Ecosystem:
                    </p>
                    <TechBadge label="FastAPI" sub="Python" />
                    <TechBadge label="React & Vite" sub="Frontend" />
                    <TechBadge label="Three.js" sub="3D Meshes" />
                    <TechBadge label="Firebase" sub="Cloud DB" />
                    <TechBadge label="Ollama" sub="Local LLM" />
                </div>
            </div>

            {/* Pipeline Process Section */}
            <div className="py-24 px-4 max-w-7xl mx-auto">
                <div className="text-center mb-16">
                    <h2 className="text-3xl md:text-5xl font-light text-charcoal tracking-tight mb-4">
                        How <span className="font-semibold">VoxAssist Works</span>
                    </h2>
                    <p className="text-stone-500 max-w-xl mx-auto">
                        A seamless, local-first compilation pipeline transforming voice constraints to immersive walk-throughs.
                    </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 relative">
                    <StepCard 
                        num="01" 
                        icon={<Mic size={24} />} 
                        title="Voice Prompting" 
                        desc="State spatial requirements, layout ideas, or room sizes naturally in conversational English." 
                    />
                    <StepCard 
                        num="02" 
                        icon={<Cpu size={24} />} 
                        title="Local LLM Parsing" 
                        desc="Ollama extracts structural parameters, room counts, and constraints locally." 
                    />
                    <StepCard 
                        num="03" 
                        icon={<Layers size={24} />} 
                        title="Custom ML Engine" 
                        desc="Our vox-architect algorithm executes layout reasoning to solve wall-adjacencies." 
                    />
                    <StepCard 
                        num="04" 
                        icon={<Box size={24} />} 
                        title="3D Walkthrough" 
                        desc="React Three Fiber instant mesh generator compiles structural data into walkable 3D rooms." 
                    />
                </div>
            </div>

            {/* Feature Showcase Grid */}
            <div className="bg-stone-50/50 py-24 border-t border-stone-100">
                <div className="px-4 max-w-7xl mx-auto">
                    <div className="text-center mb-16">
                        <h2 className="text-3xl md:text-5xl font-light text-charcoal tracking-tight mb-4">
                            Engineered for <span className="font-semibold">High Performance</span>
                        </h2>
                        <p className="text-stone-500 max-w-xl mx-auto">
                            Powerful architecture delivering state-of-the-art layout generation and high fidelity visualizations.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        <FeatureCard
                            icon={<Mic className="text-amber-600" size={26} />}
                            title="Prompt to Floorplan"
                            tag="Ollama Core"
                            desc="Describe room relationships (e.g., 'master bedroom adjacent to bath') to instantly trigger automated layout generation."
                        />
                        <FeatureCard
                            icon={<Cpu className="text-stone-800" size={26} />}
                            title="Custom ML Engine"
                            tag="vox-architect"
                            desc="Utilizes our specialized spatial reasoning engine to satisfy structural constraints, door placements, and wall alignments."
                        />
                        <FeatureCard
                            icon={<Box className="text-blue-600" size={26} />}
                            title="3D Visualization"
                            tag="React Three Fiber"
                            desc="Real-time rendering of generated floorplans into full 3D models directly in your browser. Walk through and inspect rooms."
                        />
                        <FeatureCard
                            icon={<Activity className="text-emerald-600" size={26} />}
                            title="Keep-Alive Mechanism"
                            tag="GitHub Actions"
                            desc="Features automated keep-alive orchestration preventing server sleep states on free hosting, ensuring zero-latency initial load times."
                        />
                        <FeatureCard
                            icon={<Database className="text-amber-500" size={26} />}
                            title="Real-time UX & Firebase"
                            tag="Radix Primitives"
                            desc="A fluid client state built on top of Radix primitives and Firebase backend, supporting cloud saving and live configuration."
                        />
                        <FeatureCard
                            icon={<Zap className="text-yellow-600" size={26} />}
                            title="Fluid Dark Mode"
                            tag="Tailwind CSS"
                            desc="A beautiful design environment built to respect system settings and featuring a seamless toggling visual presentation."
                        />
                    </div>
                </div>
            </div>

            {/* Newsletter & Contact Footer */}
            <div className="pt-20 pb-12 px-4 max-w-7xl mx-auto border-t border-stone-100">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-12 mb-16">
                    {/* Newsletter */}
                    <div className="bg-stone-50 border border-stone-200/50 rounded-2xl p-8 relative overflow-hidden">
                        <div className="absolute -right-6 -bottom-6 w-32 h-32 bg-stone-200/20 rounded-full blur-2xl pointer-events-none" />
                        <h3 className="text-2xl font-semibold text-charcoal mb-2">Stay Inspired</h3>
                        <p className="text-stone-500 mb-6 text-sm">
                            Get updates on new architectural layouts, voxel modules, and custom ML training datasets.
                        </p>
                        <form className="flex flex-col sm:flex-row gap-2" onSubmit={(e) => e.preventDefault()}>
                            <input
                                type="email"
                                placeholder="Enter your email"
                                className="flex-1 bg-white border border-stone-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-stone-400 focus:border-transparent transition-all"
                            />
                            <button className="bg-charcoal text-white text-sm font-semibold px-6 py-3 rounded-xl hover:bg-stone-800 transition-colors shadow-md">
                                Subscribe
                            </button>
                        </form>
                    </div>

                    {/* Contact & Links */}
                    <div className="flex flex-col justify-between py-2">
                        <div>
                            <h3 className="text-2xl font-light text-charcoal mb-4">Connect with the <span className="font-semibold">Team</span></h3>
                            <p className="text-stone-500 mb-6 text-sm leading-relaxed">
                                Curious about deployment, model parameters, or hosting a custom instance? Reach out for developer collaboration.
                            </p>
                            <a
                                href="mailto:puneethpujala@gmail.com"
                                className="text-lg font-medium text-charcoal hover:underline hover:text-amber-800 transition-colors flex items-center gap-1.5"
                            >
                                puneethpujala@gmail.com <ChevronRight size={16} />
                            </a>
                        </div>

                        <div className="mt-8 flex gap-6 text-stone-400 text-sm">
                            <a href="#" className="hover:text-charcoal transition-colors">Twitter</a>
                            <a href="#" className="hover:text-charcoal transition-colors">LinkedIn</a>
                            <a href="#" className="hover:text-charcoal transition-colors">GitHub Project</a>
                        </div>
                    </div>
                </div>

                <div className="pt-8 border-t border-stone-100 flex flex-col sm:flex-row justify-between items-center gap-4 text-stone-400 text-xs">
                    <p>© {new Date().getFullYear()} VoxAssist AI. All rights reserved.</p>
                    <p className="font-mono">FastAPI Core 2.0.0 & React Fiber</p>
                </div>
            </div>
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
        whileHover={{ y: -4 }}
        className="p-6 bg-white rounded-2xl border border-stone-200/60 shadow-sm relative group transition-all"
    >
        <span className="absolute top-4 right-6 text-3xl font-extralight text-stone-200 group-hover:text-stone-300 font-mono transition-colors font-semibold">
            {num}
        </span>
        <div className="w-10 h-10 bg-stone-50 rounded-lg flex items-center justify-center text-stone-600 mb-6 group-hover:bg-charcoal group-hover:text-cream transition-colors duration-300 border border-stone-150">
            {icon}
        </div>
        <h3 className="text-lg font-semibold text-charcoal mb-2">{title}</h3>
        <p className="text-stone-500 text-sm leading-relaxed">{desc}</p>
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
