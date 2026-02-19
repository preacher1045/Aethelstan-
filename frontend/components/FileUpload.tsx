'use client';

import { useState, useRef } from 'react';
import { uploadPcap } from '@/lib/api';

interface FileUploadProps {
    onUploadSuccess?: (sessionId: string) => void;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [dragActive, setDragActive] = useState(false);
    const fileInputRef = useRef<HTMLInputElement>(null);

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
        setDragActive(true);
        } else if (e.type === "dragleave") {
        setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFileSelect(e.dataTransfer.files[0]);
        }
    };

    const handleFileSelect = (selectedFile: File) => {
        const ext = selectedFile.name.split('.').pop()?.toLowerCase();
        if (ext !== 'pcap' && ext !== 'pcapng') {
        setError('Only .pcap and .pcapng files are supported');
        return;
        }
        
        setFile(selectedFile);
        setError(null);
    };

    const handleUpload = async () => {
        if (!file) return;

        setUploading(true);
        setError(null);

        try {
        const response = await uploadPcap(file);
        setFile(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
        onUploadSuccess?.(response.session_id);
        } catch (err) {
        setError(err instanceof Error ? err.message : 'Upload failed');
        } finally {
        setUploading(false);
        }
    };

    return (
        <div className="w-full max-w-2xl mx-auto">
        <div
            className={`relative border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
            dragActive
                ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20'
                : 'border-zinc-300 dark:border-zinc-700 hover:border-zinc-400 dark:hover:border-zinc-600'
            }`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
        >
            <input
            ref={fileInputRef}
            type="file"
            accept=".pcap,.pcapng"
            onChange={(e) => e.target.files && handleFileSelect(e.target.files[0])}
            className="hidden"
            id="file-upload"
            />
            
            <div className="space-y-4">
            <div className="text-zinc-400">
                <svg
                className="mx-auto h-12 w-12"
                stroke="currentColor"
                fill="none"
                viewBox="0 0 48 48"
                aria-hidden="true"
                >
                <path
                    d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
                </svg>
            </div>
            
            <div className="text-sm">
                <label
                htmlFor="file-upload"
                className="cursor-pointer font-medium text-blue-600 hover:text-blue-500 dark:text-blue-400"
                >
                Choose a file
                </label>
                <span className="text-zinc-600 dark:text-zinc-400"> or drag and drop</span>
            </div>
            
            <p className="text-xs text-zinc-500">PCAP or PCAPNG files only</p>
            </div>
        </div>

        {file && (
            <div className="mt-4 p-4 bg-zinc-100 dark:bg-zinc-800 rounded-lg flex items-center justify-between">
            <div className="flex items-center space-x-3">
                <svg className="h-6 w-6 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <div>
                <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{file.name}</p>
                <p className="text-xs text-zinc-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
            </div>
            <button
                onClick={() => {
                setFile(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
            >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
            </div>
        )}

        {error && (
            <div className="mt-4 p-4 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-800 dark:text-red-200">{error}</p>
            </div>
        )}

        {file && (
            <button
            onClick={handleUpload}
            disabled={uploading}
            className="mt-4 w-full bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-400 text-white font-medium py-3 px-4 rounded-lg transition-colors disabled:cursor-not-allowed"
            >
            {uploading ? 'Uploading...' : 'Upload and Analyze'}
            </button>
        )}
        </div>
    );
    }
