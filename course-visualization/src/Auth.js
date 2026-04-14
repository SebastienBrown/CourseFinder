import React, { useState, useEffect } from "react";
import { supabase } from "./supabaseClient";

export default function Auth({ onLogin, onShowUserInfo }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(""); // message state
  const [debugInfo, setDebugInfo] = useState(""); // debug info state
  const [isResetMode, setIsResetMode] = useState(false);
  const [resetSent, setResetSent] = useState(false);
  const [isSignUpMode, setIsSignUpMode] = useState(false);

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
      // Supabase's email enumeration protection returns a dummy user with no identities if the email already exists
      if (data?.user?.identities != null && data.user.identities.length === 0) {
        setMessage("This email is already registered. Please sign in.");
      } else {
        setMessage("Check your email to confirm your sign-up!");
      }
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

  const handleResetPassword = async () => {
    if (!email) {
      setMessage("Please enter your email to reset your password.");
      return;
    }

    setMessage("");
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}`,
    });

    if (error) {
      console.error("Reset Password Error:", error);
      if (error.message.includes("rate limit exceeded")) {
        setMessage("Email rate limit exceeded. Please wait a minute or two before trying again.");
      } else {
        setMessage(`Error: ${error.message}`);
      }
    } else {
      setResetSent(true);
      setMessage("Check your email for the password reset link!");
    }
  };

  if (isResetMode) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-[#f9f7fb] px-4">
        <div className="bg-white rounded-2xl shadow-lg p-10 max-w-lg w-full">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-[#3f1f69] mb-2">Reset Password</h1>
            <p className="text-gray-600 mb-6">Enter your email and we'll send you a recovery link.</p>

            <input
              className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-[#3f1f69] focus:border-transparent transition-all duration-200 placeholder-gray-500 mb-4"
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

            <button
              onClick={handleResetPassword}
              disabled={resetSent}
              className={`w-full px-6 py-3 text-white rounded-xl font-semibold shadow transition-all duration-200 ${resetSent ? 'bg-gray-400 cursor-not-allowed' : 'bg-[#3f1f69] hover:bg-[#311a4d] hover:shadow-lg'
                }`}
            >
              {resetSent ? "Email Sent" : "Send Recovery Link"}
            </button>

            <button
              onClick={() => {
                setIsResetMode(false);
                setResetSent(false);
                setMessage("");
              }}
              className="mt-6 w-full text-[#3f1f69] font-medium hover:underline text-sm"
            >
              Back to Sign In
            </button>

            {message && (
              <div className={`mt-4 p-3 rounded-xl border ${resetSent ? 'bg-green-50 border-green-200 text-green-600' : 'bg-red-50 border-red-200 text-red-600'}`}>
                <div className="text-sm">{message}</div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

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
          <h2 className="text-xl font-semibold text-gray-700">
            {isSignUpMode ? "Create an Account" : "Welcome Back"}
          </h2>
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
          
          {!isSignUpMode && (
            <div className="text-right">
              <button
                onClick={() => setIsResetMode(true)}
                className="text-sm text-[#3f1f69] hover:underline font-medium"
              >
                Forgot Password?
              </button>
            </div>
          )}
        </div>

        {/* Button */}
        <div className="mt-6">
          <button
            onClick={isSignUpMode ? signUp : signIn}
            className="w-full px-6 py-3 bg-[#3f1f69] text-white rounded-xl font-semibold shadow hover:bg-[#311a4d] transition-all duration-200 hover:shadow-lg"
          >
            {isSignUpMode ? "Sign Up" : "Sign In"}
          </button>
        </div>
        
        {/* Toggle Mode */}
        <div className="text-center mt-6">
          <p className="text-sm text-gray-600">
            {isSignUpMode ? "Already have an account?" : "Don't have an account?"}{" "}
            <button
              onClick={() => {
                setIsSignUpMode(!isSignUpMode);
                setMessage("");
              }}
              className="text-[#3f1f69] font-semibold hover:underline"
            >
              {isSignUpMode ? "Sign In" : "Sign Up"}
            </button>
          </p>
        </div>

        {/* Message */}
        {message && (
          <div className={`mt-4 p-3 rounded-xl border ${message.includes("Error") || message.includes("Invalid") ? 'bg-red-50 border-red-200 text-red-600' : 'bg-blue-50 border-blue-200 text-blue-600'}`}>
            <div className="text-sm">{message}</div>
          </div>
        )}
      </div>
    </div>
  );
}
