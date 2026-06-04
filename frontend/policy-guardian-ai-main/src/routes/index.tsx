import { createFileRoute } from '@tanstack/react-router';
import { useNavigate } from '@tanstack/react-router';
import { motion } from 'framer-motion';
import { Upload, Shield, ZapOff, AlertCircle, CheckCircle, ArrowRight } from 'lucide-react';
import { useState, useRef } from 'react';

export const Route = createFileRoute('/')({
  component: DashboardPage,
  head: () => ({
    meta: [
      { title: 'Policy Guardian AI — Insurance Risk Analyzer' },
      { name: 'description', content: 'AI-powered insurance policy risk analysis using NLP and deep learning.' },
    ],
  }),
});

function DashboardPage() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleFileUpload = (file: File) => {
    if (file.type === 'application/pdf') {
      // Store file in state and navigate to analyze
      sessionStorage.setItem('uploadedFile', file.name);
      navigate({ to: '/analyze', search: { file: file.name } });
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files;
    if (files && files.length > 0) {
      handleFileUpload(files[0]);
    }
  };

  const pipelineSteps = [
    { icon: Upload, title: 'Upload PDF', desc: 'Upload your insurance policy document' },
    { icon: Shield, title: 'Extract Clauses', desc: 'AI identifies coverage, exclusions & conditions' },
    { icon: AlertCircle, title: 'Detect Hidden Risks', desc: 'Find contradictions and hidden conditions' },
    { icon: CheckCircle, title: 'Risk Scoring', desc: 'Calculate comprehensive risk assessment' },
  ];

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
        <div>
          <h1 className="text-4xl font-bold text-foreground mb-2">Policy Guardian AI</h1>
          <p className="text-lg text-muted-foreground">
            Automated detection of hidden exclusions and contradictions in insurance policies using advanced NLP and deep learning.
          </p>
        </div>
      </motion.div>

      {/* Project Description */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.1 }}
        className="bg-card border border-border rounded-lg p-6 space-y-4"
      >
        <h2 className="text-xl font-semibold text-foreground">About This Project</h2>
        <div className="space-y-3 text-muted-foreground text-sm leading-relaxed">
          <p>
            <strong>Policy Guardian AI</strong> is an intelligent system that analyzes insurance policies to identify hidden risks and contradictions that policyholders might miss.
          </p>
          <p>
            Using fine-tuned BERT models and Natural Language Inference (NLI), the system:
          </p>
          <ul className="list-disc list-inside space-y-2 ml-2">
            <li>Classifies clauses into coverage, exclusions, and conditions</li>
            <li>Detects logical contradictions between policy sections</li>
            <li>Identifies hidden conditions that may reduce coverage</li>
            <li>Provides a comprehensive risk score with actionable insights</li>
          </ul>
        </div>
      </motion.div>

      {/* Pipeline Workflow */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.2 }}
        className="space-y-4"
      >
        <h2 className="text-xl font-semibold text-foreground">Analysis Pipeline</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {pipelineSteps.map((step, idx) => {
            const Icon = step.icon;
            return (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 + idx * 0.05 }}
                className="relative"
              >
                <div className="bg-card border border-border rounded-lg p-4 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="bg-primary/10 p-2 rounded-lg">
                      <Icon className="h-5 w-5 text-primary" />
                    </div>
                    {idx < pipelineSteps.length - 1 && (
                      <motion.div
                        animate={{ x: [0, 4, 0] }}
                        transition={{ duration: 2, repeat: Infinity }}
                        className="absolute -right-5 top-1/2 transform -translate-y-1/2 hidden lg:block"
                      >
                        <ArrowRight className="h-4 w-4 text-border" />
                      </motion.div>
                    )}
                  </div>
                  <div>
                    <h3 className="font-semibold text-foreground text-sm">{step.title}</h3>
                    <p className="text-xs text-muted-foreground mt-1">{step.desc}</p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>

      {/* Upload Section */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }} 
        animate={{ opacity: 1, y: 0 }} 
        transition={{ delay: 0.4 }}
        className="space-y-4"
      >
        <h2 className="text-xl font-semibold text-foreground">Get Started</h2>
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors cursor-pointer ${
            isDragging 
              ? 'border-primary bg-primary/5' 
              : 'border-border bg-card hover:bg-accent/50'
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={handleFileSelect}
            className="hidden"
          />
          <div className="space-y-3">
            <motion.div animate={{ scale: isDragging ? 1.1 : 1 }} className="inline-block">
              <Upload className="h-10 w-10 text-primary mx-auto" />
            </motion.div>
            <div>
              <p className="text-foreground font-semibold">Drop your PDF here or click to browse</p>
              <p className="text-sm text-muted-foreground mt-1">Upload an insurance policy PDF to analyze</p>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
