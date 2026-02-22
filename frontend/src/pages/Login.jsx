import React from 'react';
import { signInWithPopup } from 'firebase/auth';
import { auth, googleProvider } from '../firebase';
import { useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';

const Login = () => {
    const navigate = useNavigate();
    const [email, setEmail] = React.useState("");
    const [password, setPassword] = React.useState("");
    const [isSignUp, setIsSignUp] = React.useState(false);
    const [error, setError] = React.useState(null);

    const location = useLocation();
    const from = location.state?.from?.pathname || '/dashboard';

    const handleGoogleLogin = async () => {
        setError(null);
        try {
            await signInWithPopup(auth, googleProvider);
            navigate(from, { replace: true });
        } catch (err) {
            console.error("Login failed:", err);
            setError(err.message.replace("Firebase: ", ""));
        }
    };

    const handleResetPassword = async () => {
        if (!email) {
            setError("Please enter your email address to reset password.");
            return;
        }
        try {
            const { sendPasswordResetEmail } = await import("firebase/auth");
            await sendPasswordResetEmail(auth, email);
            setError("Password reset email sent! Check your inbox.");
        } catch (err) {
            setError(err.message.replace("Firebase: ", ""));
        }
    };

    const handleEmailAuth = async (e) => {
        e.preventDefault();
        setError(null);
        try {
            const { createUserWithEmailAndPassword, signInWithEmailAndPassword, sendEmailVerification } = await import("firebase/auth");
            if (isSignUp) {
                const userCredential = await createUserWithEmailAndPassword(auth, email, password);
                await sendEmailVerification(userCredential.user);
                setError("Account created! Please verify your email.");
            } else {
                await signInWithEmailAndPassword(auth, email, password);
                navigate(from, { replace: true });
            }
        } catch (err) {
            console.error("Auth failed:", err);
            setError(err.message.replace("Firebase: ", ""));
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-cream">
            <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-white p-8 rounded-2xl shadow-xl max-w-md w-full text-center border border-stone-100"
            >
                <h2 className="text-3xl font-light text-charcoal mb-2">{isSignUp ? "Create Account" : "Welcome Back"}</h2>
                <p className="text-stone-500 mb-8">{isSignUp ? "Sign up to start designing" : "Sign in to access your designs"}</p>

                {error && (
                    <div className="mb-4 p-3 bg-red-50 text-red-600 text-sm rounded-lg border border-red-100">
                        {error}
                    </div>
                )}

                <form onSubmit={handleEmailAuth} className="space-y-4 mb-6 text-left">
                    <div>
                        <input
                            type="email"
                            placeholder="Email address"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="w-full p-3 border border-stone-200 rounded-lg focus:ring-2 focus:ring-stone-400 outline-none"
                            required
                        />
                    </div>
                    <div>
                        <input
                            type="password"
                            placeholder="Password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="w-full p-3 border border-stone-200 rounded-lg focus:ring-2 focus:ring-stone-400 outline-none"
                            required
                        />
                        {!isSignUp && (
                            <div className="flex justify-end mt-1">
                                <button
                                    type="button"
                                    onClick={handleResetPassword}
                                    className="text-xs text-stone-500 hover:text-stone-800 transition-colors"
                                >
                                    Forgot password?
                                </button>
                            </div>
                        )}
                    </div>
                    <button
                        type="submit"
                        className="w-full py-3 bg-charcoal text-white rounded-lg hover:bg-stone-800 transition-colors font-medium shadow-md"
                    >
                        {isSignUp ? "Sign Up" : "Sign In"}
                    </button>
                </form>

                <div className="relative mb-6">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-stone-200"></div>
                    </div>
                    <div className="relative flex justify-center text-sm">
                        <span className="px-2 bg-white text-stone-500">Or continue with</span>
                    </div>
                </div>

                <button
                    onClick={handleGoogleLogin}
                    className="w-full flex items-center justify-center space-x-3 px-6 py-3 border border-stone-300 rounded-lg hover:bg-stone-50 transition-colors shadow-sm mb-6"
                >
                    <img src="https://www.google.com/favicon.ico" alt="Google" className="w-5 h-5" />
                    <span className="text-charcoal font-medium">Google</span>
                </button>

                <p className="text-sm text-stone-500">
                    {isSignUp ? "Already have an account?" : "Don't have an account?"}{" "}
                    <button
                        onClick={() => setIsSignUp(!isSignUp)}
                        className="text-stone-800 font-semibold hover:underline"
                    >
                        {isSignUp ? "Sign In" : "Sign Up"}
                    </button>
                </p>
            </motion.div>
        </div>
    );
};

export default Login;
