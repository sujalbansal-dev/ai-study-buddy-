import React, { useState } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
import { BookOpen, Loader, AlertTriangle, ChevronLeft, ChevronRight, RotateCcw, RefreshCw } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

const FlashcardInterface = ({ documentId, onReset }) => {
  const [flashcards, setFlashcards] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  const handleGenerateFlashcards = async () => {
    if (!documentId) {
      setError('Please upload a document first to generate flashcards.');
      return;
    }

    const cacheKey = `flashcards_${documentId}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        setFlashcards(JSON.parse(cached));
        setCurrentIndex(0);
        setIsFlipped(false);
        return;
      } catch (e) {
        console.error("Invalid cache", e);
      }
    }

    setIsLoading(true);
    setError('');
    setFlashcards([]);
    setCurrentIndex(0);
    setIsFlipped(false);

    try {
      const response = await axios.post(`${API_URL}/generate/flashcards`, {
        document_id: documentId
      });

      const cards = response.data.flashcards;
      if (!cards || cards.length === 0) {
        setError('No key terms found to generate flashcards.');
      } else {
        setFlashcards(cards);
        localStorage.setItem(cacheKey, JSON.stringify(cards));
      }
    } catch (err) {
      console.error(err);
      if (err.response?.status === 429) {
        setError('The AI is taking a breather to prevent server overload! Please wait 60 seconds before generating the next item.');
      } else {
        setError(err.response?.data?.detail || 'Failed to generate flashcards. Is the backend running?');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleNext = () => {
    if (currentIndex < flashcards.length - 1) {
      setIsFlipped(false);
      setTimeout(() => setCurrentIndex(prev => prev + 1), 150);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setIsFlipped(false);
      setTimeout(() => setCurrentIndex(prev => prev - 1), 150);
    }
  };

  if (flashcards.length === 0 && !isLoading) {
    return (
      <div className="bg-white/60 backdrop-blur-2xl rounded-3xl shadow-[0_8px_32px_0_rgba(37,99,235,0.15)] border border-white/80 p-8 text-center h-[600px] flex flex-col items-center justify-center">
        <div className="bg-blue-100 border border-blue-200 w-16 h-16 rounded-full flex items-center justify-center mb-4 shadow-sm">
          <BookOpen className="w-8 h-8 text-blue-600" />
        </div>
        <h3 className="text-xl font-bold text-slate-800 mb-2">Smart Flashcards</h3>
        <p className="text-slate-600 text-sm mb-6 max-w-sm">Quickly master key terms. The AI will extract the most important definitions into a set of interactive flashcards.</p>

        {error && (
          <div className="mb-4 text-xs text-red-600 flex items-center bg-red-50 border border-red-100 px-3 py-2 rounded-lg max-w-md text-left">
            <AlertTriangle className="w-4 h-4 mr-2 flex-shrink-0" />
            {error}
          </div>
        )}

        <button
          onClick={handleGenerateFlashcards}
          disabled={!documentId}
          className={`px-6 py-2.5 rounded-xl font-medium transition-colors shadow-sm border ${documentId
              ? 'bg-blue-600 text-white hover:bg-blue-700 border-blue-600'
              : 'bg-slate-100 text-slate-400 cursor-not-allowed border-slate-200'
            }`}
        >
          Generate Flashcards
        </button>
        {!documentId && (
          <p className="text-xs text-slate-400 mt-3">Upload a document first to unlock.</p>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="bg-white/60 backdrop-blur-2xl rounded-3xl shadow-[0_8px_32px_0_rgba(37,99,235,0.15)] border border-white/80 p-8 h-[600px] flex flex-col items-center justify-center">
        <Loader className="w-10 h-10 text-blue-500 animate-spin mb-4" />
        <h3 className="text-lg font-bold text-slate-800">Extracting Terms...</h3>
        <p className="text-slate-600 text-sm">Building your smart flashcard deck.</p>
      </div>
    );
  }

  const currentCard = flashcards[currentIndex];

  return (
    <div className="bg-white/60 backdrop-blur-2xl rounded-3xl shadow-[0_8px_32px_0_rgba(37,99,235,0.15)] border border-white/80 flex flex-col h-[600px] overflow-hidden">
      <div className="p-4 border-b border-white/80 bg-white/80 flex justify-between items-center">
        <h3 className="font-bold text-slate-800 flex items-center">
          <BookOpen className="w-5 h-5 mr-2 text-blue-600" />
          Study Deck
        </h3>
        <div className="flex items-center space-x-3">
          <div className="text-sm font-medium text-slate-500 bg-white/80 px-3 py-1 rounded-full border border-slate-200">
            Card {currentIndex + 1} of {flashcards.length}
          </div>
          <button 
            onClick={onReset}
            className="flex items-center space-x-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 bg-white hover:bg-slate-50 border border-slate-200 px-2.5 py-1.5 rounded-lg shadow-sm transition-all active:scale-95"
            title="Reset Flashcards"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset Deck</span>
          </button>
        </div>
      </div>

      <div className="flex-1 flex flex-col items-center justify-center p-8 relative [perspective:1000px]">
        {/* Flashcard Wrapper with Hover Glow */}
        <div className="w-full max-w-md h-80 transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_10px_40px_-10px_rgba(37,99,235,0.3)] rounded-3xl">
          <div
            onClick={() => setIsFlipped(!isFlipped)}
            className={`w-full h-full cursor-pointer relative transition-transform duration-500 [transform-style:preserve-3d] ${isFlipped ? '[transform:rotateY(180deg)]' : ''}`}
          >
            {/* Front */}
            <div className="absolute inset-0 bg-white backdrop-blur-md rounded-3xl shadow-sm border border-slate-200 flex flex-col items-center justify-center p-8 text-center [backface-visibility:hidden] overflow-y-auto">
              <span className="absolute top-4 left-6 text-xs font-bold text-slate-400 tracking-wider uppercase">Term</span>
              <div className="text-3xl sm:text-4xl font-extrabold text-slate-800 leading-tight prose prose-lg">
                <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{currentCard?.front || ''}</ReactMarkdown>
              </div>
              <p className="absolute bottom-6 text-xs font-medium text-blue-500 animate-pulse">Click to flip</p>
            </div>

            {/* Back */}
            <div className="absolute inset-0 bg-blue-600 backdrop-blur-md text-white rounded-3xl shadow-inner border border-blue-700 flex flex-col items-center justify-center p-8 text-center [backface-visibility:hidden] [transform:rotateY(180deg)] overflow-y-auto">
              <span className="absolute top-4 left-6 text-xs font-bold text-blue-300 tracking-wider uppercase">Definition</span>
              <div className="text-lg sm:text-xl font-medium leading-relaxed prose prose-invert prose-p:leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{currentCard?.back || ''}</ReactMarkdown>
              </div>
              <p className="absolute bottom-6 text-xs font-medium text-blue-200">Click to flip back</p>
            </div>
          </div>
        </div>

        {/* Navigation Controls */}
        <div className="flex items-center space-x-6 mt-10">
          <button
            onClick={handlePrev}
            disabled={currentIndex === 0}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 shadow-sm border ${currentIndex === 0
                ? 'bg-slate-100 border-slate-200 text-slate-400 cursor-not-allowed'
                : 'bg-blue-50 border-blue-200 text-blue-600 hover:bg-blue-100 hover:text-blue-700 hover:scale-105'
              }`}
          >
            <ChevronLeft className="w-6 h-6" />
          </button>

          <button
            onClick={() => setIsFlipped(!isFlipped)}
            className="px-5 py-2.5 bg-blue-50 border border-blue-200 text-blue-600 font-medium rounded-full hover:bg-blue-100 hover:text-blue-700 hover:scale-105 transition-all duration-300 shadow-sm flex items-center backdrop-blur-md"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Flip Card
          </button>

          <button
            onClick={handleNext}
            disabled={currentIndex === flashcards.length - 1}
            className={`w-12 h-12 rounded-full flex items-center justify-center transition-all duration-300 shadow-sm border ${currentIndex === flashcards.length - 1
                ? 'bg-slate-100 border-slate-200 text-slate-400 cursor-not-allowed'
                : 'bg-blue-50 border-blue-200 text-blue-600 hover:bg-blue-100 hover:text-blue-700 hover:scale-105'
              }`}
          >
            <ChevronRight className="w-6 h-6" />
          </button>
        </div>
      </div>

      <div className="p-4 bg-white/80 border-t border-white/80 flex justify-between items-center backdrop-blur-md">
        <button
          onClick={handleGenerateFlashcards}
          className="text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors"
        >
          Regenerate Deck
        </button>
        <div className="w-32 h-2 bg-slate-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${((currentIndex + 1) / flashcards.length) * 100}%` }}
          ></div>
        </div>
      </div>
    </div>
  );
};

export default FlashcardInterface;
