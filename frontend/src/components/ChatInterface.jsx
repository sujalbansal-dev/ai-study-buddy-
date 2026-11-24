import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Send, User, Bot, AlertTriangle, RefreshCw } from 'lucide-react';

const ChatInterface = ({ documentId, onReset }) => {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hi! I'm your AI Study Buddy. Ask me anything about your uploaded documents.", sender: 'ai' }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { id: Date.now(), text: input, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError('');

    if (!documentId) {
      setError('Please upload a document first before asking questions.');
      setIsLoading(false);
      return;
    }

    try {
      const response = await axios.post(`${API_URL}/ask`, {
        document_id: documentId,
        question: userMessage.text
      });
      
      const aiMessage = { 
        id: Date.now() + 1, 
        text: response.data.answer, 
        sender: 'ai' 
      };
      setMessages(prev => [...prev, aiMessage]);
    } catch (err) {
      console.error(err);
      if (err.response?.status === 429) {
        setError('The AI is taking a breather to prevent server overload! Please wait 60 seconds before generating the next item.');
      } else if (err.response?.status === 404) {
        setError(err.response?.data?.detail || 'Document not found on the server. Please re-upload your document.');
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Failed to connect to the AI. Ensure the backend is running.');
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
            <Bot className="w-5 h-5 text-blue-600" />
          </div>
          <h3 className="font-bold text-slate-800">Tutor Chat</h3>
        </div>
        <div className="flex items-center space-x-3">
          {error && (
            <div className="text-xs text-red-600 flex items-center bg-red-50 border border-red-100 px-2 py-1 rounded">
              <AlertTriangle className="w-3 h-3 mr-1" />
              {error}
            </div>
          )}
          <button 
            onClick={onReset}
            className="flex items-center space-x-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 bg-white hover:bg-slate-50 border border-slate-200 px-2.5 py-1.5 rounded-lg shadow-sm transition-all active:scale-95"
            title="Reset Chat"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Reset Chat</span>
          </button>
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-5 bg-transparent">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex animate-fade-in-up ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[85%] ${msg.sender === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border ${
                msg.sender === 'user' ? 'bg-blue-100 border-blue-200 ml-3' : 'bg-white border-slate-200 shadow-sm mr-3'
              }`}>
                {msg.sender === 'user' ? <User className="w-4 h-4 text-blue-600" /> : <Bot className="w-4 h-4 text-blue-600" />}
              </div>
              <div className={`p-3.5 rounded-2xl text-sm leading-relaxed shadow-sm backdrop-blur-md border ${
                msg.sender === 'user' 
                  ? 'bg-blue-600 text-white rounded-lg shadow-md border-blue-500 rounded-tr-none' 
                  : 'bg-white text-slate-800 border-slate-200 rounded-tl-none prose prose-sm max-w-none'
              }`}>
                {msg.sender === 'user' ? (
                  <p className="whitespace-pre-wrap">{msg.text}</p>
                ) : (
                  <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>{msg.text}</ReactMarkdown>
                )}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start animate-fade-in-up">
            <div className="flex flex-row max-w-[85%]">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-white border border-slate-200 shadow-sm mr-3 flex items-center justify-center">
                <Bot className="w-4 h-4 text-blue-600" />
              </div>
              <div className="bg-white border border-slate-200 backdrop-blur-md p-4 rounded-2xl rounded-tl-none shadow-sm flex items-center space-x-1.5 h-11">
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 bg-white/80 border-t border-white/80 backdrop-blur-md">
        <form onSubmit={handleSend} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question..."
            className="w-full pl-4 pr-12 py-3.5 bg-white border border-slate-200 shadow-sm rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all text-sm text-slate-800 placeholder-slate-400"
            disabled={isLoading}
          />
          <button 
            type="submit" 
            disabled={!input.trim() || isLoading}
            className="absolute right-2 p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors shadow-sm"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatInterface;
