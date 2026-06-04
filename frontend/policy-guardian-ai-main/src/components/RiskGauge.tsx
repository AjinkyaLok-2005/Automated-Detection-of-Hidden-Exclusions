import { motion } from 'framer-motion';

interface RiskGaugeProps {
  score: number;
  level: string;
  size?: number;
}

export function RiskGauge({ score, level, size = 180 }: RiskGaugeProps) {
  const radius = (size - 20) / 2;
  const circumference = Math.PI * radius;
  const progress = score * circumference;

  const levelColor = () => {
    switch (level) {
      case 'Low': return 'var(--risk-low)';
      case 'Medium': return 'var(--risk-medium)';
      case 'High': return 'var(--risk-high)';
      case 'Very High': return 'var(--risk-very-high)';
      default: return 'var(--primary)';
    }
  };

  const levelBg = () => {
    switch (level) {
      case 'Low': return 'bg-risk-low/15 text-risk-low';
      case 'Medium': return 'bg-risk-medium/15 text-risk-medium';
      case 'High': return 'bg-risk-high/15 text-risk-high';
      case 'Very High': return 'bg-risk-very-high/15 text-risk-very-high';
      default: return 'bg-primary/15 text-primary';
    }
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ width: size, height: size / 2 + 20 }}>
        <svg
          width={size}
          height={size / 2 + 20}
          viewBox={`0 0 ${size} ${size / 2 + 20}`}
        >
          <path
            d={`M 10 ${size / 2 + 10} A ${radius} ${radius} 0 0 1 ${size - 10} ${size / 2 + 10}`}
            fill="none"
            stroke="var(--border)"
            strokeWidth="8"
            strokeLinecap="round"
          />
          <motion.path
            d={`M 10 ${size / 2 + 10} A ${radius} ${radius} 0 0 1 ${size - 10} ${size / 2 + 10}`}
            fill="none"
            stroke={levelColor()}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: circumference - progress }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
          <motion.span
            className="text-3xl font-bold text-foreground font-mono"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            {(score * 100).toFixed(0)}%
          </motion.span>
        </div>
      </div>
      <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${levelBg()}`}>
        {level} Risk
      </span>
    </div>
  );
}

interface RiskBadgeProps {
  level: string;
  size?: 'sm' | 'md';
}

export function RiskBadge({ level, size = 'sm' }: RiskBadgeProps) {
  const classes = () => {
    const base = size === 'sm' ? 'px-2 py-0.5 text-[10px]' : 'px-3 py-1 text-xs';
    switch (level) {
      case 'Low': return `${base} bg-risk-low/15 text-risk-low`;
      case 'Medium': return `${base} bg-risk-medium/15 text-risk-medium`;
      case 'High': return `${base} bg-risk-high/15 text-risk-high`;
      case 'Very High': return `${base} bg-risk-very-high/15 text-risk-very-high`;
      default: return `${base} bg-muted text-muted-foreground`;
    }
  };

  return (
    <span className={`inline-flex items-center rounded-full font-semibold ${classes()}`}>
      {level}
    </span>
  );
}
