import { formatTime } from '../src/utils';

export default function WeakSegments({ segments }) {
  if (!segments || segments.length === 0) {
    return (
      <div className="text-center py-8 sm:py-12 lg:py-16">
        <div className="mx-auto mb-3 sm:mb-4 h-12 sm:h-16 w-12 sm:w-16 rounded-2xl bg-green-500/20 flex items-center justify-center">
          <svg style={{ width: '24px', height: '24px' }} fill="none" viewBox="0 0 24 24" stroke="currentColor" className="text-green-400">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <p className="text-green-300 font-semibold text-base sm:text-lg">No significant drop-off detected</p>
        <p className="text-slate-400 text-xs sm:text-sm mt-1 sm:mt-2">Your video maintains strong viewer retention throughout.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2 sm:space-y-3">
      {segments.map((segment, index) => (
        <div
          key={index}
          className="group rounded-lg sm:rounded-xl border border-red-500/30 bg-red-500/5 p-3 sm:p-4 transition hover:bg-red-500/10 hover:border-red-500/50 cursor-default"
        >
          <div className="flex items-start justify-between gap-2 sm:gap-3">
            <div className="flex items-start gap-2 sm:gap-3 flex-1 min-w-0">
              <div className="flex-shrink-0 mt-1 h-2 w-2 rounded-full bg-red-400 group-hover:scale-125 transition" />
              <div className="min-w-0 flex-1">
                <p className="text-white font-semibold text-xs sm:text-sm">
                  {formatTime(segment.start)} – {formatTime(segment.end)}
                </p>
                <p className="text-red-400 text-xs mt-0.5 sm:mt-1 font-medium">High drop-off risk</p>
              </div>
            </div>
            <div className="flex-shrink-0">
              <span className="inline-flex rounded-lg bg-red-500/20 px-2 sm:px-3 py-1 text-xs font-semibold text-red-300 whitespace-nowrap">Alert</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
