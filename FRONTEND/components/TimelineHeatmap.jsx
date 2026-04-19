const getBarColor = (level) => {
  if (level === 'high') return 'bg-green-500';
  if (level === 'medium') return 'bg-yellow-400';
  return 'bg-red-500';
};

export default function TimelineHeatmap({ heatmap = [] }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-6 sm:p-8 shadow-2xl backdrop-blur-xl">
      <h2 className="text-2xl font-bold text-white">Timeline Heatmap</h2>

      <div className="mt-6 overflow-x-auto">
        <div className="mx-auto w-max min-w-full">
          <div className="flex items-end justify-center gap-4 px-1">
            {heatmap.map((item, i) => (
              <div
                key={i}
                className={`w-16 rounded-md transition-all duration-200 hover:scale-105 ${getBarColor(item.level)}`}
                style={{ height: `${Math.max(48, Math.min(84, Number(item.value) * 0.7))}px` }}
                title={`t=${item.time}s | ${Number(item.value).toFixed(1)}%`}
              />
            ))}
          </div>
          <div className="mt-1 h-px w-full bg-slate-500/50" />
          <div className="mt-1 flex justify-center gap-4 px-1">
            {heatmap.map((_, i) => (
              <span key={i} className="w-16 text-center text-sm text-slate-400">
                S{i + 1}
              </span>
            ))}
          </div>
        </div>
      </div>

      <p className="mt-6 text-base text-slate-400">Green = high engagement, Red = low engagement</p>
    </div>
  );
}
