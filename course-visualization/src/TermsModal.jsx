import React, { useEffect, useRef, useState } from "react";
import { supabase } from "./supabaseClient"; // adjust import if using another auth
import { useLocation } from 'react-router-dom';

export default function TermsModal() {
  const dialogRef = useRef(null);
  const [checked, setChecked] = useState(false);
  const [loading, setLoading] = useState(false);
  const backendUrl=process.env.REACT_APP_BACKEND_URL;
  const [isOpen, setIsOpen] = useState(null); // null = loading

  // Inside TermsModal component:
//const location = useLocation(); 

  // Disable scrolling when modal is loaded
  useEffect(() => {
    const { overflow } = document.body.style;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = overflow;
    };
  }, []);

  // Focus first element on mount
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const titleEl = dialog.querySelector("#terms-title");
    titleEl && titleEl.focus();
  }, []);

  useEffect(() => {
    console.log("useEffect running - checking terms");
    const checkTerms = async () => {
      try {

      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
  
      if (!token) {
        console.error("No valid session token found");
        return;
      }

      const res = await fetch(`${backendUrl}/check-terms`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });

        const data = await res.json();
        console.log(data);
        setIsOpen(!data.accepted); // show modal if not accepted
      } catch (err) {
        console.error(err);
        setIsOpen(true); // fallback: show modal
      }
    };
    checkTerms();
  }, []);


  const handleAccept = async () => {
    if (!checked) return;
    setLoading(true);
    try {
      const { data: { session } } = await supabase.auth.getSession();
      const token = session?.access_token;
  
      if (!token) {
        console.error("No valid session token found");
        return;
      }

      const res = await fetch(`${backendUrl}/accept-terms`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error("Failed to accept terms");
  
      setIsOpen(false); // immediately hide modal after backend update
      document.body.style.overflow = ""; // re-enable scrolling
    } catch (err) {
      console.error(err);
      alert("Unable to save acceptance. Please try again.");
    } finally {
      setLoading(false);
    }
  };


  if (isOpen === null) return null; // wait for backend check
  if (!isOpen) return null; // already accepted


  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="terms-title"
      aria-describedby="terms-desc"
    >
      <div
        ref={dialogRef}
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl outline-none"
      >
        <h2
          id="terms-title"
          tabIndex={-1}
          className="text-xl font-semibold tracking-tight"
        >
          Terms & Conditions
        </h2>

        <div id="terms-desc" className="mt-4 space-y-3 text-sm leading-6 text-gray-700">
          <p>
            By proceeding, you agree to our Terms & Conditions as listed below.
          </p>
          <ul className="list-disc pl-5">
            <li>The course history data we collect is stored anonymously and will only be used for research purposes..</li>
            <li>Users may upload a transcript for simplified onboarding: no grade information will be stored.</li>
          </ul>
        </div>

        <label className="mt-6 flex select-none items-start gap-3 rounded-xl border border-gray-200 p-4 hover:bg-gray-50">
          <input
            type="checkbox"
            checked={checked}
            onChange={(e) => setChecked(e.target.checked)}
            className="mt-1 h-4 w-4 rounded border-gray-300"
          />
          <span className="text-sm text-gray-800">
            I have read and agree to the <a className="strong font-medium">Terms & Conditions</a>.
          </span>
        </label>

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            onClick={handleAccept}
            disabled={!checked || loading}
            className={`rounded-2xl px-4 py-2 text-sm font-medium text-white shadow transition active:scale-[.98] ${
              checked
                ? "bg-black hover:bg-gray-800"
                : "bg-gray-300 cursor-not-allowed"
            }`}
            aria-disabled={!checked || loading}
          >
            {loading ? "Saving..." : "Accept & Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
