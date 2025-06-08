import React, { useState } from "react";
import { supabase } from "./supabaseClient";

export default function Auth({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(""); // NEW: message state

  const signUp = async () => {
    setMessage("");

    const { data, error: signUpError } = await supabase.auth.signUp({ email, password });

    if (!signUpError) {
      setMessage("Check your email to confirm your sign-up!");
    } else if (signUpError.message.includes("User already registered")) {
      // User exists — prompt to log in instead
      setMessage("This email is already registered. Please sign in.");
    } else {
      console.error("SignUp Error:", signUpError); // Log full error for debugging
      setMessage(`Error: ${signUpError.message} (Status: ${signUpError.status || 'unknown'})`);
    }
  };

  const signIn = async () => {
    setMessage("");

    console.log("Attempting signIn with:", email, password); // Helpful debug log

    const { data, error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (!signInError) {
      if (data.user && !data.user.confirmed_at) {
        // User exists but not confirmed
        setMessage("Please confirm your email before signing in.");
      } else {
        // Successful login
        setMessage("");
        onLogin(data.user);
      }
    } else {
      console.error("SignIn Error:", signInError); // Log full error for debugging

      if (signInError.message.includes("Invalid login credentials")) {
        setMessage(`Invalid email or password. (Status: ${signInError.status || 'unknown'})`);
      } else {
        setMessage(`Error: ${signInError.message} (Status: ${signInError.status || 'unknown'})`);
      }
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
