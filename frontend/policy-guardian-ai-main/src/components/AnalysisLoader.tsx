import { motion } from 'framer-motion';
import { Shield, Brain, Search } from 'lucide-react';

export function AnalysisLoader() {
  const steps = [
    { icon: Search, label: 'Extracting clauses from PDF...', delay: 0 },
    { icon: Shield, label: 'Classifying with BERT model...', delay: 1.5 },
    { icon: Brain, label: 'Running NLI contradiction detection...', delay: 3 },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center gap-8 py-12"
    >
      <div className="relative">
        <motion.div
          className="h-20 w-20 rounded-2xl bg-primary/10 flex items-center justify-center"
          animate={{ rotate: [0, 5, -5, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        >
          <Brain className="h-10 w-10 text-primary" />
        </motion.div>
        <motion.div
          className="absolute inset-0 rounded-2xl border-2 border-primary/30"
          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0, 0.5] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        />
      </div>

      <div className="space-y-3 text-center">
        <h3 className="text-lg font-semibold text-foreground">AI Analysis in Progress</h3>
        <p className="text-sm text-muted-foreground max-w-sm">
          Our NLP engine is processing your policy document
        </p>
      </div>

      <div className="space-y-3 w-full max-w-xs">
        {steps.map((step, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: step.delay, duration: 0.4 }}
            className="flex items-center gap-3"
          >
            <motion.div
              className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent"
              animate={{ backgroundColor: ['var(--accent)', 'var(--primary)', 'var(--accent)'] }}
              transition={{ delay: step.delay + 0.5, duration: 1.5, repeat: Infinity }}
            >
              <step.icon className="h-4 w-4 text-foreground" />
            </motion.div>
            <span className="text-sm text-muted-foreground">{step.label}</span>
          </motion.div>
        ))}
      </div>

      <div className="w-full max-w-xs">
        <div className="h-1 w-full rounded-full bg-accent overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-primary"
            initial={{ width: '0%' }}
            animate={{ width: '100%' }}
            transition={{ duration: 5, ease: 'linear' }}
          />
        </div>
      </div>
    </motion.div>
  );
}
