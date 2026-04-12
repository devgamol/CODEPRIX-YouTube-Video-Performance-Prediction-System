import { useState, useEffect } from 'react';
import { getJobStatus } from '../api/client';

const stages = [
  'Extracting frames...',
  'Analyzing motion...',
  'Transcribing audio...',
  'Computing retention curve...',
  'Generating AI suggestions...'
];

export default function ProgressPoller({ jobId, onComplete, onError }) {
  const [currentStage, setCurrentStage] = useState(0);
  const [error, setError] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const status = await getJobStatus(jobId);
        if (status.status === 'done') {
          clearInterval(interval);
          setProgress(100);
          setTimeout(() => onComplete(status.result), 500);
        } else if (status.status === 'error') {
          clearInterval(interval);
          setError(true);
        } else {
          const stageIndex = stages.indexOf(status.progress);
          if (stageIndex !== -1) {
            setCurrentStage(stageIndex);
            setProgress(((stageIndex + 1) / stages.length) * 100);
          }
        }
      } catch (err) {
        clearInterval(interval);
        setError(true);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId, onComplete, onError]);

  if (error) {
    return (
      <div className="rounded-2xl sm:rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-12 shadow-2xl backdrop-blur-xl text-center max-w-xs sm:max-w-md mx-auto">
        <div className="mx-auto mb-4 sm:mb-6 h-14 sm:h-16 w-14 sm:w-16 rounded-2xl bg-red-500/20 flex items-center justify-center">
          <svg style={{ width: '24px', height: '24px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2" className="text-red-400">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        </div>
        <h2 className="text-xl sm:text-2xl font-bold text-white mb-2 sm:mb-3">Processing Failed</h2>
        <p className="text-xs sm:text-sm text-slate-400 mb-6 sm:mb-8">Something went wrong during analysis. Please try again.</p>
        <button
          onClick={onError}
          className="w-full rounded-lg sm:rounded-xl bg-gradient-to-r from-purple-600 to-blue-600 px-4 sm:px-6 py-2.5 sm:py-3 text-xs sm:text-sm font-semibold text-white shadow-lg shadow-purple-500/40 transition hover:opacity-95"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-2xl sm:rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-12 shadow-2xl backdrop-blur-xl text-center max-w-xs sm:max-w-md mx-auto">
      <div className="mb-8 sm:mb-12">
        <h2 className="text-xl sm:text-2xl lg:text-3xl font-bold text-white mb-1 sm:mb-2">Analyzing your video</h2>
        <p className="text-xs sm:text-sm text-slate-400">This typically takes 2-5 minutes</p>
      </div>

      {/* Overall Progress Bar */}
      <div className="mb-8 sm:mb-12">
        <div className="flex items-center justify-between mb-2 sm:mb-3">
          <span className="text-xs uppercase tracking-wider text-slate-400 font-semibold">Overall progress</span>
          <span className="text-xs sm:text-sm font-bold text-purple-400">{Math.round(progress)}%</span>
        </div>
        <div className="h-2 rounded-full bg-white/5 border border-white/10 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-purple-500 to-blue-600 transition-all duration-500 shadow-lg shadow-purple-500/50"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Stage Timeline */}
      <div className="space-y-3 sm:space-y-4">
        {stages.map((stage, index) => (
          <div
            key={stage}
            className={`flex items-center gap-3 sm:gap-4 p-3 sm:p-4 rounded-lg sm:rounded-xl transition-all ${
              index < currentStage
                ? 'bg-green-500/10'
                : index === currentStage
                ? 'bg-purple-500/10 border border-purple-500/30'
                : 'bg-white/5 opacity-50'
            }`}
          >
            <div
              className={`flex-shrink-0 w-7 sm:w-8 h-7 sm:h-8 rounded-full flex items-center justify-center font-semibold text-xs sm:text-sm ${
                index < currentStage
                  ? 'bg-green-500/30 text-green-300'
                  : index === currentStage
                  ? 'bg-gradient-to-r from-purple-500 to-blue-600 text-white animate-pulse'
                  : 'bg-white/10 text-slate-500'
              }`}
            >
              {index < currentStage ? (
                <svg style={{ width: '16px', height: '16px' }} fill="currentColor" viewBox="0 0 24 24">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                </svg>
              ) : (
                <span>{index + 1}</span>
              )}
            </div>
            <span className={`text-xs sm:text-sm font-medium ${
              index === currentStage ? 'text-white' : 'text-slate-400'
            }`}>
              {stage}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
