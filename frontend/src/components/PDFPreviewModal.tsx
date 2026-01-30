"use client";

import { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { fetchPDFText } from "@/lib/api";
import type { PDFChunk } from "@/types";

interface PDFPreviewModalProps {
  folder: string;
  fileName: string;
  onClose: () => void;
}

export default function PDFPreviewModal({ folder, fileName, onClose }: PDFPreviewModalProps) {
  const [pages, setPages] = useState<PDFChunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPage, setSelectedPage] = useState(1);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchPDFText(folder, fileName);
        setPages(data);
        if (data.length > 0) {
          setSelectedPage(data[0].page);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load PDF");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [folder, fileName]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleEscape);
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [onClose]);

  const currentPage = pages.find((p) => p.page === selectedPage);

  const modalContent = (
    <>
      {/* Dark overlay */}
      <div 
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          zIndex: 99998,
        }}
        onClick={onClose}
      />
      
      {/* Modal box - centered */}
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width: "90%",
          maxWidth: "900px",
          height: "80%",
          maxHeight: "600px",
          backgroundColor: "white",
          borderRadius: "16px",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          zIndex: 99999,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-sky-100 bg-sky-50">
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold text-sky-900 truncate">{fileName}</h2>
            <p className="text-sm text-sky-600">{folder}</p>
          </div>
          <button
            onClick={onClose}
            className="ml-4 p-2 hover:bg-sky-100 rounded-lg transition-colors"
          >
            <svg className="w-5 h-5 text-sky-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 flex overflow-hidden">
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="w-8 h-8 border-2 border-sky-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                <p className="text-sky-600">Loading document...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-red-600">
                <p>{error}</p>
              </div>
            </div>
          ) : (
            <>
              {/* Page selector sidebar */}
              <div className="w-24 border-r border-sky-100 overflow-y-auto bg-sky-50/50">
                {pages.map((page) => (
                  <button
                    key={page.page}
                    onClick={() => setSelectedPage(page.page)}
                    className={`w-full px-3 py-2 text-sm text-left transition-colors ${
                      selectedPage === page.page
                        ? "bg-sky-100 text-sky-700 font-medium"
                        : "text-sky-600 hover:bg-sky-100"
                    }`}
                  >
                    Page {page.page}
                  </button>
                ))}
              </div>

              {/* Text content */}
              <div className="flex-1 overflow-y-auto p-6">
                {currentPage ? (
                  <pre className="whitespace-pre-wrap font-mono text-sm text-slate-700 bg-slate-50 p-4 rounded-lg border border-slate-200 leading-relaxed">
                    {currentPage.text}
                  </pre>
                ) : (
                  <p className="text-sky-500">No content available</p>
                )}
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-sky-100 bg-sky-50 flex items-center justify-between">
          <span className="text-sm text-sky-600">{pages.length} pages extracted</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-sky-500 text-white text-sm font-medium rounded-lg hover:bg-sky-600 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </>
  );

  if (!mounted) return null;

  return createPortal(modalContent, document.body);
}
