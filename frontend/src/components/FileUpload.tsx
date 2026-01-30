"use client";

import { useState, useRef, useCallback } from "react";

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  isAnalyzing?: boolean;
}

export default function FileUpload({ onFileSelect, disabled, isAnalyzing }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (file: File) => {
      if (file.type === "application/pdf" || file.name.endsWith(".pdf")) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleClick = () => {
    if (!disabled && !isAnalyzing) {
      inputRef.current?.click();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-sky-100 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-sky-100 bg-sky-50">
        <h2 className="font-semibold text-sky-900">Upload Questionnaire</h2>
        <p className="text-sm text-sky-600 mt-0.5">PDF files with audit questions</p>
      </div>

      {/* Drop zone */}
      <div className="p-5">
        <div
          onClick={handleClick}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={`
            relative border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer
            ${isDragging ? "border-sky-400 bg-sky-50" : "border-sky-200 hover:border-sky-300 hover:bg-sky-50/50"}
            ${disabled || isAnalyzing ? "opacity-50 cursor-not-allowed" : ""}
          `}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".pdf"
            onChange={handleChange}
            className="hidden"
            disabled={disabled || isAnalyzing}
          />

          {isAnalyzing ? (
            <div className="space-y-3">
              <div className="w-10 h-10 mx-auto rounded-full bg-sky-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-sky-600 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              </div>
              <p className="text-sky-700 font-medium">Analyzing...</p>
              <p className="text-sky-500 text-sm">{selectedFile?.name}</p>
            </div>
          ) : selectedFile ? (
            <div className="space-y-3">
              <div className="w-10 h-10 mx-auto rounded-full bg-emerald-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <p className="text-sky-800 font-medium">{selectedFile.name}</p>
              <p className="text-sky-500 text-sm">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="w-10 h-10 mx-auto rounded-full bg-sky-100 flex items-center justify-center">
                <svg className="w-5 h-5 text-sky-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <div>
                <p className="text-sky-700 font-medium">Drop PDF here</p>
                <p className="text-sky-500 text-sm mt-1">or click to browse</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
