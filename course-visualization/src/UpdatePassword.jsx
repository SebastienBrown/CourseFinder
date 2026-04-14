import React, { useState } from "react";
import { supabase } from "./supabaseClient";

export default function UpdatePassword({ onComplete }) {
    const [password, setPassword] = useState("");
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);

    const handleUpdate = async (e) => {
        e.preventDefault();
        if (password.length < 6) {
            setMessage("Password must be at least 6 characters.");
            return;
        }

        setLoading(true);
        setMessage("");

        const { error } = await supabase.auth.updateUser({ password });

        if (error) {
            console.error("Update Password Error:", error);
            setMessage(`Error: ${error.message}`);
        } else {
            setMessage("Password updated successfully!");
            // Briefly show success then redirect/close
            setTimeout(() => {
                onComplete();
            }, 2000);
        }
        setLoading(false);
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-[#f9f7fb] px-4">
            <div className="bg-white rounded-2xl shadow-lg p-10 max-w-lg w-full">
                <div className="text-center mb-8">
                    <h1 className="text-3xl font-bold text-[#3f1f69] mb-2">Create New Password</h1>
                    <p className="text-gray-600">Please enter a new secure password for your account.</p>
                </div>

                <form onSubmit={handleUpdate} className="space-y-4">
                    <input
                        className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#3f1f69] focus:border-transparent transition-all duration-200 placeholder-gray-500"
                        type="password"
                        placeholder="New Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />

                    <button
                        type="submit"
                        disabled={loading}
                        className={`w-full px-6 py-3 text-white rounded-xl font-semibold shadow transition-all duration-200 ${loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-[#3f1f69] hover:bg-[#311a4d] hover:shadow-lg'
                            }`}
                    >
                        {loading ? "Updating..." : "Update Password"}
                    </button>

                    {message && (
                        <div className={`mt-4 p-3 rounded-xl border ${message.includes("successfully") ? 'bg-green-50 border-green-200 text-green-600' : 'bg-red-50 border-red-200 text-red-600'}`}>
                            <div className="text-sm">{message}</div>
                        </div>
                    )}
                </form>
            </div>
        </div>
    );
}
