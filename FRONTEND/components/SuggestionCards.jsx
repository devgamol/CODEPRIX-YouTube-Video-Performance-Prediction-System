import { formatTime, getPriorityOrder } from '../src/utils';

export default function SuggestionCards({ suggestions }) {
  const sortedSuggestions = [...suggestions].sort((a, b) => getPriorityOrder(a.priority) - getPriorityOrder(b.priority));

  const getPriorityStyles = (priority) => {
    switch (priority) {
      case 'High':
        return {
          border: 'border-red-500/30',
          bg: 'bg-red-500/5',
          pill: 'bg-red-500/20 text-red-300',
          dot: 'bg-red-400'
        };
      case 'Medium':
        return {
          border: 'border-amber-500/30',
          bg: 'bg-amber-500/5',
          pill: 'bg-amber-500/20 text-amber-300',
          dot: 'bg-amber-400'
        };
      case 'Low':
        return {
          border: 'border-green-500/30',
          bg: 'bg-green-500/5',
          pill: 'bg-green-500/20 text-green-300',
          dot: 'bg-green-400'
        };
      default:
        return {
          border: 'border-white/10',
          bg: 'bg-white/5',
          pill: 'bg-white/10 text-white',
          dot: 'bg-white/40'
        };
    }
  };

  return (
    <div className="space-y-2 sm:space-y-3">
      {sortedSuggestions.map((suggestion, index) => {
        const styles = getPriorityStyles(suggestion.priority);
        return (
          <div
            key={index}
            className={`group rounded-lg sm:rounded-xl border transition ${styles.border} ${styles.bg} p-3 sm:p-4 lg:p-5 hover:${styles.bg.replace('5', '10')} hover:border-${styles.dot.split('-')[1]}-500/50`}
          >
            <div className="flex items-start gap-2 sm:gap-3 lg:gap-4">
              <div className={`flex-shrink-0 mt-1 h-3 w-3 rounded-full ${styles.dot} group-hover:scale-125 transition`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-start justify-between gap-2 sm:gap-3 mb-2 sm:mb-3">
                  <div className="min-w-0">
                    <p className="text-white font-bold text-xs sm:text-sm leading-tight break-words">{suggestion.issue}</p>
                  </div>
                  <span className={`inline-flex flex-shrink-0 rounded-lg px-2 sm:px-3 py-1 text-xs font-semibold ${styles.pill} whitespace-nowrap`}>
                    {suggestion.priority}
                  </span>
                </div>
                <p className="text-slate-300 text-xs sm:text-sm leading-relaxed mb-2 sm:mb-3">
                  {suggestion.reason}
                </p>
                <p className="text-slate-400 text-xs sm:text-sm leading-relaxed mb-2 sm:mb-3">💡 {suggestion.fix}</p>
                <p className="text-xs text-slate-500 font-mono">
                  {formatTime(suggestion.timestamp_start)} – {formatTime(suggestion.timestamp_end)}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
