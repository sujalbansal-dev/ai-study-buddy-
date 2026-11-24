import React from 'react';
import { MessageSquare, BrainCircuit, Library, FileText } from 'lucide-react';

const FeatureTabs = ({ activeTab, setActiveTab }) => {
  const tabs = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'quizzes', label: 'Quizzes', icon: BrainCircuit },
    { id: 'flashcards', label: 'Flashcards', icon: Library },
    { id: 'summary', label: 'Summary', icon: FileText },
  ];

  return (
    <div className="flex space-x-1 bg-white/60 backdrop-blur-md p-1.5 rounded-xl mb-6 border border-white/80 shadow-sm overflow-x-auto">
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center min-w-[100px] py-2.5 px-4 rounded-lg text-sm font-medium transition-all duration-200 ${
              isActive 
                ? 'bg-blue-600 text-white rounded-lg shadow-md' 
                : 'text-slate-500 hover:text-slate-700 hover:bg-white/50'
            }`}
          >
            <Icon className={`w-4 h-4 mr-2 flex-shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};

export default FeatureTabs;
