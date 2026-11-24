import React, { useState } from 'react';
import FileUpload from './components/FileUpload';
import ChatInterface from './components/ChatInterface';
import QuizInterface from './components/QuizInterface';
import FlashcardInterface from './components/FlashcardInterface';
import SummaryInterface from './components/SummaryInterface';
import FeatureTabs from './components/FeatureTabs';
import { BookOpen, Sparkles, RefreshCw } from 'lucide-react';
import axios from 'axios';
import 'katex/dist/katex.min.css';

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");

function App() {
  const [documentId, setDocumentId] = useState(null);
  const [activeTab, setActiveTab] = useState('chat');
  const [globalKey, setGlobalKey] = useState(0);
  const [tabKeys, setTabKeys] = useState({ chat: 0, quizzes: 0, flashcards: 0, summary: 0 });

  const handleTabReset = (tabName) => {
    if (documentId) {
      if (tabName === 'summary') localStorage.removeItem(`summary_${documentId}`);
      if (tabName === 'quizzes') localStorage.removeItem(`quiz_${documentId}`);
      if (tabName === 'flashcards') localStorage.removeItem(`flashcards_${documentId}`);
    }
    setTabKeys(prev => ({ ...prev, [tabName]: prev[tabName] + 1 }));
  };

  const handleReset = async () => {
    if (documentId) {
      localStorage.removeItem(`summary_${documentId}`);
      localStorage.removeItem(`quiz_${documentId}`);
      localStorage.removeItem(`flashcards_${documentId}`);
      try {
        await axios.post(`${API_URL}/reset`, { document_id: documentId }, { timeout: 10000 });
      } catch (err) {
        console.error("Failed to reset on backend", err);
      }
    }
    setDocumentId(null);
    setActiveTab('chat');
    setGlobalKey(prev => prev + 1);
  };

  const handleUploadSuccess = (id) => {
    setDocumentId(id);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-blue-100 animate-gradient flex flex-col font-sans text-slate-800">
      {/* Header */}
      <header className="bg-white/60 border-b border-white/80 sticky top-0 z-10 shadow-sm backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="bg-blue-600 p-2 rounded-xl shadow-md">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-800">
              AI Study Buddy
            </h1>
          </div>
          <button
            onClick={handleReset}
            className="flex items-center space-x-2 bg-red-50 text-red-600 px-4 py-2 rounded-xl font-semibold border border-red-200 hover:bg-red-100 active:scale-95 transition-all shadow-sm"
          >
            <span>Reset Session 🔄</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          
          {/* Left Column: Upload & Context */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            <div className="bg-white/60 backdrop-blur-2xl border border-white/80 rounded-3xl p-8 shadow-[0_8px_32px_0_rgba(37,99,235,0.15)] relative overflow-hidden">
              <div className="absolute top-0 right-0 p-8 opacity-5">
                <BookOpen className="w-32 h-32 text-slate-800" />
              </div>
              <div className="relative z-10">
                <h2 className="text-3xl font-bold mb-3 tracking-tight text-slate-800">Your Personal Tutor</h2>
                <p className="text-slate-600 mb-8 max-w-xl text-lg">
                  Upload your syllabus, lecture notes, or textbook chapters. 
                  The AI will instantly read the material and generate interactive study aids.
                </p>
                <FileUpload onUploadSuccess={handleUploadSuccess} />
              </div>
            </div>
            
            {documentId && (
              <div className="bg-green-500/10 backdrop-blur-md border border-green-500/20 rounded-2xl p-5 flex items-center shadow-lg">
                <div className="flex items-center justify-center w-10 h-10 rounded-full bg-green-500/20 mr-4 flex-shrink-0 border border-green-500/30">
                  <div className="w-2.5 h-2.5 bg-green-400 rounded-full shadow-[0_0_8px_rgba(74,222,128,0.8)]"></div>
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-green-100">Ready to Learn</h4>
                  <p className="text-xs text-green-200/70 mt-0.5">Your document is loaded and ready for analysis.</p>
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Interactive Features */}
          <div className="lg:col-span-7 flex flex-col">
            <FeatureTabs activeTab={activeTab} setActiveTab={setActiveTab} />
            
            <div key={globalKey} className="flex-1 transition-all duration-300 relative">
              <div className={activeTab === 'chat' ? 'block' : 'hidden'}>
                <ChatInterface key={tabKeys.chat} documentId={documentId} onReset={() => handleTabReset('chat')} />
              </div>
              <div className={activeTab === 'quizzes' ? 'block' : 'hidden'}>
                <QuizInterface key={tabKeys.quizzes} documentId={documentId} onReset={() => handleTabReset('quizzes')} />
              </div>
              <div className={activeTab === 'flashcards' ? 'block' : 'hidden'}>
                <FlashcardInterface key={tabKeys.flashcards} documentId={documentId} onReset={() => handleTabReset('flashcards')} />
              </div>
              <div className={activeTab === 'summary' ? 'block' : 'hidden'}>
                <SummaryInterface key={tabKeys.summary} documentId={documentId} onReset={() => handleTabReset('summary')} />
              </div>
            </div>
          </div>

        </div>
      </main>
    </div>
  );
}

export default App;
