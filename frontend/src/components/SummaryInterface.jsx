import React, { useState } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { FileText, AlertTriangle, Loader2, RefreshCw } from 'lucide-react';

const SummaryInterface = ({ documentId, onReset }) => {
  const [summary, setSummary] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerateSummary = async () => {
    if (!documentId) {
      setError('Please upload a document first to generate a summary.');
      return;
    }

    const cacheKey = `summary_${documentId}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      setSummary(cached);
      return;
    }

    setIsLoading(true);
    setError('');
    setSummary('');

    try {
      const response = await axios.post(`${API_URL}/generate/summary`, {
        document_id: documentId
      });

      if (response.data.summary) {
        setSummary(response.data.summary);
        localStorage.setItem(cacheKey, response.data.summary);
      } else {
        setError('No summary was generated.');
      }
    } catch (err) {
      console.error(err);
      if (err.response?.status === 429) {
        setError('The AI is taking a breather to prevent server overload! Please wait 60 seconds before generating the next item.');
      } else {
        setError(err.response?.data?.detail || 'Failed to generate summary. Is the backend running?');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] bg-white/60 backdrop-blur-2xl rounded-3xl shadow-[0_8px_32px_0_rgba(37,99,235,0.15)] border border-white/80 overflow-hidden">
      <div className="p-4 border-b border-white/80 bg-white/80 flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <div className="bg-blue-100 p-1.5 rounded-lg shadow-sm border border-blue-200">
            <FileText className="w-5 h-5 text-blue-600" />
          </div>
          <h3 className="font-bold text-slate-800">Document Summary</h3>
        </div>
        <div className="flex items-center space-x-3">
          {error && (
            <div className="text-xs text-red-600 flex items-center bg-red-50 border border-red-100 px-2 py-1 rounded max-w-sm">
              <AlertTriangle className="w-3 h-3 mr-1 flex-shrink-0" />
              <span className="truncate">{error}</span>
            </div>
          )}
          <button 
            onClick={onReset}
            className="flex items-center space-x-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 bg-white hover:bg-slate-50 border border-slate-200 px-2.5 py-1.5 rounded-lg shadow-sm transition-all active:scale-95"
            title="Reset Summary"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset Summary</span>
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 bg-transparent">
        {!summary && !isLoading && (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
            <div className="w-16 h-16 bg-blue-50 rounded-2xl flex items-center justify-center shadow-sm border border-blue-100 mb-2">
              <FileText className="w-8 h-8 text-blue-500" />
            </div>
            <h4 className="text-lg font-semibold text-slate-800">Ready to Summarize</h4>
            <p className="text-sm text-slate-500 max-w-sm">
              Click the button below to generate a concise, AI-powered summary of your document's key concepts.
            </p>
          </div>
        )}

        {isLoading && (
          <div className="h-full flex flex-col items-center justify-center text-center space-y-4">
            <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
            <p className="text-sm text-slate-500">Analyzing document and generating summary...</p>
          </div>
        )}

        {summary && !isLoading && (
          <div className="prose prose-slate max-w-none animate-fade-in-up bg-white/80 p-6 rounded-2xl shadow-sm border border-white/80 text-slate-800 leading-relaxed space-y-4">
            <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{summary}</ReactMarkdown>
          </div>
        )}
      </div>

      <div className="p-4 bg-white/80 border-t border-white/80 backdrop-blur-md flex justify-center">
        <button
          onClick={handleGenerateSummary}
          disabled={isLoading || !documentId}
          className="flex items-center justify-center px-6 py-3 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg active:scale-95 w-full sm:w-auto font-medium"
        >
          <FileText className="w-5 h-5 mr-2" />
          {isLoading ? 'Generating...' : 'Generate PDF Summary ✨'}
        </button>
      </div>
    </div>
  );
};

export default SummaryInterface;
