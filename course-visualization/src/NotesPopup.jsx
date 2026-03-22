import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, Plus, Trash2, Send, Save, CheckCircle } from 'lucide-react';
import { supabase } from './supabaseClient';
import html2canvas from 'html2canvas';

const FY_QUESTIONS = [
    "Are there particular skills or knowledge you would like to gain this semester? If so, what are they?",
    "What were your favorite topics to study in high school?",
    "Are there any topics you did not study in high school that you would like to explore in college?",
    "What courses are you considering taking in your first semester? Do these courses build on your prior knowledge? Are you exploring a completely new area?"
];

const OTHER_QUESTIONS = [
    "Are there particular skills or knowledge you would like to gain this semester? If so, what are they?",
    "What have been your favorite courses so far? Why were they your favorite?",
    "Consider the courses you plan on taking this semester. How will they help you gain the skills and knowledge you would like to gain this semester?",
    "Where do these intended courses fall on your map in relation to the courses you have already taken?",
    "Is there any area you have not explored yet that you would like to explore? Which areas that you have not yet considered will help you reach your intended goals?"
];

export default function NotesPopup({ isOpen, onClose, graphRef, classYear }) {
    const [predefinedResponses, setPredefinedResponses] = useState({});
    const [customQna, setCustomQna] = useState([]);
    const [personalNotes, setPersonalNotes] = useState("");
    const [advisorEmail, setAdvisorEmail] = useState("");
    const [saveStatus, setSaveStatus] = useState("Saved");
    const [isSending, setIsSending] = useState(false);
    const backendUrl = process.env.REACT_APP_BACKEND_URL;
    const saveTimeoutRef = useRef(null);

    // Determine if student is a First Year
    const isFirstYear = React.useMemo(() => {
        if (!classYear) return false;
        const now = new Date();
        const year = now.getFullYear();
        const month = now.getMonth();

        const targetFY = month < 5 ? year + 3 : year + 4;
        return parseInt(classYear) >= targetFY;
    }, [classYear]);

    const activeQuestions = isFirstYear ? FY_QUESTIONS : OTHER_QUESTIONS;

    const saveToSupabase = useCallback(async (payload) => {
        try {
            setSaveStatus("Saving...");
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) return;

            const res = await fetch(`${backendUrl}/save_user_notes`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session.access_token}`
                },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                setSaveStatus("Saved");
            } else {
                setSaveStatus("Error saving");
            }
        } catch (err) {
            console.error(err);
            setSaveStatus("Offline");
        }
    }, [backendUrl]);

    const loadNotes = useCallback(async () => {
        try {
            const { data: { session } } = await supabase.auth.getSession();
            if (!session) return;

            // Try Supabase first
            const res = await fetch(`${backendUrl}/get_user_notes`, {
                headers: { "Authorization": `Bearer ${session.access_token}` }
            });

            if (res.ok) {
                const data = await res.json();
                if (data.id) {
                    setPredefinedResponses(data.predefined_responses || {});
                    setCustomQna(data.custom_qna || []);
                    setPersonalNotes(data.personal_notes || "");
                    return;
                }
            }

            // Fallback to localStorage if Supabase has nothing
            const localData = localStorage.getItem('user_notes_draft');
            if (localData) {
                const parsed = JSON.parse(localData);
                setPredefinedResponses(parsed.predefined_responses || {});
                setCustomQna(parsed.custom_qna || []);
                setPersonalNotes(parsed.personal_notes || "");
            }
        } catch (err) {
            console.error("Error loading notes:", err);
        }
    }, [backendUrl]);

    // 1. Initial Load (Supabase + LocalStorage fallback)
    useEffect(() => {
        if (isOpen) {
            loadNotes();
        }
    }, [isOpen, loadNotes]);

    // 2. Autosave Logic (Local Fast, DB Debounced)
    useEffect(() => {
        if (!isOpen) return;

        const dataToSave = {
            predefined_responses: predefinedResponses,
            custom_qna: customQna,
            personal_notes: personalNotes
        };

        // Immediate local save
        localStorage.setItem('user_notes_draft', JSON.stringify(dataToSave));
        setSaveStatus("Typing...");

        // Debounced DB save
        if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
        saveTimeoutRef.current = setTimeout(() => {
            saveToSupabase(dataToSave);
        }, 3000);

        return () => {
            if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
        };
    }, [predefinedResponses, customQna, personalNotes, isOpen, saveToSupabase]);

    // 1.5 Sync on Tab Close
    useEffect(() => {
        const handleBeforeUnload = () => {
            if (saveStatus !== "Saved") {
                const dataToSave = {
                    predefined_responses: predefinedResponses,
                    custom_qna: customQna,
                    personal_notes: personalNotes
                };

                saveToSupabase(dataToSave);
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => window.removeEventListener('beforeunload', handleBeforeUnload);
    }, [predefinedResponses, customQna, personalNotes, saveStatus, saveToSupabase]);

    // 3. Handlers
    const handlePredefinedChange = (question, value) => {
        setPredefinedResponses(prev => ({ ...prev, [question]: value }));
    };

    const addCustomQna = () => {
        setCustomQna(prev => [...prev, { question: "", answer: "" }]);
    };

    const updateCustomQna = (index, field, value) => {
        const updated = [...customQna];
        updated[index][field] = value;
        setCustomQna(updated);
    };

    const removeCustomQna = (index) => {
        setCustomQna(prev => prev.filter((_, i) => i !== index));
    };

    const handleSendToAdvisor = async () => {
        if (!advisorEmail) {
            alert("Please enter an advisor email.");
            return;
        }

        setIsSending(true);
        try {
            const { data: { session } } = await supabase.auth.getSession();

            // Capture Screenshot
            // 1. Capture High-Quality Screenshot
            let screenshotUrl = "";
            let fileName = "";
            if (graphRef && graphRef.current) {
                const canvas = await html2canvas(graphRef.current, {
                    scale: 2, // High quality
                    useCORS: true
                });

                // Convert to Blob for upload
                const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
                fileName = `report_${session.user.id}_${Date.now()}.png`;

                // 2. Upload to Supabase Storage (Private bucket 'reports' recommended)
                const { data, error: uploadError } = await supabase.storage
                    .from('reports')
                    .upload(fileName, blob, { contentType: 'image/png', upsert: true });

                if (uploadError) {
                    console.error("Supabase Upload Error:", uploadError);
                } else {
                    // Create a Signed URL (valid for 5 minutes / 300 seconds)
                    const { data: { signedUrl }, error: signedUrlError } = await supabase.storage
                        .from('reports')
                        .createSignedUrl(fileName, 300);

                    if (signedUrlError) {
                        console.error("Signed URL Error:", signedUrlError);
                    } else {
                        screenshotUrl = signedUrl;
                    }
                }
            }

            const res = await fetch(`${backendUrl}/email_to_advisor`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session.access_token}`
                },
                body: JSON.stringify({
                    email: advisorEmail,
                    notes: { predefined: predefinedResponses, custom: customQna },
                    screenshot_url: screenshotUrl,
                    file_name: fileName
                })
            });

            const result = await res.json();
            if (res.ok) {
                console.log("--- SUCCESS: Secure email trigger (with temporary signed URL) sent to GitHub Actions ---");
                alert("Email request sent! (Note: The screenshot link is temporary and will be deleted after the email is sent)");
            } else {
                const details = result.details ? ` (${result.details})` : "";
                console.error("Failed to trigger email:", result);
                alert("Failed to send email." + details);
            }
        } catch (err) {
            console.error(err);
            alert("Error sending email.");
        } finally {
            setIsSending(false);
        }
    };

    const handleClose = () => {
        // Final force save on exit
        saveToSupabase({ predefined_responses: predefinedResponses, custom_qna: customQna, personal_notes: personalNotes });
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100] p-4">
            <div className="bg-white w-full max-w-3xl max-h-[90vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden">

                {/* Header */}
                <div className="px-6 py-4 bg-purple-700 text-white flex justify-between items-center shrink-0">
                    <div>
                        <h2 className="text-xl font-bold">Academic Notes</h2>
                        <div className="flex items-center gap-1.5 text-xs text-purple-200 mt-1">
                            {saveStatus === "Saved" ? <CheckCircle className="w-3 h-3 text-green-400" /> : <Save className="w-3 h-3 animate-pulse" />}
                            <span>{saveStatus}</span>
                        </div>
                    </div>
                    <button onClick={handleClose} className="p-1 hover:bg-purple-600 rounded-full transition-colors">
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 overflow-y-auto space-y-8">

                    <div className="bg-purple-50 p-4 rounded-xl border border-purple-100">
                        <p className="text-sm text-purple-800 leading-relaxed font-medium">
                            Use this section to organize your thoughts before meeting with your advisor. Your answers are saved automatically and can be sent as a report along with a screenshot of your current course graph.
                        </p>
                    </div>

                    {/* Predefined Questions */}
                    <section className="space-y-4">
                        <h3 className="text-lg font-bold text-gray-800 border-b pb-2">Advisor Questions ({isFirstYear ? "First Year" : "Other Years"})</h3>
                        {activeQuestions.map((q, idx) => (
                            <div key={idx} className="space-y-1.5">
                                <label className="text-sm font-semibold text-gray-600">{q}</label>
                                <textarea
                                    className="w-full border border-gray-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all outline-none min-h-[80px]"
                                    placeholder="Type your answer here..."
                                    value={predefinedResponses[q] || ""}
                                    onChange={(e) => handlePredefinedChange(q, e.target.value)}
                                />
                            </div>
                        ))}
                    </section>

                    {/* Custom Q&A */}
                    <section className="space-y-4">
                        <div className="flex justify-between items-center border-b pb-2">
                            <h3 className="text-lg font-bold text-gray-800">Custom Questions</h3>
                            <button
                                onClick={addCustomQna}
                                className="flex items-center gap-1 text-sm bg-purple-100 text-purple-700 px-3 py-1.5 rounded-lg hover:bg-purple-200 transition-colors font-semibold"
                            >
                                <Plus className="w-4 h-4" /> Add Question
                            </button>
                        </div>
                        {customQna.map((item, idx) => (
                            <div key={idx} className="bg-gray-50 p-4 rounded-xl space-y-3 relative group border border-gray-100">
                                <button
                                    onClick={() => removeCustomQna(idx)}
                                    className="absolute top-2 right-2 text-gray-400 hover:text-red-500 transition-colors"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                                <input
                                    className="w-full bg-transparent border-0 border-b border-gray-200 focus:border-purple-500 transition-all outline-none text-sm font-semibold py-1"
                                    placeholder="Enter your custom question..."
                                    value={item.question}
                                    onChange={(e) => updateCustomQna(idx, 'question', e.target.value)}
                                />
                                <textarea
                                    className="w-full bg-white border border-gray-200 rounded-lg p-2.5 text-sm focus:ring-2 focus:ring-purple-500 transition-all outline-none min-h-[60px]"
                                    placeholder="Type your answer here..."
                                    value={item.answer}
                                    onChange={(e) => updateCustomQna(idx, 'answer', e.target.value)}
                                />
                            </div>
                        ))}
                    </section>

                    {/* Personal Notes */}
                    <section className="space-y-4">
                        <h3 className="text-lg font-bold text-gray-800 border-b pb-2">Personal Notes</h3>
                        <textarea
                            className="w-full border border-gray-200 rounded-lg p-3 text-sm focus:ring-2 focus:ring-purple-500 transition-all outline-none min-h-[150px]"
                            placeholder="Jot down anything else you want to remember..."
                            value={personalNotes}
                            onChange={(e) => setPersonalNotes(e.target.value)}
                        />
                    </section>
                </div>

                {/* Footer */}
                <div className="p-6 bg-gray-50 border-t shrink-0">
                    <div className="max-w-md mx-auto sm:mx-0">
                        <label className="text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">Advisor Email</label>
                        <div className="flex gap-2 mt-1">
                            <input
                                type="email"
                                className="flex-grow border border-gray-300 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-purple-500 transition-all outline-none"
                                placeholder="advisor@school.edu"
                                value={advisorEmail}
                                onChange={(e) => setAdvisorEmail(e.target.value)}
                            />
                            <button
                                disabled={isSending}
                                onClick={handleSendToAdvisor}
                                className="flex items-center gap-2 bg-purple-600 text-white px-6 py-2 rounded-lg font-bold hover:bg-purple-700 transition-all disabled:opacity-50 shadow-md whitespace-nowrap"
                            >
                                {isSending ? "Sending..." : "Send to Advisor"}
                                <Send className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
