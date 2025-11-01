import React, { useState, useEffect } from "react";
import { supabase } from "./supabaseClient";

export default function Auth({ onLogin, onShowUserInfo }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(""); // message state
  const [debugInfo, setDebugInfo] = useState(""); // debug info state

  const checkUserInfo = async (user) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      if (!token) {
        console.error("No valid session token found");
        return false;
      }

      const backendUrl = process.env.REACT_APP_BACKEND_URL;
      const response = await fetch(`${backendUrl}/check_user_info`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        console.error("Failed to check user info");
        return false;
      }

      const data = await response.json();
      return data.has_info;
    } catch (error) {
      console.error("Error checking user info:", error);
      return false;
    }
  };

  const saveUserInfo = async (userInfo) => {
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
      
      if (!token) {
        throw new Error("No valid session token found");
      }

      const backendUrl = process.env.REACT_APP_BACKEND_URL;
      const response = await fetch(`${backendUrl}/save_user_info`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(userInfo),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to save user information");
      }

      return await response.json();
    } catch (error) {
      console.error("Error saving user info:", error);
      throw error;
    }
  };

  const signUp = async () => {
    setMessage("");
    const debugText = `SignUp Attempt - Email: ${email}, Password: ${password}`;
    setDebugInfo(debugText);
    console.log(debugText);

    const { data, error: signUpError } = await supabase.auth.signUp({ email, password });

    if (!signUpError) {
      setMessage("Check your email to confirm your sign-up!");
    } else if (signUpError.message.includes("User already registered")) {
      setMessage("This email is already registered. Please sign in.");
    } else {
      console.error("SignUp Error:", signUpError);
      setMessage(
        `Error: ${signUpError.message}` +
        (signUpError.code ? ` (Code: ${signUpError.code})` : "") +
        (signUpError.status ? ` (Status: ${signUpError.status})` : "")
      );
    }
  };

  const signIn = async () => {
    setMessage("");
    const debugText = `SignIn Attempt - Email: ${email}, Password: ${password}`;
    setDebugInfo(debugText);
    // console.log(debugText);

    const { data, error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (!signInError) {
      if (data.user && !data.user.confirmed_at) {
        setMessage("Please confirm your email before signing in.");
      } else {
        setMessage("");
        // Just proceed with login - App.js will handle checking for user info
        onLogin(data.user);
      }
    } else {
      console.error("SignIn Error:", signInError);
      if (signInError.message.includes("Invalid login credentials")) {
        setMessage(
          `Invalid email or password.` +
          (signInError.code ? ` (Code: ${signInError.code})` : "") +
          (signInError.status ? ` (Status: ${signInError.status})` : "")
        );
      } else {
        setMessage(
          `Error: ${signInError.message}` +
          (signInError.code ? ` (Code: ${signInError.code})` : "") +
          (signInError.status ? ` (Status: ${signInError.status})` : "")
        );
      }
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-[#f9f7fb] px-4">
      <div className="bg-white rounded-2xl shadow-lg p-10 max-w-lg w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-[#3f1f69] mb-2">
            The Visual Open Curriculum
          </h1>
          <h2 className="text-xl font-semibold text-gray-700 mb-4">Welcome Back</h2>
          <div className="bg-[#f9f7fb] border border-[#e8e2f2] rounded-xl p-4 mb-6">
            <div className="flex items-center justify-center space-x-2 mb-3">
              <svg className="w-5 h-5 text-[#3f1f69]" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <h3 className="text-sm font-semibold text-[#3f1f69]">First Time Here?</h3>
            </div>
            <div className="space-y-2 text-sm text-gray-600">
              <div className="flex items-center space-x-2" style={{ marginLeft: '5rem' }}>
                <span className="w-1.5 h-1.5 bg-[#3f1f69] rounded-full flex-shrink-0"></span>
                <span>Enter your email and password</span>
              </div>
              <div className="flex items-center space-x-2" style={{ marginLeft: '5rem' }}>
                <span className="w-1.5 h-1.5 bg-[#3f1f69] rounded-full flex-shrink-0"></span>
                <span>Click <strong>"Sign Up"</strong> for new accounts</span>
              </div>
              <div className="flex items-center space-x-2" style={{ marginLeft: '5rem' }}>
                <span className="w-1.5 h-1.5 bg-[#3f1f69] rounded-full flex-shrink-0"></span>
                <span>Check your email for verification link</span>
              </div>
            </div>
          </div>
        </div>

        {/* Form */}
        <div className="space-y-4">
          <div>
            <input
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#3f1f69] focus:border-transparent transition-all duration-200 placeholder-gray-500"
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div>
            <input
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#3f1f69] focus:border-transparent transition-all duration-200 placeholder-gray-500"
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
        </div>

        {/* Buttons */}
        <div className="flex flex-col sm:flex-row gap-3 mt-6">
          <button 
            onClick={signIn} 
            className="flex-1 px-6 py-3 bg-[#3f1f69] text-white rounded-xl font-semibold shadow hover:bg-[#311a4d] transition-all duration-200 hover:shadow-lg"
          >
            Sign In
          </button>
          <button 
            onClick={signUp} 
            className="flex-1 px-6 py-3 bg-[#5d3c85] text-white rounded-xl font-semibold shadow hover:bg-[#4b2f72] transition-all duration-200 hover:shadow-lg"
          >
            Sign Up
          </button>
        </div>

        {/* Message */}
        {message && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-xl">
            <div className="text-red-600 text-sm">{message}</div>
          </div>
        )}

        {/* Debug info */}
        {debugInfo && (
          <div className="text-sm text-gray-500 mt-4">
            {/* Debug Info: {debugInfo} */}
          </div>
        )}
      </div>
    </div>
  );
}
