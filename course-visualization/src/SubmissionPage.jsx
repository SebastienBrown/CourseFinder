import { useState } from "react";
import { supabase } from "./supabaseClient";
import { Link } from "react-router-dom";

export default function SubmissionPage() {
  const [category, setCategory] = useState("Question");
  const [content, setContent] = useState("");
  const [status, setStatus] = useState(null);
  const backendUrl = process.env.REACT_APP_BACKEND_URL;

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!content.trim()) {
      setStatus("⚠️ Please enter something.");
      return;
    }

    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;

      if (!token) {
        setStatus("❌ No valid session token found.");
        return;
      }

      const res = await fetch(`${backendUrl}/submit-feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          TYPE: category,
          content: content,
        }),
      });

      if (!res.ok) {
        const errText = await res.text();
        setStatus(`❌ Submission failed: ${errText}`);
        return;
      }

      // Clear input fields on success
      setCategory("Question");
      setContent("");
      setStatus("✅ Submission successful!");
    } catch (err) {
      console.error(err);
      setStatus("❌ An error occurred while submitting.");
    }

  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-6">
      <div className="w-full max-w-2xl space-y-6">
        {/* Back button */}
        <Link
          to="/"
          className="px-4 py-2 bg-gray-200 rounded-lg font-medium hover:bg-gray-300 transition"
        >
          ← Back to Graph
        </Link>

        {/* Submission Form */}
        <form
          onSubmit={handleSubmit}
          className="bg-white p-6 rounded-xl shadow w-full space-y-4"
        >
          <h1 className="text-2xl font-bold">Ask a Question!</h1>

          {/* Category Selector */}
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="w-full border rounded p-2"
          >
            <option>Question</option>
            <option>Request</option>
            <option>Bug</option>
          </select>

          {/* Content */}
          <textarea
            className="w-full border rounded p-2 min-h-[120px]"
            placeholder="Write your message here..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />

          {/* Submit Button */}
          <button
            type="submit"
            className="px-4 py-2 bg-purple-600 text-white rounded-lg font-semibold shadow hover:bg-purple-700 transition-all duration-200"
          >
            Submit
          </button>

          {/* Status message */}
          {status && <p className="text-sm">{status}</p>}
        </form>
      </div>
    </div>
  );
}
