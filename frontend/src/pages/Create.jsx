import React, { useState, Suspense, useRef, useEffect } from 'react';
import { Canvas, useLoader, useThree } from '@react-three/fiber';
import { OrbitControls, Stage, Center, Grid } from '@react-three/drei';
import { PLYLoader } from 'three/examples/jsm/loaders/PLYLoader';
import { motion } from 'framer-motion';
import { useAuth } from '../contexts/AuthContext';
import axios from 'axios';
import { Loader2, Send, Download } from 'lucide-react';
import * as THREE from 'three';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

const Model = ({ url }) => {
    const geometry = useLoader(PLYLoader, url);
    const { camera, controls } = useThree(); // Access camera & controls

    // Auto-frame the camera when model loads
    useEffect(() => {
        if (geometry) {
            geometry.computeVertexNormals();
            geometry.computeBoundingBox();

            // 1. Calculate Bounding Box & Center
            const box = geometry.boundingBox;
            const center = new THREE.Vector3();
            box.getCenter(center);

            const size = new THREE.Vector3();
            box.getSize(size);

            const maxDim = Math.max(size.x, size.y, size.z);

            // 2. Position Camera (Fit to View)
            // Distance required to fit object within FOV
            const fov = camera.fov * (Math.PI / 180);
            let cameraDist = Math.abs(maxDim / 2 / Math.tan(fov / 2));
            cameraDist *= 2.0; // Add some padding (2x distance)

            // Move camera to an isometric-like angle relative to center
            const newPos = new THREE.Vector3(
                center.x + cameraDist,
                center.y + cameraDist,
                center.z + cameraDist
            );

            camera.position.copy(newPos);
            camera.lookAt(center);

            // 3. Update Controls Target
            if (controls) {
                controls.target.copy(center);
                controls.update();
            }

            console.log("Auto-framed camera to:", newPos);
        }
    }, [geometry, url, camera, controls]);

    return (
        <group>
            <mesh geometry={geometry}>
                <meshStandardMaterial
                    vertexColors={true}
                    side={THREE.DoubleSide}
                    roughness={0.8}
                />
            </mesh>
        </group>
    );
};

const RoomHighlight = ({ roomPoly, color }) => {
    if (!roomPoly) return null;

    const shape = new THREE.Shape();
    let coords = roomPoly.coordinates;

    // Robust parsing for Ring vs Multi-Ring
    if (Array.isArray(coords[0]) && Array.isArray(coords[0][0])) {
        coords = coords[0];
    }

    if (coords && coords.length > 0) {
        shape.moveTo(coords[0][0], coords[0][1]);
        for (let i = 1; i < coords.length; i++) {
            shape.lineTo(coords[i][0], coords[i][1]);
        }
    }

    // Taller extrusion, lifted up
    const extrudeSettings = { depth: 2.8, bevelEnabled: false };

    return (
        <mesh position={[0, 0, 0.1]}>
            <extrudeGeometry args={[shape, extrudeSettings]} />
            <meshBasicMaterial
                color={color || "#ff00ff"}
                transparent
                opacity={0.6}
                side={THREE.DoubleSide}
                depthTest={false} /* Force it to show on top of everything */
            />
        </mesh>
    );
};

const InteractiveRoom = ({ roomPoly, roomId, setHoveredRoomId }) => {
    if (!roomPoly) return null;

    const shape = new THREE.Shape();
    let coords = roomPoly.coordinates;

    // Handle standard GeoJSON (Array of Rings) vs Flattened (Array of Points)
    // Standard: [[x,y], [x,y]...] -> coords[0] is the ring
    // Flattened: [[x,y], [x,y]...] -> coords is the ring
    // Wait, if flattened, coords is [pt, pt]. pt is [x,y].
    // If standard, coords is [ring, hole]. ring is [pt, pt].

    // Check depth:
    // If coords[0][0] is a number, it's a Ring (Flattened Polygon structure).
    // If coords[0][0] is an array, it's a List of Rings (Standard Polygon).

    if (Array.isArray(coords[0]) && Array.isArray(coords[0][0])) {
        coords = coords[0]; // Extract exterior ring
    }

    if (coords && coords.length > 0) {
        shape.moveTo(coords[0][0], coords[0][1]);
        for (let i = 1; i < coords.length; i++) {
            shape.lineTo(coords[i][0], coords[i][1]);
        }
    }

    const extrudeSettings = { depth: 2.8, bevelEnabled: false }; // Match wall height

    return (
        <mesh
            position={[0, 0, 0]}
            onPointerOver={(e) => { e.stopPropagation(); setHoveredRoomId(roomId); }}
            onPointerOut={() => setHoveredRoomId(null)}
        >
            <extrudeGeometry args={[shape, extrudeSettings]} />
            <meshBasicMaterial transparent opacity={0.0} />
        </mesh>
    );
};

