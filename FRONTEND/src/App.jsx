import { useState } from 'react';
import Upload from '../components/Upload';
import ProgressPoller from '../components/ProgressPoller';
import ScoreGauge from '../components/ScoreGauge';
import RetentionChart from '../components/RetentionChart';
import WeakSegments from '../components/WeakSegments';
import SuggestionCards from '../components/SuggestionCards';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts';

const mockData = {
  overall_score: 64,
  summary: "Video has strong opening but loses momentum significantly after the 45 second mark. Pacing issues and low motion segments are the primary drivers of predicted drop-off.",
  retention_curve: [
    { time: 0, retention: 100 },
    { time: 10, retention: 96 },
    { time: 20, retention: 89 },
    { time: 30, retention: 85 },
    { time: 45, retention: 71 },
    { time: 60, retention: 58 },
    { time: 75, retention: 52 },
    { time: 90, retention: 61 },
    { time: 105, retention: 55 },
    { time: 120, retention: 48 }
  ],
  weak_segments: [
    { start: 45, end: 78 },
    { start: 105, end: 130 }
  ],
  suggestions: [
    {
      timestamp_start: 0,
      timestamp_end: 18,
      issue: "Intro too long with static framing",
      fix: "Open with the most compelling moment from the video, push channel intro after first hook",
      priority: "High"
    },
    {
      timestamp_start: 45,
      timestamp_end: 78,
      issue: "Low motion and flat vocal delivery for 33 seconds",
      fix: "Add B-roll footage or cut this segment by 60 percent",
      priority: "High"
    },
    {
      timestamp_start: 105,
      timestamp_end: 130,
      issue: "Dialogue lacks engagement cues",
      fix: "Rewrite to include a direct question to viewer or a surprising statement",
      priority: "Medium"
    }
  ],
  motion_data: [
    { timestamp: 0, motion: 0.8 },
    { timestamp: 5, motion: 0.6 },
    { timestamp: 10, motion: 0.3 },
    { timestamp: 15, motion: 0.2 },
    { timestamp: 20, motion: 0.7 }
  ]
};

function normalizeResult(rawResult) {
  const safe = rawResult && typeof rawResult === 'object' ? rawResult : {};
  const retention = safe.retention || {};
  const suggestionsPayload =
    safe.suggestions && typeof safe.suggestions === 'object' ? safe.suggestions : {};
  const weakSegments = Array.isArray(retention.weak_segments) ? retention.weak_segments : [];
  const suggestions = Array.isArray(suggestionsPayload.suggestions)
    ? suggestionsPayload.suggestions
    : Array.isArray(safe.suggestions)
    ? safe.suggestions
    : [];
  const retentionCurve = Array.isArray(retention.retention_curve) ? retention.retention_curve : [];
  const motionData = Array.isArray(safe.video?.motion_scores)
    ? safe.video.motion_scores.map((item) => ({
        timestamp: Number(item.timestamp) || 0,
        motion: Number(item.motion_intensity) || 0,
      }))
    : [];

  const fallbackSummary = weakSegments.length
    ? `Detected ${weakSegments.length} weak segment${weakSegments.length === 1 ? '' : 's'} with predicted drop-off risk.`
    : 'No major weak segments detected.';
  const summary =
    typeof suggestionsPayload.summary === 'string' && suggestionsPayload.summary.trim()
      ? suggestionsPayload.summary
      : fallbackSummary;

  const fallbackSuggestions = weakSegments.slice(0, 3).map((segment) => ({
    timestamp_start: Number(segment.start) || 0,
    timestamp_end: Number(segment.end) || 0,
    issue: 'Predicted audience drop-off',
    reason: 'This segment is flagged as a weak point in retention behavior.',
    fix: 'Tighten pacing and add stronger visual or audio variation in this section.',
    priority: segment.severity === 'critical' || segment.severity === 'severe' ? 'High' : 'Medium',
  }));
  const normalizedSuggestions = (suggestions.length ? suggestions : fallbackSuggestions).map((item) => ({
    ...item,
    reason:
      typeof item?.reason === 'string' && item.reason.trim()
        ? item.reason
        : 'This segment is flagged as a weak point in retention behavior.',
  }));

  return {
    overall_score: Number(suggestionsPayload.overall_score) || Number(retention.vpq_score) || 0,
    summary,
    retention_curve: retentionCurve.map((point) => ({
      time: Number(point.time) || 0,
      retention: Number(point.retention) || 0,
    })),
    weak_segments: weakSegments.map((segment) => ({
      ...segment,
      start: Number(segment.start) || 0,
      end: Number(segment.end) || 0,
    })),
    suggestions: normalizedSuggestions,
    motion_data: motionData,
  };
}

