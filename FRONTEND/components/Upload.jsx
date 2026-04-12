import { useState } from 'react';
import { uploadVideo } from '../api/client';

export default function Upload({ onUploadSuccess }) {
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState('');
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileSelect = (file) => {
    if (!file.type.startsWith('video/')) {
      setError('Please select a video file.');
      return;
    }
    setSelectedFile(file);
    setError('');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || isUploading) {
      return;
    }

    setIsUploading(true);
    setError('');
    try {
      const response = await uploadVideo(selectedFile);
      onUploadSuccess?.(response.job_id);
    } catch {
      setError('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
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
        <div className="flex min-h-[240px] flex-col items-center justify-center px-6 py-14 text-center sm:min-h-[280px]">
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
          <p className="text-3xl font-semibold leading-tight text-white sm:text-[42px]">
            {selectedFile ? selectedFile.name : 'Drag & drop your video'}
          </p>
          <p className="mt-2.5 text-base text-[#9aa4b2] sm:text-[30px]">
            {selectedFile ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB selected` : 'or click to browse (MP4, WebM, MOV - up to 2GB)'}
          </p>
        </div>
      </label>

      <input
        id="file-input"
        type="file"
        accept="video/*"
        className="hidden"
        onChange={(e) => {
          if (e.target.files[0]) {
            handleFileSelect(e.target.files[0]);
          }
        }}
      />

      {selectedFile && (
        <button
          onClick={handleUpload}
          disabled={isUploading}
          className="inline-flex h-14 min-w-[180px] items-center justify-center rounded-2xl bg-gradient-to-r from-[#5f2df5] to-[#6527e6] px-7 text-base font-semibold text-white shadow-[0_12px_30px_rgba(101,39,230,0.38)] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isUploading ? 'Uploading...' : 'Start Analysis'}
        </button>
      )}

      {error && (
        <p className="text-sm font-medium text-red-300">{error}</p>
      )}
    </div>
  );
}
