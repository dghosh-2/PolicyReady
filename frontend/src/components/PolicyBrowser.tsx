"use client";

import { useState, useEffect } from "react";
import { fetchPolicies, fetchFolderContents } from "@/lib/api";
import type { PolicyFolder, PolicyFile, IndexStats } from "@/types";
import PDFPreviewModal from "./PDFPreviewModal";

interface PolicyBrowserProps {
  onStatsLoaded?: (stats: IndexStats) => void;
}

export default function PolicyBrowser({ onStatsLoaded }: PolicyBrowserProps) {
  const [folders, setFolders] = useState<PolicyFolder[]>([]);
  const [totalFiles, setTotalFiles] = useState(0);
  const [expandedFolder, setExpandedFolder] = useState<string | null>(null);
  const [folderFiles, setFolderFiles] = useState<Record<string, PolicyFile[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [previewFile, setPreviewFile] = useState<{ folder: string; name: string } | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [policiesData, statsRes] = await Promise.all([
          fetchPolicies(),
          fetch("http://localhost:8000/index/stats").then(r => r.ok ? r.json() : null).catch(() => null),
        ]);
        setFolders(policiesData.folders);
        setTotalFiles(policiesData.total_files);
        if (statsRes) {
          onStatsLoaded?.(statsRes);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load policies");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [onStatsLoaded]);

  const toggleFolder = async (folderName: string) => {
    if (expandedFolder === folderName) {
      setExpandedFolder(null);
      return;
    }

    setExpandedFolder(folderName);

    if (!folderFiles[folderName]) {
      try {
        const data = await fetchFolderContents(folderName);
        setFolderFiles((prev) => ({ ...prev, [folderName]: data.files }));
      } catch {
        // Silently fail
      }
    }
  };

  const handleFileClick = (folder: string, fileName: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setPreviewFile({ folder, name: fileName });
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-sky-100">
        <div className="animate-pulse space-y-4">
          <div className="h-5 bg-sky-100 rounded w-1/3"></div>
          <div className="space-y-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-11 bg-sky-50 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-red-200">
        <p className="text-red-600">{error}</p>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-2xl shadow-sm border border-sky-100 overflow-hidden">
        {/* Header */}
        <div className="px-5 py-4 border-b border-sky-100 bg-sky-50">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-sky-900">Policy Database</h2>
            <span className="text-sm text-sky-600">{totalFiles} documents</span>
          </div>
        </div>

        {/* Folder list */}
        <div className="max-h-[420px] overflow-y-auto">
          {folders.map((folder, idx) => (
            <div key={folder.name} className={`animate-fade-in stagger-${Math.min(idx + 1, 10)}`}>
              <button
                onClick={() => toggleFolder(folder.name)}
                className="w-full px-5 py-3 flex items-center justify-between hover:bg-sky-50 transition-colors border-b border-sky-50"
              >
                <div className="flex items-center gap-3">
                  <svg
                    className={`w-4 h-4 text-sky-400 transition-transform ${
                      expandedFolder === folder.name ? "rotate-90" : ""
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                  <span className="font-medium text-sky-800">{folder.name}</span>
                </div>
                <span className="text-xs text-sky-500 bg-sky-100 px-2 py-0.5 rounded">
                  {folder.file_count}
                </span>
              </button>

              {/* Expanded files */}
              {expandedFolder === folder.name && folderFiles[folder.name] && (
                <div className="bg-sky-50/50 border-b border-sky-100">
                  {folderFiles[folder.name].map((file) => (
                    <button
                      key={file.path}
                      onClick={(e) => handleFileClick(folder.name, file.name, e)}
                      className="w-full px-5 py-2.5 pl-12 text-sm text-sky-700 hover:bg-sky-100 hover:text-sky-800 transition-colors flex items-center gap-2 text-left"
                    >
                      <svg className="w-4 h-4 text-sky-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="truncate">{file.name}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* PDF Preview Modal */}
      {previewFile && (
        <PDFPreviewModal
          folder={previewFile.folder}
          fileName={previewFile.name}
          onClose={() => setPreviewFile(null)}
        />
      )}
    </>
  );
}