function App() {
  const [screen, setScreen] = useState('idle');
  const [jobId, setJobId] = useState(null);
  const [resultData, setResultData] = useState(null);
  const [trackingJobId, setTrackingJobId] = useState('');
  const [searchError, setSearchError] = useState('');

  const handleUploadSuccess = (id) => {
    setJobId(id);
    setScreen('processing');
  };

  const handleProcessingComplete = (data) => {
    setResultData(normalizeResult(data));
    setScreen('results');
  };

  const handleError = () => {
    setScreen('idle');
    setJobId(null);
  };

  const handleTrackJob = async () => {
    if (!trackingJobId.trim()) {
      setSearchError('Please enter a job ID');
      return;
    }
    setSearchError('');
  };

  const renderHeader = () => (
    <header className="border-b border-[#20283a] bg-gradient-to-r from-[#171c28] via-[#0f1627] to-[#070d19]">
      <div className="mx-auto flex max-w-[1160px] items-center px-6 py-6 sm:px-8">
        <div className="flex items-center gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-gradient-to-br from-[#5857ff] to-[#5b8cff] shadow-[0_10px_24px_rgba(88,87,255,0.35)]">
            <svg className="h-6 w-6 text-white" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 6.5v11l9-5.5L8 6.5z" />
            </svg>
          </div>
          <div>
            <p className="text-3xl font-bold leading-none text-[#615bff] sm:text-4xl">Video Insight AI</p>
            <p className="mt-1.5 text-base text-[#9aa4b2] sm:text-[30px]">AI-Powered Performance Analysis</p>
          </div>
        </div>
      </div>
    </header>
  );

  if (screen === 'idle') {
    return (
      <div className="min-h-screen bg-[#020917] [forced-color-adjust:none]">
        {renderHeader()}
        <main className="mx-auto max-w-[1160px] px-6 pb-10 pt-10 sm:px-8 sm:pt-14">
          <section>
            <h1 className="text-center text-4xl font-semibold sm:text-6xl" style={{ color: '#ffffff' }}>Analyze Your Video</h1>
            <p className="mx-auto mt-4 max-w-[980px] text-center text-lg sm:text-[34px]" style={{ color: '#a7b2c1' }}>
              Get AI-powered insights on viewer retention, engagement patterns, and optimization tips.
            </p>
            <div className="mt-8">
              <Upload onUploadSuccess={handleUploadSuccess} />
            </div>
          </section>

          <div className="my-12 h-px bg-[#1b2434]" />

          <section>
            <h2 className="text-3xl font-semibold sm:text-[44px]" style={{ color: '#ffffff' }}>Track Previous Analysis</h2>
            <div className="mt-8 flex flex-col gap-4 sm:flex-row sm:items-center">
              <input
                type="text"
                placeholder="Enter job ID (e.g., JOB_1234567890)"
                value={trackingJobId}
                onChange={(e) => {
                  setTrackingJobId(e.target.value);
                  setSearchError('');
                }}
                className="h-[56px] w-full flex-1 rounded-3xl border border-[#2b3447] bg-[#1a222f] px-5 text-[18px] text-[#e2e8f0] placeholder:text-[#6f7a8e] focus:border-[#4d5e7e] focus:outline-none"
              />
              <button
                onClick={handleTrackJob}
                className="inline-flex h-[56px] w-full items-center justify-center gap-2 whitespace-nowrap rounded-3xl bg-gradient-to-r from-[#7436f3] to-[#5f22dc] px-6 text-[18px] font-semibold text-white shadow-[0_12px_30px_rgba(116,54,243,0.4)] sm:w-[150px] sm:shrink-0"
              >
                <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.3">
                  <circle cx="11" cy="11" r="8" />
                  <path d="M21 21l-4.35-4.35" />
                </svg>
                <span className="leading-none">Search</span>
              </button>
            </div>
            {searchError && <p className="mt-3 text-sm text-red-300">{searchError}</p>}
          </section>
        </main>
      </div>
    );
  }

  if (screen === 'processing') {
    return (
      <div className="min-h-screen bg-[#060b18]">
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
        </div>
        <div className="relative z-10">
          {renderHeader()}
          <main className="mx-auto flex min-h-[calc(100vh-80px)] max-w-3xl items-center justify-center px-4 sm:px-6 lg:px-8 py-8 sm:py-24">
            <ProgressPoller jobId={jobId} onComplete={handleProcessingComplete} onError={handleError} />
          </main>
        </div>
      </div>
    );
  }

  if (screen === 'results') {
    const data = resultData || mockData;
    return (
      <div className="min-h-screen bg-[#060b18]">
        <div className="fixed inset-0 overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-1/4 right-1/3 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
        </div>
        <div className="relative z-10">
          {renderHeader()}
          <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
            <section className="mb-12 grid gap-6 sm:gap-8 lg:grid-cols-[1.4fr_0.6fr]">
              <div className="rounded-2xl sm:rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-10 shadow-2xl backdrop-blur-xl">
                <div className="space-y-4 sm:space-y-6">
                  <div>
                    <span className="inline-flex items-center gap-2 rounded-full bg-purple-500/20 px-3 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-semibold text-purple-200">Analysis Complete</span>
                    <h1 className="mt-4 text-2xl sm:text-3xl lg:text-5xl font-bold text-white leading-tight">Performance insights for your video.</h1>
                    <p className="mt-4 max-w-2xl text-sm sm:text-base lg:text-lg text-slate-400 leading-relaxed">{data.summary}</p>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-lg sm:rounded-2xl border border-white/10 bg-white/5 p-4 sm:p-6 backdrop-blur">
                      <p className="text-xs uppercase tracking-wider text-slate-500">VPQ Score</p>
                      <p className="mt-2 sm:mt-3 text-2xl sm:text-3xl lg:text-4xl font-bold text-white">{data.overall_score}</p>
                    </div>
                    <div className="rounded-lg sm:rounded-2xl border border-white/10 bg-white/5 p-4 sm:p-6 backdrop-blur">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Weak Segments</p>
                      <p className="mt-2 sm:mt-3 text-2xl sm:text-3xl lg:text-4xl font-bold text-orange-400">{data.weak_segments.length}</p>
                    </div>
                    <div className="rounded-lg sm:rounded-2xl border border-white/10 bg-white/5 p-4 sm:p-6 backdrop-blur">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Recommendations</p>
                      <p className="mt-2 sm:mt-3 text-2xl sm:text-3xl lg:text-4xl font-bold text-blue-400">{data.suggestions.length}</p>
                    </div>
                  </div>
                </div>
              </div>
              <div className="rounded-2xl sm:rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-10 shadow-2xl backdrop-blur-xl flex items-center justify-center">
                <ScoreGauge score={data.overall_score} />
              </div>
            </section>

            <section className="mb-12 grid gap-6 sm:gap-8 lg:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-2xl sm:rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-10 shadow-2xl backdrop-blur-xl">
                <div className="mb-6 sm:mb-8">
                  <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-white">Retention Curve</h2>
                  <p className="mt-2 text-xs sm:text-sm text-slate-400">Track viewer drop-off throughout your video timeline.</p>
                </div>
                <div className="h-56 sm:h-72 lg:h-80">
                  <RetentionChart data={data.retention_curve} weakSegments={data.weak_segments} />
                </div>
              </div>
              <div className="rounded-2xl sm:rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-10 shadow-2xl backdrop-blur-xl">
                <div className="mb-6 sm:mb-8">
                  <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-white">Motion Analysis</h2>
                  <p className="mt-2 text-xs sm:text-sm text-slate-400">Intensity levels across your timeline.</p>
                </div>
                <div className="h-56 sm:h-72 lg:h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data.motion_data} margin={{ top: 5, right: 30, left: -15, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="timestamp" stroke="#94a3b8" style={{ fontSize: '12px' }} />
                      <YAxis stroke="#94a3b8" style={{ fontSize: '12px' }} domain={[0, 1]} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(6, 11, 24, 0.95)',
                          border: '1px solid rgba(255,255,255,0.1)',
                          borderRadius: '12px',
                          boxShadow: '0 20px 60px rgba(0,0,0,0.4)'
                        }}
                        labelStyle={{ color: '#fff' }}
                      />
                      <ReferenceLine y={0.3} stroke="#ef4444" strokeDasharray="5 5" />
                      <Line type="monotone" dataKey="motion" stroke="#8b5cf6" strokeWidth={3} dot={false} isAnimationActive />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </section>

            <section className="grid gap-6 sm:gap-8 lg:grid-cols-2">
              <div className="rounded-2xl sm:rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-10 shadow-2xl backdrop-blur-xl">
                <h2 className="mb-6 sm:mb-8 text-lg sm:text-xl lg:text-2xl font-bold text-white">Weak Segments</h2>
                <WeakSegments segments={data.weak_segments} />
              </div>
              <div className="rounded-2xl sm:rounded-3xl border border-white/10 bg-white/5 p-6 sm:p-10 shadow-2xl backdrop-blur-xl">
                <div className="mb-6 sm:mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <h2 className="text-lg sm:text-xl lg:text-2xl font-bold text-white">AI Suggestions</h2>
                    <p className="mt-2 text-xs sm:text-sm text-slate-400">Priority-ordered recommendations.</p>
                  </div>
                  <button
                    onClick={() => {
                      setScreen('idle');
                      setJobId(null);
                    }}
                    className="rounded-lg bg-gradient-to-r from-purple-500 to-blue-600 px-4 py-2 text-xs sm:text-sm font-semibold text-white shadow-lg shadow-purple-500/40 transition hover:opacity-95 whitespace-nowrap flex-shrink-0"
                  >
                    Analyze Another
                  </button>
                </div>
                <SuggestionCards suggestions={data.suggestions} />
              </div>
            </section>
          </main>
        </div>
      </div>
    );
  }

  return null;
}

export default App;
