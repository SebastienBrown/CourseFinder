import React, { useState } from "react";
import { Sparkles, X, Loader2, RefreshCw } from "lucide-react";
import { supabase } from "./supabaseClient";

// --- per-tab/session "seen" cache ---
const SEEN_KEY = "surprise_seen_codes";

function loadSeen() {
  try {
    return new Set(JSON.parse(sessionStorage.getItem(SEEN_KEY) || "[]"));
  } catch {
    return new Set();
  }
}

function saveSeen(seenSet) {
  sessionStorage.setItem(SEEN_KEY, JSON.stringify([...seenSet]));
}

function clearSeen() {
  sessionStorage.removeItem(SEEN_KEY);
}

const SurpriseButton = ({ semester /* e.g., "2425F" */ }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false); // covers initial + regenerate
  const [recommendation, setRecommendation] = useState(null);
  const [error, setError] = useState(null);

  // single fetcher used by initial click + regenerate
  const fetchRecommendation = async ({ openModal = true } = {}) => {
    setIsLoading(true);
    setError(null);

    try {
      const raw = process.env.REACT_APP_BACKEND_URL;
      if (!raw) throw new Error("Backend URL not configured");
      const backendUrl = raw.replace(/\/$/, "");

      // auth
      const {
        data: { session },
        error: sessionError,
      } = await supabase.auth.getSession();
      if (sessionError || !session)
        throw new Error("Please sign in to get recommendations");
      const token = session.access_token;

      // load seen codes for this tab/session
      const seen = loadSeen();

      // nonce nudges backend randomness (harmless if ignored)
      const body = {
        ...(semester ? { semester } : {}),
        exclude_codes: [...seen],
        nonce: Date.now(),
      };

      const res = await fetch(`${backendUrl}/surprise_recommendation`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      const maybeJson = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg =
          maybeJson?.error ||
          maybeJson?.details ||
          "Failed to get recommendation";
        throw new Error(msg);
      }

      setRecommendation(maybeJson);

      // mark returned course codes as seen for this session
      if (Array.isArray(maybeJson.course_codes)) {
        for (const code of maybeJson.course_codes) {
          if (code) seen.add(String(code).trim().toUpperCase());
        }
        saveSeen(seen);
      }

      if (openModal) setIsOpen(true);
    } catch (err) {
      console.error("Error getting surprise recommendation:", err);
      setRecommendation(null);
      setError(err.message || "Something went wrong");
      setIsOpen(true); // show error in modal
    } finally {
      setIsLoading(false);
    }
  };

  const handleSurpriseMe = () => fetchRecommendation({ openModal: true });
  const handleRegenerate = () => fetchRecommendation({ openModal: false });

  const closeModal = () => {
    setIsOpen(false);
    setRecommendation(null);
    setError(null);
  };

  const handleResetSeen = () => {
    clearSeen();
    setError(null);
    // Optionally trigger a new recommendation immediately:
    // fetchRecommendation({ openModal: false });
  };

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={handleSurpriseMe}
        disabled={isLoading}
        aria-busy={isLoading}
        className="fixed bottom-6 right-6 z-50 bg-gradient-to-r from-purple-500 to-pink-500 text-white p-4 rounded-full shadow-lg hover:shadow-xl transform transition-all duration-200 hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed"
        title="Get a surprising course recommendation!"
      >
        {isLoading ? (
          <Loader2 className="w-6 h-6 animate-spin" />
        ) : (
          <Sparkles className="w-6 h-6" />
        )}
      </button>

      {/* Modal */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          role="dialog"
          aria-modal="true"
        >
          <div className="bg-white rounded-lg max-w-md w-full max-h-[80vh] overflow-y-auto shadow-xl">
            {/* Header */}
            <div className="flex justify-between items-center p-6 border-b">
              <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-purple-500" />
                Surprise Recommendation
              </h2>
              <button
                onClick={closeModal}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Close"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 space-y-4">
              {error ? (
                <div className="text-center">
                  <div className="text-red-500 mb-2">
                    <p className="font-semibold">Oops! Something went wrong</p>
                    <p className="text-sm text-gray-600 mt-2">{error}</p>
                  </div>

                  {/* Show Reset link when we've exhausted unseen options */}
                  {/no unseen/i.test(error) && (
                    <button
                      onClick={handleResetSeen}
                      className="mt-2 text-sm text-purple-700 underline"
                    >
                      Reset suggestions for this session
                    </button>
                  )}
                </div>
              ) : recommendation ? (
                <>
                  {/* Course Info */}
                  <div className="bg-gradient-to-r from-purple-50 to-pink-50 p-4 rounded-lg border">
                    <h3 className="font-bold text-lg text-gray-900 mb-2">
                      {recommendation.course_codes?.join(" / ")} —{" "}
                      {recommendation.course_title}
                    </h3>
                    <div className="flex flex-wrap gap-2 mb-3">
                      {recommendation.department && (
                        <span className="text-xs px-2 py-1 rounded-full bg-purple-100 text-purple-700">
                          Dept: {recommendation.department}
                        </span>
                      )}
                      {recommendation.semester && (
                        <span className="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700">
                          Semester: {recommendation.semester}
                        </span>
                      )}
                    </div>
                    {recommendation.description && (
                      <p className="text-gray-700 text-sm">
                        {recommendation.description}
                      </p>
                    )}
                  </div>

                  {/* Surprise Connection */}
                  {recommendation.surprise_connection && (
                    <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                      <h4 className="font-semibold text-gray-900 mb-2 flex items-center gap-1">
                        <Sparkles className="w-4 h-4" />
                        Why this might surprise you:
                      </h4>
                      <p className="text-gray-700 text-sm">
                        {recommendation.surprise_connection}
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex items-center justify-center text-sm text-gray-600 h-16">
                  Loading…
                </div>
              )}

              {/* Actions: Regenerate + Close only */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleRegenerate}
                  disabled={isLoading}
                  className="flex-1 inline-flex items-center justify-center gap-2 border border-purple-300 text-purple-700 px-4 py-2 rounded hover:bg-purple-50 disabled:opacity-50"
                  title="Try a different pick"
                >
                  {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  Regenerate
                </button>
                <button
                  onClick={closeModal}
                  className="flex-1 bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default SurpriseButton;
