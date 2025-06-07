// src/Auth.js
import React, { useState } from "react";
import { supabase } from "./supabaseClient";

export default function Auth({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(""); // NEW: message state

  const signIn = async () => {
    setMessage(""); // Clear previous message
    const { error, data } = await supabase.auth.signInWithPassword({ email, password });
    if (!error) {
      onLogin(data.user);
    } else {
      setMessage(error.message);
    }
  };

  const signUp = async () => {
    setMessage("");
  
    // First, try to sign in to check if user already exists and confirmed
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
  
    if (!signInError) {
      // User already exists and password matches → prompt to log in
      setMessage("This email is already registered. You are now signed in.");
      return;
    } else if (signInError.message.includes("Invalid login credentials")) {
      // User may exist but wrong password → block sign up and prompt to log in
      setMessage("This email is already registered. Please sign in withb correct login credentials.");
      return;
    }
  
    // If we got here, assume user does not exist or is unconfirmed → proceed with sign up
    const { error: signUpError } = await supabase.auth.signUp({ email, password });
  
    if (!signUpError) {
      setMessage("Check your email to confirm sign up!");
    } else {
      setMessage(signUpError.message);
    }
  };

  return (
    <div className="p-4 max-w-md mx-auto">
      <h2 className="text-xl font-semibold mb-4">Login or Sign Up</h2>
      <input
        className="border p-2 w-full mb-2"
        type="email"
        placeholder="Email"
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        className="border p-2 w-full mb-2"
        type="password"
        placeholder="Password"
        onChange={(e) => setPassword(e.target.value)}
      />
      <div className="flex gap-2 mb-2">
        <button onClick={signIn} className="bg-purple-600 text-white px-4 py-2 rounded">Sign In</button>
        <button onClick={signUp} className="bg-gray-300 px-4 py-2 rounded">Sign Up</button>
      </div>
      {message && <div className="text-red-600 mt-2">{message}</div>} {/* Show message */}
    </div>
  );
}
