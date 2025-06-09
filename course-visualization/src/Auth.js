import React, { useState } from "react";
import { supabase } from "./supabaseClient";

export default function Auth({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState(""); // message state
  const [debugInfo, setDebugInfo] = useState(""); // debug info state

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

      {/* Show debug info */}
      {debugInfo && (
        <div className="text-sm text-gray-500 mt-4">
          Debug Info: {debugInfo}
        </div>
      )}
    </div>
  );
}
