import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import type { KnowledgeDocument } from '../types';
import { 
  Upload, FileText, Trash2, Shield, MessageSquare, LogOut, 
  Search, CheckCircle2, AlertTriangle, FileUp, Database, HardDrive, RefreshCw 
} from 'lucide-react';

export default function Admin() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Basic frontend authentication and role check
    const userStr = localStorage.getItem('user');
    if (!userStr) {
      navigate('/login');
      return;
    }
    try {
      const user = JSON.parse(userStr);
      if (user.role !== 'admin') {
        navigate('/chat');
        return;
      }
    } catch {
      navigate('/login');
      return;
    }

    fetchDocuments();
  }, [navigate]);

  const fetchDocuments = async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get('/api/knowledge/documents');
      setDocuments(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || '获取文档列表失败');
    } finally {
      setLoading(false);
    }
  };

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
      uploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      uploadFile(e.target.files[0]);
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  const uploadFile = async (file: File) => {
    setUploading(true);
    setError('');
    setSuccess('');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      await api.post('/api/knowledge/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      setSuccess(`文件 "${file.name}" 上传并分片导入成功！`);
      fetchDocuments();
    } catch (err: any) {
      setError(err.response?.data?.detail || `上传失败: ${file.name}`);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (docId: string, filename: string) => {
    if (!confirm(`确定要从商品知识库中删除 "${filename}" 吗？该操作不可恢复！`)) {
      return;
    }
    
    setError('');
    setSuccess('');
    try {
      await api.delete(`/api/knowledge/documents/${docId}`);
      setSuccess(`文档 "${filename}" 已成功删除。`);
      fetchDocuments();
    } catch (err: any) {
      setError(err.response?.data?.detail || `删除文档失败: ${filename}`);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  const filteredDocs = documents.filter(doc => 
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden relative">
      {/* Background glowing decorations */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-sky-500/5 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[120px] pointer-events-none"></div>

      {/* Sidebar */}
      <aside className="w-64 glass-panel border-r border-white/5 flex flex-col z-10">
        <div className="p-6 border-b border-white/5 flex items-center gap-3">
          <div className="p-2 bg-gradient-to-tr from-sky-500 to-indigo-600 rounded-xl shadow-md ring-1 ring-white/10">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-sm tracking-wide">知识库后台</h2>
            <span className="text-[10px] text-sky-400 font-semibold tracking-wider uppercase">管理员控制台</span>
          </div>
        </div>

        {/* Sidebar Nav */}
        <nav className="flex-1 px-4 py-6 space-y-2">
          <button 
            disabled 
            className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl bg-sky-500/10 text-sky-300 border border-sky-500/20"
          >
            <Database className="w-4 h-4" />
            <span>知识库管理</span>
          </button>
          
          <button 
            onClick={() => navigate('/chat')}
            className="w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-xl text-slate-400 hover:bg-white/5 hover:text-slate-200 transition duration-200"
          >
            <MessageSquare className="w-4 h-4" />
            <span>知识库问答</span>
          </button>
        </nav>

        {/* User profile footer in sidebar */}
        <div className="p-4 border-t border-white/5 flex flex-col gap-2">
          <div className="flex items-center gap-3 px-2 py-1">
            <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs text-sky-400 border border-slate-700">
              AD
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold truncate">admin</p>
              <p className="text-[9px] text-slate-500">超级管理员</p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-medium text-rose-400 bg-rose-500/5 hover:bg-rose-500/10 border border-rose-500/10 hover:border-rose-500/20 rounded-lg transition duration-200"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>退出登录</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden z-10">
        {/* Header */}
        <header className="h-16 border-b border-white/5 px-8 flex items-center justify-between glass-panel">
          <h1 className="text-lg font-semibold text-slate-100 flex items-center gap-2">
            <Database className="w-5 h-5 text-sky-400" />
            <span>商品知识库文档管理</span>
          </h1>
          <div className="flex items-center gap-4">
            <div className="text-xs text-slate-400 flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 border border-white/5 rounded-full">
              <HardDrive className="w-3.5 h-3.5 text-indigo-400" />
              <span>Chroma Vector Store: <strong className="text-slate-200">{documents.length}</strong> 个文档</span>
            </div>
          </div>
        </header>

        {/* Content Container */}
        <div className="flex-1 overflow-y-auto p-8 space-y-6">
          {/* Notifications */}
          {error && (
            <div className="flex items-center gap-3 p-4 text-sm text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-2xl">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="flex items-center gap-3 p-4 text-sm text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-2xl">
              <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
              <span>{success}</span>
            </div>
          )}

          {/* Grid Layout: Drag & Drop upload (left) + Documents List (right) */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Upload Area Card */}
            <div className="glass-panel rounded-3xl p-6 border border-white/5 flex flex-col h-fit">
              <h2 className="text-sm font-semibold tracking-wide text-slate-300 mb-4 flex items-center gap-2">
                <FileUp className="w-4 h-4 text-sky-400" />
                导入新文档
              </h2>
              
              <div 
                onDragEnter={handleDrag}
                onDragOver={handleDrag}
                onDragLeave={handleDrag}
                onDrop={handleDrop}
                onClick={triggerFileInput}
                className={`border-2 border-dashed rounded-2xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-300 ${
                  dragActive 
                    ? 'border-sky-500 bg-sky-500/5' 
                    : 'border-slate-800 hover:border-slate-700 bg-slate-900/40 hover:bg-slate-900/80'
                }`}
              >
                <input 
                  ref={fileInputRef}
                  type="file" 
                  onChange={handleFileInputChange}
                  accept=".pdf,.docx,.xlsx,.txt,.md"
                  className="hidden" 
                />
                
                <div className={`p-4 rounded-full bg-slate-800 border border-slate-700/60 mb-4 text-sky-400 transition-transform ${
                  uploading ? 'animate-bounce' : ''
                }`}>
                  <Upload className="w-6 h-6" />
                </div>
                
                <p className="text-xs font-semibold text-slate-300">
                  {uploading ? '正在解析并生成向量...' : '拖拽文件到此处，或点击上传'}
                </p>
                <p className="text-[10px] text-slate-500 mt-2">
                  支持 PDF, Word, Excel, TXT, Markdown 格式
                </p>
              </div>

              {uploading && (
                <div className="mt-4 space-y-2">
                  <div className="flex justify-between text-[10px] font-semibold text-sky-400">
                    <span>处理中</span>
                    <span className="flex items-center gap-1">
                      <RefreshCw className="w-3 h-3 animate-spin" />
                      文本分片中...
                    </span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-900 rounded-full overflow-hidden">
                    <div className="h-full w-2/3 bg-sky-500 rounded-full animate-pulse"></div>
                  </div>
                </div>
              )}
            </div>

            {/* Documents List Card (occupies 2 cols) */}
            <div className="lg:col-span-2 glass-panel rounded-3xl p-6 border border-white/5 flex flex-col min-h-[400px]">
              {/* List header and search */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                <h2 className="text-sm font-semibold tracking-wide text-slate-300 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-indigo-400" />
                  已导入的商品文件
                </h2>
                
                <div className="relative w-full sm:w-64">
                  <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 text-xs rounded-xl text-slate-200 glass-input focus:outline-none placeholder-slate-500"
                    placeholder="搜索文件名称..."
                  />
                </div>
              </div>

              {/* Table */}
              <div className="flex-1 overflow-x-auto">
                {loading ? (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-400 gap-3">
                    <RefreshCw className="w-6 h-6 animate-spin text-sky-400" />
                    <span className="text-xs">正在加载知识库列表...</span>
                  </div>
                ) : filteredDocs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-20 text-slate-500 text-center gap-3">
                    <FileText className="w-8 h-8 text-slate-700" />
                    <div>
                      <p className="text-xs font-semibold">暂无文档数据</p>
                      <p className="text-[10px] text-slate-600 mt-1">
                        {searchQuery ? '未找到符合条件的搜索结果' : '上传商品信息说明文件，即可在问答系统中引用'}
                      </p>
                    </div>
                  </div>
                ) : (
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-white/5 text-slate-400 font-semibold">
                        <th className="pb-3 pr-4">文件名</th>
                        <th className="pb-3 px-4 w-24">文件大小</th>
                        <th className="pb-3 px-4 w-24">分块数量</th>
                        <th className="pb-3 px-4 w-36">导入时间</th>
                        <th className="pb-3 pl-4 text-right w-16">操作</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {filteredDocs.map((doc) => (
                        <tr key={doc.id} className="hover:bg-white/5 transition duration-150">
                          <td className="py-4 pr-4 font-medium text-slate-200 flex items-center gap-2 truncate max-w-[240px]">
                            <FileText className="w-4 h-4 text-sky-400 flex-shrink-0" />
                            <span title={doc.filename}>{doc.filename}</span>
                          </td>
                          <td className="py-4 px-4 text-slate-400 font-mono">{doc.file_size}</td>
                          <td className="py-4 px-4 text-slate-300">
                            <span className="px-2 py-0.5 bg-slate-900 border border-white/5 rounded text-[10px]">
                              {doc.chunk_count} Chunks
                            </span>
                          </td>
                          <td className="py-4 px-4 text-slate-400">
                            {new Date(doc.uploaded_at).toLocaleString()}
                          </td>
                          <td className="py-4 pl-4 text-right">
                            <button
                              onClick={() => handleDelete(doc.id, doc.filename)}
                              className="p-2 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 rounded-lg transition duration-200"
                              title="删除文档"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
