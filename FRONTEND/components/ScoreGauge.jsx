import { useEffect, useState } from 'react';
import { getLetterGrade } from '../src/utils';

export default function ScoreGauge({ score }) {
  const [animatedScore, setAnimatedScore] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setAnimatedScore(score), 500);
    return () => clearTimeout(timer);
  }, [score]);

  const percentage = animatedScore / 100;
  const strokeDashoffset = 283 - (283 * percentage);

  const getColor = (score) => {
    if (score >= 80) return '#22c55e';
    if (score >= 60) return '#f59e0b';
    return '#ef4444';
  };

  const getGlowColor = (score) => {
    if (score >= 80) return 'rgb(34, 197, 94)';
    if (score >= 60) return 'rgb(245, 158, 11)';
    return 'rgb(239, 68, 68)';
  };

  return (
    <div className="flex flex-col items-center justify-center w-full h-full">
      <div className="relative w-40 sm:w-48 h-40 sm:h-48 mb-6 sm:mb-8">
        {/* Glow ring */}
        <div
          className="absolute inset-0 rounded-full blur-2xl opacity-50 animate-pulse"
          style={{ backgroundColor: getGlowColor(score) }}
        />
        {/* SVG Gauge */}
        <svg className="absolute inset-0 w-full h-full transform -rotate-90" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" stroke="rgba(255,255,255,0.1)" strokeWidth="6" fill="none" />
          <circle
            cx="50"
            cy="50"
            r="45"
            stroke={getColor(animatedScore)}
            strokeWidth="6"
            fill="none"
            strokeDasharray="283"
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-1000 ease-out drop-shadow-lg"
            style={{
              filter: `drop-shadow(0 0 20px ${getColor(animatedScore)}40)`
            }}
          />
        </svg>
        {/* Center Content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-4xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tighter">{animatedScore}</div>
          <div className="text-base sm:text-lg lg:text-xl font-semibold text-slate-300">{getLetterGrade(animatedScore)}</div>
        </div>
      </div>
      <div className="text-center">
        <p className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-400">VPQ Score</p>
        <p className="text-xs text-slate-500 mt-0.5 sm:mt-1">Video Performance Quotient</p>
      </div>
    </div>
  );
}
