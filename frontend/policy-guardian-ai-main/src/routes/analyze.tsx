import { createFileRoute } from '@tanstack/react-router';
import { useState } from 'react';
import { toast } from 'sonner';
import { FileUploader } from '@/components/FileUploader';
import { AnalysisLoader } from '@/components/AnalysisLoader';
import { AnalysisResults } from '@/components/AnalysisResults';
import { uploadAndAnalyze, type AnalysisResponse } from '@/lib/api';
import { mockAnalysis } from '@/lib/mock-data';

export const Route = createFileRoute('/analyze')({
  component: AnalyzePage,
  head: () => ({
    meta: [
      { title: 'Analyze Policy — Insurance Risk Analyzer AI' },
      { name: 'description', content: 'Upload and analyze insurance policy PDFs with AI-powered risk detection.' },
    ],
  }),
});

function AnalyzePage() {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  const handleAnalyze = async (file: File) => {
    setIsUploading(true);
    setUploadProgress(0);
    setResult(null);

    try {
      setIsAnalyzing(true);

      // Try real backend API
      const response = await uploadAndAnalyze(file, (pct) => {
        setUploadProgress(pct);
        if (pct >= 100) {
          setIsUploading(false);
        }
      });

      setResult(response);
      toast.success(`Analysis complete! Risk level: ${response.risk_level}`);
    } catch (error: any) {
      console.warn('Backend unavailable, using demo data:', error?.message);
      setIsUploading(false);

      // Simulate processing delay with mock data
      toast.info('Backend not reachable — showing demo results');
      await new Promise((r) => setTimeout(r, 4000));

      setResult({ ...mockAnalysis, filename: file.name });
      toast.success(`Demo analysis complete! Risk level: ${mockAnalysis.risk_level}`);
    } finally {
      setIsAnalyzing(false);
      setIsUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-foreground tracking-tight">Analyze Policy</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Upload an insurance policy PDF to detect risks, hidden conditions, and contradictions
        </p>
      </div>

      {!isAnalyzing && !result && (
        <FileUploader
          onFileSelect={handleAnalyze}
          isUploading={isUploading}
          uploadProgress={Math.min(uploadProgress, 100)}
        />
      )}

      {isAnalyzing && <AnalysisLoader />}

      {result && !isAnalyzing && (
        <>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Results for</p>
              <p className="text-sm font-medium text-foreground">{result.filename}</p>
            </div>
            <button
              onClick={() => setResult(null)}
              className="text-sm text-primary hover:underline font-medium"
            >
              Analyze Another
            </button>
          </div>
          <AnalysisResults result={result} />
        </>
      )}
    </div>
  );
}