const Create = () => {
    const { currentUser } = useAuth();
    const [prompt, setPrompt] = useState("");
    const [loading, setLoading] = useState(false);
    const [modelUrl, setModelUrl] = useState(null);
    const [layoutSpec, setLayoutSpec] = useState(null);
    const [layoutData, setLayoutData] = useState(null); // Full layout (polygons)
    const [score, setScore] = useState(0);
    const [stats, setStats] = useState(null);
    const [error, setError] = useState(null);
    const [hoveredRoomId, setHoveredRoomId] = useState(null); // ID for 3D highlight

    const [candidates, setCandidates] = useState([]);
    const [selectedCandidateId, setSelectedCandidateId] = useState(null);

    const handleGenerate = async () => {
        if (!prompt.trim()) return;

        setLoading(true);
        setError(null);
        setCandidates([]);
        setSelectedCandidateId(null);
        setModelUrl(null);
        setLayoutSpec(null);
        setLayoutData(null);

        try {
            const token = await currentUser.getIdToken();
            const response = await axios.post(
                `${import.meta.env.VITE_API_URL}/api/v1/generate`,
                { prompt },
                { headers: { Authorization: `Bearer ${token}` } }
            );

            if (response.data.success) {
                // Determine winner first
                const best = response.data.candidates.find(c => c.model_url === response.data.model_url) || response.data.candidates[0];

                // Set candidates (mapped for UI)
                setCandidates(response.data.candidates);

                // Auto-select winner
                handleSelectCandidate(best);
            } else {
                setError(response.data.error || "Generation failed");
            }
        } catch (err) {
            console.error(err);
            setError("Failed to connect to server. Ensure Backend is running.");
        } finally {
            setLoading(false);
        }
    };

    const handleSelectCandidate = (candidate) => {
        setSelectedCandidateId(candidate.id);
        setModelUrl(`${import.meta.env.VITE_API_URL}${candidate.model_url}`);
        setLayoutSpec(candidate.spec);
        setLayoutData(candidate.layout.rooms); // Store rooms dict
        setScore(candidate.score);
        setStats(candidate.stats);
    };

    // Helper to get poly for hovered room
    const hoveredPoly = hoveredRoomId && layoutData ? layoutData[hoveredRoomId] : null;
    const hoveredColor = hoveredRoomId && layoutSpec ? layoutSpec.rooms.find(r => r.id === hoveredRoomId)?.color : null;

    return (
        <div className="pt-20 px-4 h-screen flex flex-col md:flex-row overflow-hidden bg-cream">
            {/* Left Panel: Input & Stats */}
            <motion.div
                initial={{ x: -50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                className="w-full md:w-1/3 p-6 flex flex-col bg-white border-r border-stone-200 z-10 shadow-lg md:h-full overflow-y-auto"
            >
                <h1 className="text-3xl font-light text-charcoal mb-6">Create Space</h1>

                <div className="space-y-4 mb-8">
                    <label className="block text-sm font-medium text-stone-600">
                        Describe your dream home
                    </label>
                    <textarea
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        placeholder="E.g., A cozy 2-bedroom apartment with a large balcony connected to the living room..."
                        className="w-full p-4 rounded-xl border border-stone-200 focus:border-charcoal focus:ring-1 focus:ring-charcoal outline-none resize-none h-32 text-stone-700 bg-stone-50"
                    />
                    <button
                        onClick={handleGenerate}
                        disabled={loading || !prompt.trim()}
                        className={`w-full py-4 rounded-xl font-medium flex items-center justify-center space-x-2 transition-all
              ${loading || !prompt.trim()
                                ? 'bg-stone-200 text-stone-400 cursor-not-allowed'
                                : 'bg-charcoal text-cream hover:bg-stone-800 shadow-lg hover:shadow-xl transform hover:-translate-y-1'
                            }`}
                    >
                        {loading ? <Loader2 className="animate-spin" /> : <Send size={20} />}
                        <span>{loading ? "Generating Options..." : "Generate Layout"}</span>
                    </button>
                </div>

                {/* Selection Grid (Miniatures) */}
                {candidates.length > 0 && (
                    <div className="mb-8">
                        <h3 className="text-xs font-bold text-stone-400 uppercase tracking-wider mb-3">Select Design Candidate</h3>
                        <div className="grid grid-cols-3 gap-2">
                            {candidates.map((c) => (
                                <div
                                    key={c.id}
                                    onClick={() => handleSelectCandidate(c)}
                                    className={`relative rounded-lg overflow-hidden border-2 cursor-pointer transition-all ${selectedCandidateId === c.id ? 'border-charcoal ring-2 ring-charcoal/20' : 'border-stone-100 hover:border-stone-300'}`}
                                >
                                    <div className="h-20 bg-stone-100">
                                        {/* Mini Canvas */}
                                        <Canvas camera={{ position: [0, 50, 0], fov: 50 }}>
                                            <ambientLight intensity={0.5} />
                                            <directionalLight position={[10, 20, 10]} intensity={1.5} />
                                            <Suspense fallback={null}>
                                                <Model url={`${import.meta.env.VITE_API_URL}${c.model_url}`} />
                                            </Suspense>
                                        </Canvas>
                                    </div>
                                    <div className="absolute top-1 right-1 bg-white/90 backdrop-blur px-1.5 py-0.5 rounded text-[10px] font-bold shadow-sm">
                                        {c.score}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {error && (
                    <div className="p-4 bg-red-50 text-red-600 rounded-lg text-sm mb-6">
                        {error}
                    </div>
                )}

                {layoutSpec && stats && (
                    <div className="mt-0 bg-white p-6 rounded-2xl shadow-sm border border-stone-100">
                        <div className="flex items-center justify-between mb-6">
                            <h3 className="text-lg font-semibold text-stone-800 flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-emerald-500"></div>
                                Architectural Analysis
                            </h3>
                            <div className="px-3 py-1 bg-stone-100 rounded-full text-xs font-mono text-stone-600">
                                Score: {score}/100
                            </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            {/* Area Distribution */}
                            <div className="h-64 relative">
                                <p className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-2 text-center">Area Distribution</p>
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={layoutSpec.rooms}
                                            dataKey="area"
                                            nameKey="type"
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={60}
                                            outerRadius={80}
                                            paddingAngle={5}
                                            onMouseEnter={(_, index) => setHoveredRoomId(layoutSpec.rooms[index].id)}
                                            onMouseLeave={() => setHoveredRoomId(null)}
                                        >
                                            {layoutSpec.rooms.map((entry, index) => (
                                                <Cell
                                                    key={`cell-${index}`}
                                                    fill={entry.color || '#e5e7eb'}
                                                    stroke="none"
                                                    opacity={hoveredRoomId && hoveredRoomId !== entry.id ? 0.3 : 1}
                                                />
                                            ))}
                                        </Pie>
                                    </PieChart>
                                </ResponsiveContainer>
                                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                    <div className="text-center mt-6">
                                        <span className="block text-2xl font-bold text-stone-800">
                                            {hoveredRoomId ? Math.round(layoutSpec.rooms.find(r => r.id === hoveredRoomId)?.area || 0) : layoutSpec.rooms.reduce((a, b) => a + b.area, 0)}
                                        </span>
                                        <span className="text-[10px] text-stone-400 uppercase tracking-widest">
                                            {hoveredRoomId ? layoutSpec.rooms.find(r => r.id === hoveredRoomId)?.type : 'TOTAL SQFT'}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            {/* Scores */}
                            <div>
                                <p className="text-xs font-medium text-stone-400 uppercase tracking-wider mb-4">Performance Metrics</p>
                                <div className="space-y-4">
                                    {[
                                        { label: 'Efficiency', val: stats.efficiency, color: '#10b981' },
                                        { label: 'Privacy', val: stats.privacy, color: '#6366f1' },
                                        { label: 'Daylight', val: stats.daylight, color: '#f59e0b' },
                                        { label: 'Circulation', val: stats.circulation, color: '#ec4899' }
                                    ].map((stat, i) => (
                                        <div key={i}>
                                            <div className="flex justify-between text-xs mb-1">
                                                <span className="text-stone-600 font-medium">{stat.label}</span>
                                                <span className="text-stone-400">{stat.val}%</span>
                                            </div>
                                            <div className="h-2 w-full bg-stone-100 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full rounded-full transition-all duration-1000 ease-out"
                                                    style={{ width: `${stat.val}%`, backgroundColor: stat.color }}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Legend */}
                        <div className="mt-6 pt-6 border-t border-stone-100">
                            <div className="grid grid-cols-2 gap-3">
                                {layoutSpec.rooms.map((room, idx) => (
                                    <div
                                        key={idx}
                                        className={`flex items-center justify-between p-2 rounded-lg transition-colors cursor-pointer ${hoveredRoomId === room.id ? 'bg-stone-100 ring-1 ring-stone-300' : 'hover:bg-stone-50'}`}
                                        onMouseEnter={() => setHoveredRoomId(room.id)}
                                        onMouseLeave={() => setHoveredRoomId(null)}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div
                                                className="w-3 h-3 rounded-full"
                                                style={{ backgroundColor: room.color || '#e5e7eb' }}
                                            />
                                            <span className="text-sm text-stone-600 capitalize">{room.type}</span>
                                        </div>
                                        <span className="text-sm font-mono text-stone-400">{Math.round(room.area)} sqft</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                        <a
                            href={modelUrl}
                            download
                            className="mt-6 flex items-center justify-center text-sm text-charcoal hover:underline mt-4 cursor-pointer"
                        >
                            <Download size={14} className="mr-1" /> Download .PLY Model
                        </a>
                    </div>
                )}
            </motion.div>

            {/* Right Panel: 3D Visualization */}
            <div className="w-full md:w-2/3 h-[50vh] md:h-full bg-stone-100 relative">
                <Canvas camera={{ position: [20, 30, 20], fov: 45, far: 10000 }}>
                    <fog attach="fog" args={['#f5f5f4', 50, 10000]} />
                    <ambientLight intensity={0.5} />
                    <directionalLight position={[10, 20, 10]} intensity={1.5} />
                    <Suspense fallback={null}>
                        <Center>
                            {modelUrl && <Model url={modelUrl} />}

                            {/* Interactive Layer */}
                            {layoutSpec && layoutData && layoutSpec.rooms.map(room => (
                                <InteractiveRoom
                                    key={room.id}
                                    roomId={room.id}
                                    roomPoly={layoutData[room.id]}
                                    setHoveredRoomId={setHoveredRoomId}
                                />
                            ))}

                            {/* Highlight Layer */}
                            {/* Highlight Layer */}
                            {hoveredPoly && <RoomHighlight roomPoly={hoveredPoly} color={hoveredColor} />}

                            {/* 1-Meter Grid for Scale inside Center so it aligns with base */}
                            <Grid position={[0, -0.01, 0]} rotation={[Math.PI / 2, 0, 0]} args={[50, 50]} sectionSize={1} sectionThickness={1.5} cellThickness={0} sectionColor="#e5e7eb" fadeDistance={30} />
                        </Center>
                        {/* ContactShadows removed per user request */}                    </Suspense>

                    <OrbitControls makeDefault />
                </Canvas>

                {/* North Arrow UI */}
                <div className="absolute top-6 right-6 pointer-events-none">
                    <div className="w-12 h-12 bg-white rounded-full shadow-lg flex items-center justify-center border border-stone-200">
                        <div className="flex flex-col items-center">
                            <span className="text-[10px] font-bold text-red-500">N</span>
                            <div className="w-0.5 h-4 bg-stone-800 rounded-full"></div>
                        </div>
                    </div>
                </div>

                {/* Scale Legend UI */}
                <div className="absolute bottom-6 right-6 pointer-events-none">
                    <div className="bg-white/90 backdrop-blur px-3 py-2 rounded-lg shadow-sm border border-stone-200 flex items-center gap-3">
                        <span className="text-[10px] font-bold text-stone-400 uppercase tracking-wider">Scale</span>
                        <div className="flex flex-col items-center gap-1">
                            <div className="w-12 border-b-2 border-stone-800 relative">
                                <div className="absolute top-[-3px] left-0 w-0.5 h-1.5 bg-stone-800"></div>
                                <div className="absolute top-[-3px] right-0 w-0.5 h-1.5 bg-stone-800"></div>
                            </div>
                            <span className="text-[10px] font-medium text-stone-600">1 Grid = 1m</span>
                        </div>
                    </div>
                </div>

                {!modelUrl && !loading && (
                    <div className="absolute inset-0 flex flex-col items-center justify-center text-stone-400 pointer-events-none">
                        <div className="w-16 h-16 border-2 border-stone-300 rounded-full flex items-center justify-center mb-4">
                            <span className="text-2xl">3D</span>
                        </div>
                        <p>Your generated design will appear here</p>
                    </div>
                )}

                {loading && (
                    <div className="absolute inset-0 flex items-center justify-center bg-white/50 backdrop-blur-sm z-20">
                        <div className="text-center">
                            <Loader2 className="w-12 h-12 text-charcoal animate-spin mx-auto mb-4" />
                            <p className="text-charcoal font-medium">Architecting 3 Candidates...</p>
                            <p className="text-xs text-stone-500 mt-2">Computing Privacy & Daylight Analysis</p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Create;
