import React, { useState } from 'react';
import axios from 'axios';
import { BrainCircuit, Loader, AlertTriangle, CheckCircle } from 'lucide-react';
import Confetti from 'react-confetti';

const QuizInterface = ({ documentId }) => {
  const [quizData, setQuizData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [answers, setAnswers] = useState({});
  const [score, setScore] = useState(null);

  const handleGenerateQuiz = async () => {
    if (!documentId) {
      setError('Please upload a document first to generate a quiz.');
      return;
    }

    setIsLoading(true);
    setError('');
    setQuizData(null);
    setAnswers({});
    setScore(null);

    try {
      const response = await axios.post('http://localhost:8000/generate/quiz', {
        document_id: documentId
      });

      if (response.data.quiz && response.data.quiz.error) {
        setError(response.data.quiz.error);
      } else {
        setQuizData(response.data.quiz);
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to generate quiz. Is the backend running?');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOptionSelect = (qIndex, type, value) => {
    setAnswers(prev => ({
      ...prev,
      [`${type}-${qIndex}`]: value
    }));
  };

  const checkAnswers = () => {
    let correct = 0;
    let total = 0;

    if (quizData.multiple_choice) {
      quizData.multiple_choice.forEach((q, idx) => {
        total++;
        if (answers[`mc-${idx}`] === q.answer) correct++;
      });
    }

    if (quizData.true_false) {
      quizData.true_false.forEach((q, idx) => {
        total++;
        // strict boolean check or string match depending on how it's saved
        if (String(answers[`tf-${idx}`]).toLowerCase() === String(q.answer).toLowerCase()) correct++;
      });
    }

    // We don't auto-grade short answer right now
    setScore({ correct, total });
  };

  if (!quizData && !isLoading) {
    return (
      <div className="bg-white/60 backdrop-blur-2xl rounded-3xl shadow-[0_8px_32px_0_rgba(37,99,235,0.15)] border border-white/80 p-8 text-center h-[600px] flex flex-col items-center justify-center">
        <div className="bg-blue-100 border border-blue-200 w-16 h-16 rounded-full flex items-center justify-center mb-4 shadow-sm">
          <BrainCircuit className="w-8 h-8 text-blue-600" />
        </div>
        <h3 className="text-xl font-bold text-slate-800 mb-2">Quiz Generation</h3>
        <p className="text-slate-600 text-sm mb-6 max-w-sm">Test your knowledge. We'll generate a custom multiple-choice and true/false quiz based strictly on your uploaded materials.</p>

        {error && (
          <div className="mb-4 text-xs text-red-600 flex items-center bg-red-50 border border-red-100 px-3 py-2 rounded-lg max-w-md text-left">
            <AlertTriangle className="w-4 h-4 mr-2 flex-shrink-0" />
            {error}
          </div>
        )}

        <button
          onClick={handleGenerateQuiz}
          disabled={!documentId}
          className={`px-6 py-2.5 rounded-xl font-medium transition-colors shadow-sm border ${documentId
            ? 'bg-blue-600 text-white hover:bg-blue-700 border-blue-600'
            : 'bg-slate-100 text-slate-400 cursor-not-allowed border-slate-200'
            }`}
        >
          Generate Quiz
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
        <h3 className="text-lg font-bold text-slate-800">Reading Your Material...</h3>
        <p className="text-slate-600 text-sm">Generating your custom quiz, this might take a few seconds.</p>
      </div>
    );
  }

  return (
    <>
      {score && score.correct === score.total && (
        <Confetti
          width={window.innerWidth}
          height={window.innerHeight}
          recycle={false}
          numberOfPieces={500}
          style={{ position: 'fixed', top: 0, left: 0, zIndex: 100, pointerEvents: 'none' }}
        />
      )}
      <div className="bg-white/60 backdrop-blur-2xl rounded-3xl shadow-[0_8px_32px_0_rgba(37,99,235,0.15)] border border-white/80 flex flex-col h-[600px] overflow-hidden">
        <div className="p-4 border-b border-white/80 bg-white/80 flex justify-between items-center">
          <h3 className="font-bold text-slate-800 flex items-center">
            <BrainCircuit className="w-5 h-5 mr-2 text-blue-600" />
            Your Custom Quiz
          </h3>
          {score && (
            <div className="bg-gradient-to-r from-blue-500 to-blue-600 text-white border border-blue-400 px-4 py-1.5 rounded-full text-sm font-bold flex items-center shadow-md">
              <CheckCircle className="w-4 h-4 mr-1.5" />
              Score: {score.correct} / {score.total}
            </div>
          )}
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-8">
          {quizData.multiple_choice && quizData.multiple_choice.length > 0 && (
            <section>
              <h4 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-4">Multiple Choice</h4>
              <div className="space-y-6">
                {quizData.multiple_choice.map((q, qIndex) => (
                  <div key={`mc-${qIndex}`} className="bg-white/80 p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="font-medium text-slate-800 mb-3">{qIndex + 1}. {q.question}</p>
                    <div className="space-y-2">
                      {q.options.map((opt, oIndex) => {
                        const isSelected = answers[`mc-${qIndex}`] === opt;
                        const isCorrect = score && q.answer === opt;
                        const isWrong = score && isSelected && q.answer !== opt;

                        let btnClass = "w-full text-left p-3 rounded-lg border transition-all duration-200 text-sm ";
                        if (isCorrect) btnClass += "bg-green-50 border-green-500 text-green-800 scale-[1.02] shadow-md z-10 relative font-medium";
                        else if (isWrong) btnClass += "bg-red-50 border-red-500 text-red-800 animate-shake scale-[1.02] shadow-md z-10 relative font-medium";
                        else if (isSelected) btnClass += "bg-blue-50 border-blue-400 text-blue-900 scale-[1.02] shadow-sm relative";
                        else btnClass += "bg-white border-slate-200 hover:border-blue-400 hover:scale-[1.02] hover:shadow-md text-slate-800";

                        return (
                          <button
                            key={oIndex}
                            onClick={() => !score && handleOptionSelect(qIndex, 'mc', opt)}
                            disabled={!!score}
                            className={btnClass}
                          >
                            {opt}
                          </button>
                        );
                      })}
                    </div>
                    {score && (
                      <div className="mt-3 text-sm text-slate-600">
                        <strong className="text-slate-800">Correct Answer:</strong> {q.answer}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          )}

          {quizData.true_false && quizData.true_false.length > 0 && (
            <section>
              <h4 className="text-lg font-bold text-slate-800 border-b border-slate-200 pb-2 mb-4">True / False</h4>
              <div className="space-y-6">
                {quizData.true_false.map((q, qIndex) => (
                  <div key={`tf-${qIndex}`} className="bg-white/80 p-4 rounded-xl border border-slate-200 shadow-sm">
                    <p className="font-medium text-slate-800 mb-3">{qIndex + 1}. {q.question}</p>
                    <div className="flex space-x-3">
                      {['True', 'False'].map(opt => {
                        const optValue = opt.toLowerCase() === 'true';
                        const isSelected = String(answers[`tf-${qIndex}`]) === String(optValue);
                        const isCorrect = score && String(q.answer) === String(optValue);
                        const isWrong = score && isSelected && String(q.answer) !== String(optValue);

                        let btnClass = "flex-1 text-center p-3 rounded-lg border transition-all duration-200 text-sm font-medium ";
                        if (isCorrect) btnClass += "bg-green-50 border-green-500 text-green-800 scale-[1.02] shadow-md z-10 relative";
                        else if (isWrong) btnClass += "bg-red-50 border-red-500 text-red-800 animate-shake scale-[1.02] shadow-md z-10 relative";
                        else if (isSelected) btnClass += "bg-blue-50 border-blue-400 text-blue-900 scale-[1.02] shadow-sm relative";
                        else btnClass += "bg-white border-slate-200 hover:border-blue-400 hover:scale-[1.02] hover:shadow-md text-slate-800";

                        return (
                          <button
                            key={opt}
                            onClick={() => !score && handleOptionSelect(qIndex, 'tf', optValue)}
                            disabled={!!score}
                            className={btnClass}
                          >
                            {opt}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        <div className="p-4 bg-white/80 border-t border-white/80 flex justify-between backdrop-blur-md">
          <button
            onClick={handleGenerateQuiz}
            className="px-4 py-2 text-blue-600 hover:text-blue-700 hover:bg-blue-50 font-medium rounded-lg transition-colors text-sm"
          >
            Regenerate New Quiz
          </button>
          {!score && (
            <button
              onClick={checkAnswers}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium transition-colors text-sm shadow-sm"
            >
              Submit Answers
            </button>
          )}
        </div>
      </div>
    </>
  );
};

export default QuizInterface;
