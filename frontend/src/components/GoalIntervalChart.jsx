import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Cell, ResponsiveContainer, LabelList,
} from 'recharts';
import { probToColor } from '../utils/colorScale';
import { toPercent } from '../utils/oddsConverter';

const INTERVAL_LABELS = {
  '0-15': '0–15\'',
  '16-30': '16–30\'',
  '31-45': '31–45\'',
  '46-60': '46–60\'',
  '61-75': '61–75\'',
  '76-90': '76–90\'',
  '90+': '90+\'',
};

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const prob = payload[0].value;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs border border-[#1F2937]">
      <div className="font-heading font-bold text-text-primary mb-0.5">
        {INTERVAL_LABELS[label] || label}
      </div>
      <div className="font-semibold" style={{ color: probToColor(prob) }}>
        {toPercent(prob)}
      </div>
    </div>
  );
};

export default function GoalIntervalChart({ goalInterval = {} }) {
  const data = Object.entries(goalInterval).map(([key, prob]) => ({
    interval: key,
    probability: prob,
    label: INTERVAL_LABELS[key] || key,
  }));

  if (data.length === 0) return (
    <div className="text-center text-text-muted text-sm py-6">No interval data</div>
  );

  return (
    <div className="animate-fade-in">
      <div className="text-xs text-text-muted mb-3 text-center">
        Probability of first goal in each 15-minute interval
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 16, right: 8, left: -28, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
          <XAxis
            dataKey="interval"
            tick={{ fill: '#9CA3AF', fontSize: 10 }}
            tickFormatter={(v) => INTERVAL_LABELS[v] || v}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: '#9CA3AF', fontSize: 9 }}
            tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            axisLine={false}
            tickLine={false}
            domain={[0, 'dataMax + 0.05']}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
          <Bar dataKey="probability" radius={[4, 4, 0, 0]} maxBarSize={40}>
            {data.map((entry, i) => (
              <Cell key={i} fill={probToColor(entry.probability)} />
            ))}
            <LabelList
              dataKey="probability"
              position="top"
              formatter={(v) => `${(v * 100).toFixed(0)}%`}
              style={{ fill: '#9CA3AF', fontSize: 9 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Highlight the peak interval */}
      {data.length > 0 && (() => {
        const peak = data.reduce((a, b) => (a.probability > b.probability ? a : b));
        return (
          <div className="mt-3 text-center text-xs text-text-secondary">
            Most likely interval:{' '}
            <span className="font-bold text-accent-green">{INTERVAL_LABELS[peak.interval]}</span>
            {' '}({toPercent(peak.probability)})
          </div>
        );
      })()}
    </div>
  );
}
