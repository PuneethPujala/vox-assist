import React, { createContext, useContext, useEffect, useState } from "react";
import { auth } from "../firebase";
import { onAuthStateChanged } from "firebase/auth";

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
    const [currentUser, setCurrentUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, (user) => {
            setCurrentUser(user);
            setLoading(false);
        });

        // Timeout fallback in case Firebase config is missing/wrong
        const timer = setTimeout(() => {
            setLoading(false);
        }, 5000);

        return () => {
            unsubscribe();
            clearTimeout(timer);
        };
    }, []);

    const value = {
        currentUser,
        loading
    };

    return (
        <AuthContext.Provider value={value}>
            {loading ? <div className="min-h-screen flex items-center justify-center bg-cream text-charcoal">Loading VOX-ASSIST...</div> : children}
        </AuthContext.Provider>
    );
};
