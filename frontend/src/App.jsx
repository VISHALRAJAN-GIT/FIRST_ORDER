import React, { useState, useRef } from 'react';
import {
  Upload,
  FileText,
  Sparkles,
  Send,
  CheckCircle2,
  Loader2,
  ArrowRight,
  Download,
  ExternalLink
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import axios from 'axios';
import confetti from 'canvas-confetti';

const API_BASE = 'http://localhost:8000/api/resume';

function App() {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [isEnhancing, setIsEnhancing] = useState(false);
  const [enhancedData, setEnhancedData] = useState(null);
  const [isApplying, setIsApplying] = useState(false);
  const [jobUrl, setJobUrl] = useState('');
  const [applicationStatus, setApplicationStatus] = useState(null);

  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleEnhance = async () => {
    if (!file || !jobDescription) return;

    setIsEnhancing(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_description', jobDescription);

    try {
      const response = await axios.post(`${API_BASE}/enhance`, formData);
      setEnhancedData(response.data);
      setApplicationStatus('Enhanced successfully!');
    } catch (error) {
      console.error(error);
      alert('Failed to enhance resume.');
    } finally {
      setIsEnhancing(false);
    }
  };

  const handleApply = async () => {
    if (!jobUrl || !enhancedData) return;

    setIsApplying(true);
    const formData = new FormData();
    formData.append('job_url', jobUrl);
    formData.append('pdf_filename', enhancedData.pdf_filename);
    formData.append('personal_info', JSON.stringify({
      name: "User", // This could be dynamic
      email: "user@example.com"
    }));

    try {
      await axios.post(`${API_BASE}/apply`, formData);
      confetti({
        particleCount: 150,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#6366f1', '#a855f7', '#ec4899']
      });
      setApplicationStatus('Application Submitted Successfully!');
    } catch (error) {
      console.error(error);
      alert('Application failed.');
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="min-h-screen p-4 md:p-8 flex flex-col items-center">
      {/* Header */}
      <motion.header
        initial={{ y: -50, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="w-full max-w-6xl flex justify-between items-center mb-12"
      >
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Sparkles className="text-white" size={24} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight">AI Agent <span className="text-indigo-400">Apply</span></h1>
        </div>
        <div className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-400">
          <a href="#" className="hover:text-white transition-colors">How it works</a>
          <a href="#" className="hover:text-white transition-colors">Documentation</a>
          <button className="px-5 py-2 rounded-full border border-slate-700 hover:border-slate-500 transition-colors">Sign In</button>
        </div>
      </motion.header>

      <main className="w-full max-w-5xl grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left Column: Input */}
        <div className="flex flex-col gap-6">
          <motion.div
            initial={{ x: -30, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            className="glass-card p-6 md:p-8"
          >
            <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
              <Upload size={20} className="text-indigo-400" />
              Upload Source
            </h2>

            <div className="space-y-6">
              {/* File Upload */}
              <div
                onClick={() => fileInputRef.current.click()}
                className="group border-2 border-dashed border-slate-700 hover:border-indigo-500/50 rounded-2xl p-8 transition-all cursor-pointer bg-white/5 flex flex-col items-center justify-center gap-4"
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                  accept=".pdf"
                />
                <div className="p-4 bg-indigo-500/10 rounded-full group-hover:scale-110 transition-transform">
                  <FileText className="text-indigo-400" size={32} />
                </div>
                <div className="text-center">
                  <p className="font-medium">{file ? file.name : 'Upload your resume'}</p>
                  <p className="text-xs text-slate-500 mt-1">PDF only (max 5MB)</p>
                </div>
              </div>

              {/* Job Description */}
              <div>
                <label className="label">Job Description</label>
                <textarea
                  rows="6"
                  placeholder="Paste the job requirements here..."
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                />
              </div>

              <button
                onClick={handleEnhance}
                disabled={isEnhancing || !file || !jobDescription}
                className="btn-primary w-full justify-center py-4"
              >
                {isEnhancing ? (
                  <>
                    <Loader2 className="animate-spin" size={20} />
                    Analyzing with AI...
                  </>
                ) : (
                  <>
                    Enhance Resume
                    <Sparkles size={18} />
                  </>
                )}
              </button>
            </div>
          </motion.div>
        </div>

        {/* Right Column: Result & Automation */}
        <div className="flex flex-col gap-6">
          <AnimatePresence mode="wait">
            {!enhancedData ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="glass-card p-8 flex flex-col items-center justify-center text-center h-full border-dashed"
              >
                <div className="w-20 h-20 rounded-full bg-slate-800/50 flex items-center justify-center mb-6">
                  <CheckCircle2 size={40} className="text-slate-600" />
                </div>
                <h3 className="text-lg font-medium text-slate-400">Waiting for analysis</h3>
                <p className="text-sm text-slate-500 mt-2 max-w-[240px]">Upload your resume and the job description to see the magic happen.</p>
              </motion.div>
            ) : (
              <motion.div
                key="result"
                initial={{ x: 30, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                className="glass-card p-6 md:p-8 flex flex-col gap-6"
              >
                <div className="flex justify-between items-center">
                  <h2 className="text-xl font-semibold flex items-center gap-2">
                    <Sparkles size={20} className="text-indigo-400" />
                    Enhanced Result
                  </h2>
                  <div className="flex gap-2">
                    <button className="p-2 hover:bg-white/10 rounded-lg transition-colors text-slate-400 hover:text-white">
                      <Download size={20} />
                    </button>
                    <button className="p-2 hover:bg-white/10 rounded-lg transition-colors text-slate-400 hover:text-white">
                      <ExternalLink size={20} />
                    </button>
                  </div>
                </div>

                <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-800 h-[300px] overflow-y-auto text-sm text-slate-300 whitespace-pre-wrap leading-relaxed">
                  {enhancedData.enhanced_text}
                </div>

                <div className="space-y-4 pt-4 border-t border-slate-800">
                  <div>
                    <label className="label">Application URL</label>
                    <div className="flex gap-2">
                      <input
                        type="url"
                        placeholder="https://company.com/jobs/123"
                        value={jobUrl}
                        onChange={(e) => setJobUrl(e.target.value)}
                      />
                    </div>
                  </div>

                  <button
                    onClick={handleApply}
                    disabled={isApplying || !jobUrl}
                    className="btn-primary w-full justify-center bg-none bg-indigo-500 hover:bg-indigo-600 shadow-indigo-500/20"
                  >
                    {isApplying ? (
                      <>
                        <Loader2 className="animate-spin" size={20} />
                        Automating Browser...
                      </>
                    ) : (
                      <>
                        Apply to Job
                        <Send size={18} />
                      </>
                    )}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Status Tracker */}
          {applicationStatus && (
            <motion.div
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              className="bg-emerald-500/10 border border-emerald-500/20 p-4 rounded-xl flex items-center gap-3 text-emerald-400"
            >
              <CheckCircle2 size={20} />
              <span className="text-sm font-medium">{applicationStatus}</span>
            </motion.div>
          )}
        </div>
      </main>

      {/* Decorative background elements */}
      <div className="fixed top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="fixed bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-600/10 rounded-full blur-[120px] pointer-events-none" />
    </div>
  );
}

export default App;
