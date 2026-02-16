import React from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Mic, Layout, Box } from 'lucide-react';
import { Link } from 'react-router-dom';

const Dashboard = () => {
    return (
        <div className="pt-24 pb-12 px-4 max-w-7xl mx-auto">
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center mb-16"
            >
                <h1 className="text-5xl md:text-6xl font-light text-charcoal mb-4 tracking-tight">
                    Design Your Dream Home<br />
                    <span className="font-semibold">Through Voice</span>
                </h1>
                <p className="text-xl text-stone-500 max-w-2xl mx-auto mb-8">
                    Translate natural language into architectural intelligence using our AI-powered layout generator.
                </p>
                <Link
                    to="/create"
                    className="inline-flex items-center px-8 py-4 bg-charcoal text-cream rounded-full text-lg font-medium hover:bg-stone-800 transition-transform hover:scale-105 shadow-xl"
                >
                    Start Creating <ArrowRight className="ml-2" size={20} />
                </Link>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <FeatureCard
                    icon={<Mic size={32} />}
                    title="Natural Voice Input"
                    desc="Simply describe your dream home in your own words. Our AI understands architectural intent."
                />
                <FeatureCard
                    icon={<Layout size={32} />}
                    title="Intelligent Layouts"
                    desc="Get spatially optimized, architecturally valid floor plans generated instantly."
                />
                <FeatureCard
                    icon={<Box size={32} />}
                    title="3D Visualization"
                    desc="Walk through your generated design in interactive 3D directly in the browser."
                />
            </div>
            {/* Newsletter & Contact Section */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="mt-20 border-t border-stone-100 pt-16"
            >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                    {/* Newsletter */}
                    <div className="bg-stone-50 rounded-2xl p-8">
                        <h3 className="text-2xl font-light text-charcoal mb-4">Stay Inspired</h3>
                        <p className="text-stone-500 mb-6">
                            Join our newsletter for the latest architectural trends and AI updates.
                        </p>
                        <form className="flex gap-2" onSubmit={(e) => e.preventDefault()}>
                            <input
                                type="email"
                                placeholder="Enter your email"
                                className="flex-1 bg-white border border-stone-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-stone-400"
                            />
                            <button className="bg-charcoal text-white px-6 py-3 rounded-xl hover:bg-stone-800 transition-colors">
                                Subscribe
                            </button>
                        </form>
                    </div>

                    {/* Contact & Links */}
                    <div className="flex flex-col justify-between">
                        <div>
                            <h3 className="text-2xl font-light text-charcoal mb-4">Get in Touch</h3>
                            <p className="text-stone-500 mb-6">
                                Have questions or custom requirements? We'd love to hear from you.
                            </p>
                            <a
                                href="mailto:hello@voxassist.ai"
                                className="text-xl font-medium text-charcoal hover:underline"
                            >
                                puneethpujala@gmail.com
                            </a>
                        </div>

                        <div className="mt-8 flex gap-6 text-stone-400">
                            <a href="#" className="hover:text-charcoal transition-colors">Twitter</a>
                            <a href="#" className="hover:text-charcoal transition-colors">LinkedIn</a>
                            <a href="#" className="hover:text-charcoal transition-colors">Instagram</a>
                        </div>
                    </div>
                </div>

                <div className="mt-16 text-center text-stone-400 text-sm">
                    © {new Date().getFullYear()} VoxAssist AI. All rights reserved.
                </div>
            </motion.div>
        </div>
    );
};

const FeatureCard = ({ icon, title, desc }) => (
    <motion.div
        whileHover={{ y: -5 }}
        className="p-8 bg-white rounded-2xl shadow-sm hover:shadow-md border border-stone-100 transition-all"
    >
        <div className="w-12 h-12 bg-stone-100 rounded-xl flex items-center justify-center text-charcoal mb-6">
            {icon}
        </div>
        <h3 className="text-xl font-semibold text-charcoal mb-3">{title}</h3>
        <p className="text-stone-600 leading-relaxed">{desc}</p>
    </motion.div>
);

export default Dashboard;
