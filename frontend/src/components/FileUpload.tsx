'use client';

import { useCallback, useState, useRef } from 'react';
import { useTranslations } from 'next-intl';
import { Upload, FileText, AlertCircle, CheckCircle2 } from 'lucide-react';

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  selectedFile?: File | null;
  selectedFileName?: string | null;
}

export default function FileUpload({ onFileSelect, disabled, selectedFile, selectedFileName }: FileUploadProps) {
  const t = useTranslations('upload');
  const [isDragActive, setIsDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    const validTypes = ['application/pdf', 'text/plain'];
    const maxSize = 50 * 1024 * 1024; // 50 MB

    if (!validTypes.includes(file.type) && !file.name.endsWith('.txt') && !file.name.endsWith('.pdf')) {
      return t('error.invalidType');
    }
    if (file.size > maxSize) {
      return t('error.tooLarge');
    }
    return null;
  };

  const handleFile = useCallback(
    (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        return;
      }
      setError(null);
      onFileSelect(file);
    },
    [onFileSelect, t]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragActive(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleClick = () => {
    inputRef.current?.click();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          relative cursor-pointer rounded-2xl border-2 border-dashed p-12
          transition-all duration-300 ease-out
          ${
            isDragActive
              ? 'border-blue-500 bg-blue-900/20 scale-[1.02] shadow-lg shadow-blue-900/20'
              : 'border-gray-700 hover:border-blue-600 hover:bg-gray-800/40'
          }
          ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
          ${selectedFile ? 'border-green-600 bg-green-900/20' : ''}
        `}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt"
          onChange={handleChange}
          disabled={disabled}
          className="hidden"
          aria-label={t('browse')}
        />

        <div className="flex flex-col items-center gap-4 text-center">
          {selectedFile || selectedFileName ? (
            <>
              <div className="w-16 h-16 rounded-2xl bg-green-900/40 flex items-center justify-center animate-fade-in">
                <CheckCircle2 className="w-8 h-8 text-green-400" />
              </div>
              <div>
                <p className="font-medium text-gray-200">{selectedFile?.name || selectedFileName}</p>
                {selectedFile && (
                  <p className="text-sm text-gray-500 mt-1">
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                )}
              </div>
            </>
          ) : isDragActive ? (
            <>
              <div className="w-16 h-16 rounded-2xl bg-blue-900/40 flex items-center justify-center animate-bounce">
                <Upload className="w-8 h-8 text-blue-400" />
              </div>
              <p className="text-lg font-medium text-blue-400">{t('dragActive')}</p>
            </>
          ) : (
            <>
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-900/30 to-purple-900/30 flex items-center justify-center">
                <FileText className="w-8 h-8 text-blue-400" />
              </div>
              <div>
                <p className="text-lg font-medium text-gray-300">{t('dragDrop')}</p>
                <p className="text-sm text-gray-500 mt-1">{t('fileTypes')}</p>
              </div>
              <span className="inline-flex items-center gap-2 px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 text-white text-sm font-medium rounded-xl shadow-lg shadow-blue-900/30 hover:shadow-xl hover:shadow-blue-900/40 hover:from-blue-500 hover:to-blue-600 transition-all duration-200">
                <Upload className="w-4 h-4" />
                {t('browse')}
              </span>
            </>
          )}
        </div>

        {/* Animated gradient border on hover */}
        <div
          className={`
            absolute inset-0 rounded-2xl transition-opacity duration-300 pointer-events-none
            ${isDragActive ? 'opacity-100' : 'opacity-0'}
          `}
          style={{
            background:
              'linear-gradient(135deg, rgba(59, 130, 246, 0.08), rgba(147, 51, 234, 0.08))',
          }}
        />
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-4 flex items-center gap-2 text-sm text-red-400 bg-red-900/30 rounded-xl px-4 py-3 animate-fade-in border border-red-800/30">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}