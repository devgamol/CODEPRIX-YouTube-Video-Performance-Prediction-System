import { useState } from 'react';
import { uploadVideo } from '../api/client';

const MAX_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024;
const ALLOWED_EXTENSIONS = ['.mp4', '.mov', '.webm', '.mkv'];

export default function Upload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedJobId, setUploadedJobId] = useState(null);
  const [error, setError] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);

  const startUpload = async (file) => {
    if (!file || isUploading) {
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setUploadedJobId(null);
    setError('');
    try {
      setUploadProgress(20);
      const response = await uploadVideo(file);
      setUploadProgress(100);
      setUploadedJobId(response?.job_id || null);
    } catch (err) {
      setUploadProgress(0);
      setUploadedJobId(null);
      setError(err?.message || 'Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileSelect = (file) => {
    const lowerName = String(file.name || '').toLowerCase();
    const hasAllowedExt = ALLOWED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
    const mimeLooksVideo = String(file.type || '').startsWith('video/');

    if (!mimeLooksVideo && !hasAllowedExt) {
      setError('Please select a video file.');
      return;
    }
    if (file.size > MAX_UPLOAD_BYTES) {
      setError('File must be smaller than 2GB.');
      return;
    }
    setSelectedFile(file);
    setUploadProgress(0);
    setUploadedJobId(null);
    setError('');
    startUpload(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  return (
    <div className="space-y-6">
      <label
        htmlFor="file-input"
        className={`group block cursor-pointer rounded-[22px] border-2 border-dashed transition-all duration-200 ${
          isDragOver
            ? 'border-[#7c3aed] bg-[#090f1e]'
            : 'border-[#3b4559] bg-[#040b1b] hover:border-[#5b667c]'
        }`}
        onDrop={handleDrop}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragOver(true);
        }}
        onDragLeave={() => setIsDragOver(false)}
      >
        <div className="flex min-h-[220px] flex-col items-center justify-center px-6 py-12 text-center sm:min-h-[260px]">
          <div className="mb-7 flex h-20 w-20 items-center justify-center rounded-2xl bg-[#191436]">
            <svg
              className="h-10 w-10 text-[#7c3aed]"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <path d="M7 10l5-5 5 5" />
              <path d="M12 5v11" />
            </svg>
          </div>
          <p className="text-2xl font-semibold leading-tight text-white sm:text-4xl">
            {selectedFile ? selectedFile.name : 'Drag & drop your video'}
          </p>
          <p className="mt-2.5 text-sm text-[#9aa4b2] sm:text-lg">
            {selectedFile ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB selected` : 'or click to browse (MP4, WebM, MOV - up to 2GB)'}
          </p>
        </div>
      </label>

      <input
        id="file-input"
        type="file"
        accept="video/*"
        className="hidden"
        disabled={isUploading}
        onChange={(e) => {
          if (e.target.files[0]) {
            handleFileSelect(e.target.files[0]);
          }
        }}
      />

      {selectedFile && (
        <div className="w-full rounded-2xl border border-[#243041] bg-[#071326] p-4 sm:p-5">
          <div className="mb-3 flex items-center justify-between">
            <p className="text-sm font-medium text-[#b2bfd1]">Upload Progress</p>
            <p className="text-sm font-semibold text-[#dbe5f3]">{uploadProgress}%</p>
          </div>
          <div className="h-3 w-full overflow-hidden rounded-full bg-[#111d32] ring-1 ring-[#2a3a59]">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#5f2df5] via-[#6d33f8] to-[#7d5dff] transition-all duration-300"
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
          <button
            onClick={() => onUploadSuccess?.(uploadedJobId)}
            disabled={isUploading || uploadProgress !== 100 || !uploadedJobId}
            className="mx-auto mt-4 flex h-14 w-full max-w-[260px] items-center justify-center rounded-2xl bg-gradient-to-r from-[#5f2df5] to-[#6527e6] px-7 text-base font-semibold text-white shadow-[0_12px_30px_rgba(101,39,230,0.38)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isUploading ? 'Uploading...' : 'Analyze Video'}
          </button>
        </div>
      )}

      {error && (
        <p className="text-sm font-medium text-red-300">{error}</p>
      )}
    </div>
  );
}
