import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceArea, ReferenceLine, ResponsiveContainer } from 'recharts';
import { formatTime } from '../src/utils';

export default function RetentionChart({ data, weakSegments }) {
  const formatXAxis = (tickItem) => formatTime(tickItem);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart data={data} margin={{ top: 5, right: 30, left: -15, bottom: 5 }}>
        <defs>
          <linearGradient id="colorRetention" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis
          dataKey="time"
          stroke="#94a3b8"
          tickFormatter={formatXAxis}
          style={{ fontSize: '11px' }}
        />
        <YAxis
          stroke="#94a3b8"
          style={{ fontSize: '11px' }}
          domain={[0, 100]}
        />
        <Tooltip
          formatter={(value) => [`${value}%`, 'Retention']}
          labelFormatter={(label) => `Time: ${formatTime(label)}`}
          contentStyle={{
            backgroundColor: 'rgba(6, 11, 24, 0.95)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '12px',
            boxShadow: '0 20px 60px rgba(0,0,0,0.4)',
            fontSize: '12px'
          }}
          labelStyle={{ color: '#fff' }}
        />
        <ReferenceLine
          y={70}
          stroke="#ef4444"
          strokeDasharray="5 5"
          label={{ value: 'Danger Zone', position: 'right', fill: '#ef4444', fontSize: 11 }}
        />
        {weakSegments.map((segment, index) => (
          <ReferenceArea
            key={index}
            x1={segment.start}
            x2={segment.end}
            fill="#ef4444"
            fillOpacity={0.1}
          />
        ))}
        <Area
          type="monotone"
          dataKey="retention"
          stroke="#8b5cf6"
          fill="url(#colorRetention)"
          strokeWidth={2.5}
          dot={false}
          isAnimationActive
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
