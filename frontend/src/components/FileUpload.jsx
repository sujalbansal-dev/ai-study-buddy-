import React, { useState, useRef } from 'react';
import axios from 'axios';

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "");
import { UploadCloud, File, CheckCircle, AlertCircle, Loader } from 'lucide-react';

const FileUpload = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    const droppedFile = e.dataTransfer.files[0];
    validateAndSetFile(droppedFile);
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    validateAndSetFile(selectedFile);
  };

  const validateAndSetFile = (selectedFile) => {
    setError('');
    setSuccess('');
    if (selectedFile && selectedFile.type === 'application/pdf') {
      setFile(selectedFile);
    } else {
      setFile(null);
      setError('Please select a valid PDF file.');
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setSuccess('File uploaded successfully!');
      if (onUploadSuccess) {
        onUploadSuccess(response.data.document_id);
      }
    } catch (err) {
      console.error(err);
      if (err.response?.status === 413) {
        setError('The file is too large for the server. Please try a smaller PDF.');
      } else if (err.response?.data?.detail) {
        setError(err.response.data.detail);
      } else {
        setError('Failed to upload file. Is the backend running?');
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="w-full bg-white rounded-xl shadow-sm border border-slate-200 p-6 mt-4">
      <h3 className="text-slate-800 font-semibold mb-3">Upload PDF Material</h3>
      
      <div 
        className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer shadow-sm ${
          isDragging ? 'border-blue-400 bg-blue-50' : 'border-slate-300 bg-slate-50 hover:border-blue-400 hover:bg-white'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input 
          type="file" 
          className="hidden" 
          ref={fileInputRef} 
          accept=".pdf" 
          onChange={handleFileChange} 
        />
        
        {file ? (
          <div className="flex justify-center">
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 flex items-center justify-between w-full max-w-md shadow-sm">
              <div className="flex items-center space-x-3 overflow-hidden">
                <File className="w-6 h-6 text-blue-600 flex-shrink-0" />
                <span className="text-sm text-slate-700 font-medium truncate">{file.name}</span>
              </div>
              <p className="text-xs text-slate-500 whitespace-nowrap ml-4">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center">
            <div className="bg-blue-100 p-4 rounded-full inline-block mb-4 shadow-sm border border-blue-200">
              <UploadCloud className="w-10 h-10 text-blue-600" />
            </div>
            <p className="text-lg font-medium text-slate-800 mb-2">Drag & drop your study material here</p>
            <p className="text-sm text-slate-500">Supports PDF documents (up to 10MB)</p>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg flex items-center text-sm">
          <AlertCircle className="w-4 h-4 mr-2 flex-shrink-0" />
          {error}
        </div>
      )}

      {success && (
        <div className="mt-3 p-3 bg-green-50 border border-green-200 text-green-700 rounded-lg flex items-center text-sm">
          <CheckCircle className="w-4 h-4 mr-2 flex-shrink-0" />
          {success}
        </div>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        className="mt-4 w-full py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors shadow-sm flex justify-center items-center"
      >
        {uploading ? (
          <>
            <Loader className="w-4 h-4 mr-2 animate-spin" />
            Uploading...
          </>
        ) : (
          'Process Document'
        )}
      </button>
    </div>
  );
};

export default FileUpload;
