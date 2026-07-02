import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api, { API_BASE_URL } from '../api';
import type { ChatSession, ChatMessage, Citation } from '../types';
import { 
  MessageSquare, Plus, Trash2, Send, ShieldAlert, LogOut, 
  Settings, Key, AlertCircle, CheckCircle2, ChevronRight, 
  ChevronDown, BookOpen, ShoppingBag, X, RefreshCw 
} from 'lucide-react';

export default function Chat() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [currentUser, setCurrentUser] = useState<any>(null);
  
  // State for streaming response
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamedResponse, setStreamedResponse] = useState('');
  const [streamedSources, setStreamedSources] = useState<Citation[]>([]);
  
  // Settings & password change modal
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [settingsError, setSettingsError] = useState('');
  const [settingsSuccess, setSettingsSuccess] = useState('');
  const [settingsLoading, setSettingsLoading] = useState(false);

  // Expandable sources mapping
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    // Auth Check
    const userStr = localStorage.getItem('user');
    const token = localStorage.getItem('token');
    if (!userStr || !token) {
      navigate('/login');
      return;
    }
    try {
      const user = JSON.parse(userStr);
      setCurrentUser(user);
    } catch {
      navigate('/login');
      return;
    }

    fetchSessions();
  }, [navigate]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamedResponse]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchSessions = async (selectFirst = true) => {
    try {
      const res = await api.get('/api/chat/sessions');
      const sessionsData = res.data;
      setSessions(sessionsData);
      
      if (selectFirst && sessionsData.length > 0) {
        handleSelectSession(sessionsData[0].id);
      } else if (sessionsData.length === 0) {
        // Automatically create a session if empty
        handleNewSession();
      }
    } catch (err) {
      console.error('获取会话列表失败', err);
    }
  };

  const handleSelectSession = async (sessionId: string) => {
    if (isStreaming) {
      alert('请等待当前回答生成完毕后再切换会话。');
      return;
    }
    setActiveSessionId(sessionId);
    setStreamedResponse('');
    setStreamedSources([]);
    
    try {
      const res = await api.get(`/api/chat/sessions/${sessionId}/messages`);
      const msgList = res.data.map((msg: any) => {
        let parsed = [];
        if (msg.sources) {
          try {
            parsed = JSON.parse(msg.sources);
          } catch {
            parsed = [];
          }
        }
        return {
          ...msg,
          parsedSources: parsed
        };
      });
      setMessages(msgList);
    } catch (err) {
      console.error('获取聊天记录失败', err);
    }
  };

  const handleNewSession = async () => {
    if (isStreaming) return;
    try {
      const res = await api.post('/api/chat/sessions', { title: '新会话' });
      const newSession = res.data;
      setSessions(prev => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      setMessages([]);
      setStreamedResponse('');
      setStreamedSources([]);
    } catch (err) {
      console.error('创建会话失败', err);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (isStreaming) return;
    if (!confirm('确定删除该会话及其聊天记录吗？')) return;

    try {
      await api.delete(`/api/chat/sessions/${sessionId}`);
      const updated = sessions.filter(s => s.id !== sessionId);
      setSessions(updated);
      
      if (activeSessionId === sessionId) {
        if (updated.length > 0) {
          handleSelectSession(updated[0].id);
        } else {
          handleNewSession();
        }
      }
    } catch (err) {
      console.error('删除会话失败', err);
    }
  };

  // 处理消息发送逻辑，包括用户消息本地入栈、启动 SSE 流式请求、打字机追加以及事件结束处理
  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    // 限制在输入为空、正在流式接收、或者没有选定会话时发送
    if (!inputMessage.trim() || isStreaming || !activeSessionId) return;

    const userText = inputMessage.trim();
    setInputMessage('');
    setIsStreaming(true);
    setStreamedResponse('');
    setStreamedSources([]);

    // 1. 立即将用户输入的文本本地压入 UI 对话框列表，提升用户响应体验
    const tempUserMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      content: userText,
      sources: null,
      created_at: new Date().toISOString(),
      parsedSources: []
    };
    setMessages(prev => [...prev, tempUserMsg]);

    // 2. 构造服务器推送事件 (EventSource) 链接。由于 EventSource 在浏览器端无法直接配置自定义 Header，
    // 我们必须以 Query String 的形式将 JWT Token（ token=xxx ）传入 URL 中，以便后端校验身份。
    const token = localStorage.getItem('token');
    const sseUrl = `${API_BASE_URL}/api/chat/sessions/${activeSessionId}/stream?query=${encodeURIComponent(userText)}&token=${token}`;
    
    // 3. 初始化原生 EventSource 连接，开启服务器推送单向长连接
    const eventSource = new EventSource(sseUrl);
    eventSourceRef.current = eventSource;

    // 4. 监听从服务器推送回来的消息帧 (onmessage)
    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'sources') {
          // 接收后端检索出的商品文档引用来源元数据
          setStreamedSources(payload.sources || []);
        } else if (payload.type === 'text') {
          // 接收大模型生成的文本字块，并通过 setState 累加字符，从而在前端形成打字机动画效果
          setStreamedResponse(prev => prev + payload.content);
        } else if (payload.type === 'done') {
          // 当接收到 'done' 事件标志时，表明大模型流式生成完成，主动断开连接
          eventSource.close();
          setIsStreaming(false);
          
          // 从数据库重新拉取该会话下的所有历史消息，确保与服务端生成的主键 ID/时间戳保持一致
          handleSelectSession(activeSessionId);
          fetchSessions(false); // 刷新左侧列表标题（如果是首轮提问，会刷新标题摘要）
        } else if (payload.type === 'error') {
          // 接收到后端流中输出的错误事件，并在界面输出错误提示，断开连接
          setStreamedResponse(prev => prev + `\n[错误: ${payload.content}]`);
          eventSource.close();
          setIsStreaming(false);
        }
      } catch (err) {
        console.error('解析流式数据失败', err);
      }
    };

    // 5. 监听长连接异常中断（如断网或后端奔溃）
    eventSource.onerror = (err) => {
      console.error('SSE 连接出错', err);
      setStreamedResponse(prev => prev + '\n\n【网络连接中断，请刷新重试】');
      eventSource.close();
      setIsStreaming(false);
    };
  };

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setSettingsError('');
    setSettingsSuccess('');

    if (newPassword !== confirmPassword) {
      setSettingsError('新密码和确认密码不一致');
      return;
    }

    setSettingsLoading(true);
    try {
      await api.post('/api/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      });
      setSettingsSuccess('密码修改成功！');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setShowSettingsModal(false), 1500);
    } catch (err: any) {
      setSettingsError(err.response?.data?.detail || '修改密码失败，请检查旧密码是否正确。');
    } finally {
      setSettingsLoading(false);
    }
  };

  const toggleSourceExpand = (msgId: string) => {
    setExpandedSources(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden relative">
      {/* Background glowing decorations */}
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-sky-500/5 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-500/5 rounded-full blur-[120px] pointer-events-none"></div>

      {/* Sidebar */}
      <aside className="w-72 glass-panel border-r border-white/5 flex flex-col z-10">
        <div className="p-5 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-tr from-sky-500 to-indigo-600 rounded-xl shadow-md ring-1 ring-white/10">
              <ShoppingBag className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="font-bold text-sm tracking-wide">RAG 智能问答</h2>
              <span className="text-[10px] text-slate-400 font-medium">企业级知识库</span>
            </div>
          </div>
        </div>

        {/* Action Button: New Session */}
        <div className="p-4">
          <button
            onClick={handleNewSession}
            disabled={isStreaming}
            className="w-full py-3 px-4 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-2 transition duration-200 shadow-md shadow-sky-500/10 hover:shadow-sky-500/20 active:scale-95 disabled:opacity-50"
          >
            <Plus className="w-4 h-4" />
            <span>开启新对话</span>
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto px-3 space-y-1">
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => handleSelectSession(s.id)}
              className={`group flex items-center justify-between px-3 py-3 rounded-xl cursor-pointer transition duration-150 border ${
                activeSessionId === s.id
                  ? 'bg-sky-500/10 text-sky-300 border-sky-500/25'
                  : 'text-slate-400 hover:bg-white/5 border-transparent hover:text-slate-200'
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <MessageSquare className={`w-4 h-4 flex-shrink-0 ${activeSessionId === s.id ? 'text-sky-400' : 'text-slate-500'}`} />
                <span className="text-xs font-medium truncate pr-2">{s.title}</span>
              </div>
              <button
                onClick={(e) => handleDeleteSession(s.id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-rose-500/10 text-rose-400 hover:text-rose-300 rounded-lg transition duration-150"
                title="删除会话"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>

        {/* Footer profile & menu */}
        <div className="p-4 border-t border-white/5 flex flex-col gap-2 bg-slate-950/40">
          <div className="flex items-center justify-between px-2">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs text-sky-400 border border-slate-700">
                {currentUser?.username?.slice(0, 2).toUpperCase() || 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold truncate text-slate-200">{currentUser?.username}</p>
                <p className="text-[9px] text-sky-400/90 font-medium">
                  {currentUser?.role === 'admin' ? '系统管理员' : '普通用户'}
                </p>
              </div>
            </div>
            
            <button
              onClick={() => setShowSettingsModal(true)}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-white/5 rounded-lg transition"
              title="修改密码"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>

          <div className="grid grid-cols-2 gap-2 mt-2">
            {currentUser?.role === 'admin' && (
              <button
                onClick={() => navigate('/admin')}
                className="flex items-center justify-center gap-1.5 py-2 px-3 text-[10px] font-semibold text-sky-300 bg-sky-500/10 hover:bg-sky-500/20 border border-sky-500/20 rounded-lg transition duration-200"
              >
                <ShieldAlert className="w-3 h-3" />
                <span>后台管理</span>
              </button>
            )}
            <button
              onClick={handleLogout}
              className={`flex items-center justify-center gap-1.5 py-2 px-3 text-[10px] font-semibold text-rose-400 bg-rose-500/5 hover:bg-rose-500/10 border border-rose-500/10 rounded-lg transition duration-200 ${
                currentUser?.role !== 'admin' ? 'col-span-2' : ''
              }`}
            >
              <LogOut className="w-3 h-3" />
              <span>退出登录</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Q&A Area */}
      <main className="flex-1 flex flex-col overflow-hidden z-10">
        {/* Header */}
        <header className="h-16 border-b border-white/5 px-8 flex items-center justify-between glass-panel">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-sky-400" />
            <h1 className="text-sm font-semibold text-slate-200">
              {sessions.find(s => s.id === activeSessionId)?.title || '智能问答'}
            </h1>
          </div>
          <div className="text-[10px] text-slate-500">
            电商 RAG 商品知识库已加载完成
          </div>
        </header>

        {/* Scrollable messages container */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-6">
          {messages.length === 0 && !streamedResponse && (
            <div className="flex flex-col items-center justify-center h-full text-center max-w-lg mx-auto py-20 space-y-6">
              <div className="p-4 bg-sky-500/5 border border-sky-500/10 rounded-3xl animate-bounce">
                <ShoppingBag className="w-10 h-10 text-sky-400" />
              </div>
              <div className="space-y-2">
                <h2 className="text-lg font-bold text-slate-200">欢迎使用电商 RAG 智能问答系统！</h2>
                <p className="text-xs text-slate-400 leading-relaxed">
                  本系统支持智能匹配后台商品数据库中的规则。你可以向我询问商品规格、售后政策、尺码建议或优惠详情，我会尽量基于知识库向您作出客观真实的引用解答。
                </p>
              </div>
            </div>
          )}

          {/* Render historical messages */}
          {messages.map((msg) => (
            <div 
              key={msg.id}
              className={`flex gap-4 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {/* Avatar for Assistant */}
              {msg.sender === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center flex-shrink-0 text-white font-bold text-xs ring-1 ring-white/10">
                  AI
                </div>
              )}

              {/* Message Bubble */}
              <div className="max-w-2xl space-y-3">
                <div className={`p-4 rounded-2xl text-sm leading-relaxed ${
                  msg.sender === 'user'
                    ? 'bg-gradient-to-br from-sky-500/80 to-indigo-600/80 text-white rounded-br-none shadow-md shadow-sky-500/5'
                    : 'glass-panel rounded-bl-none border border-white/5 text-slate-200'
                }`}>
                  {/* Message body, splits paragraphs */}
                  <div className="whitespace-pre-wrap font-sans">
                    {msg.content}
                  </div>
                </div>

                {/* Sources list for assistant messages */}
                {msg.sender === 'assistant' && msg.parsedSources && msg.parsedSources.length > 0 && (
                  <div className="glass-panel border border-white/5 rounded-xl p-3 space-y-2">
                    <button 
                      onClick={() => toggleSourceExpand(msg.id)}
                      className="flex items-center justify-between w-full text-[10px] font-semibold text-sky-400 hover:text-sky-300 transition"
                    >
                      <span className="flex items-center gap-1.5">
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>引用知识库来源 ({msg.parsedSources.length})</span>
                      </span>
                      {expandedSources[msg.id] ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    </button>

                    {expandedSources[msg.id] && (
                      <div className="space-y-2.5 pt-2 border-t border-white/5 animate-slide-down">
                        {msg.parsedSources.map((source, idx) => (
                          <div key={idx} className="bg-slate-950/40 p-2.5 rounded-lg border border-white/5 text-xs">
                            <div className="flex justify-between items-center text-[10px] text-slate-400 mb-1">
                              <span className="font-semibold text-slate-300">{source.source_name}</span>
                              <span className="text-sky-400 font-semibold font-mono">相关度 {(source.score * 100).toFixed(0)}%</span>
                            </div>
                            <p className="text-slate-400 text-[11px] leading-relaxed italic bg-slate-900/50 p-2 rounded">
                              &ldquo;{source.content}&rdquo;
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Avatar for User */}
              {msg.sender === 'user' && (
                <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center flex-shrink-0 text-sky-400 font-bold text-xs border border-slate-700">
                  {currentUser?.username?.slice(0, 2).toUpperCase() || 'U'}
                </div>
              )}
            </div>
          ))}

          {/* Streaming active response */}
          {isStreaming && streamedResponse && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center flex-shrink-0 text-white font-bold text-xs ring-1 ring-white/10">
                AI
              </div>
              <div className="max-w-2xl space-y-3">
                <div className="p-4 glass-panel rounded-2xl rounded-bl-none border border-white/5 text-slate-200 text-sm leading-relaxed">
                  <div className="whitespace-pre-wrap font-sans typing-cursor">
                    {streamedResponse}
                  </div>
                </div>

                {/* Streaming sources preview */}
                {streamedSources.length > 0 && (
                  <div className="glass-panel border border-white/5 rounded-xl p-3 space-y-2">
                    <button 
                      onClick={() => toggleSourceExpand('streaming')}
                      className="flex items-center justify-between w-full text-[10px] font-semibold text-sky-400 hover:text-sky-300 transition"
                    >
                      <span className="flex items-center gap-1.5">
                        <BookOpen className="w-3.5 h-3.5" />
                        <span>已召回引用文献 ({streamedSources.length})</span>
                      </span>
                      {expandedSources['streaming'] ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                    </button>

                    {expandedSources['streaming'] && (
                      <div className="space-y-2.5 pt-2 border-t border-white/5">
                        {streamedSources.map((source, idx) => (
                          <div key={idx} className="bg-slate-950/40 p-2.5 rounded-lg border border-white/5 text-xs">
                            <div className="flex justify-between items-center text-[10px] text-slate-400 mb-1">
                              <span className="font-semibold text-slate-300">{source.source_name}</span>
                              <span className="text-sky-400 font-semibold font-mono">得分 {(source.score * 100).toFixed(0)}%</span>
                            </div>
                            <p className="text-slate-400 text-[11px] leading-relaxed italic bg-slate-900/50 p-2 rounded">
                              &ldquo;{source.content}&rdquo;
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Anchor to scroll to */}
          <div ref={messagesEndRef} />
        </div>

        {/* Input form */}
        <div className="p-4 md:p-6 border-t border-white/5 glass-panel">
          <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto flex gap-4">
            <div className="flex-1 relative">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage(e);
                  }
                }}
                rows={1}
                className="w-full pl-4 pr-12 py-3.5 rounded-2xl text-sm text-slate-200 glass-input focus:outline-none placeholder-slate-500 resize-none max-h-32 min-h-[48px]"
                placeholder={isStreaming ? "AI 正在回答中，请稍候..." : "向 AI 询问关于商品的问题... (Enter 发送, Shift+Enter 换行)"}
                disabled={isStreaming}
              />
            </div>
            
            <button
              type="submit"
              disabled={isStreaming || !inputMessage.trim() || !activeSessionId}
              className="px-5 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white rounded-2xl transition duration-200 flex items-center justify-center shadow-lg shadow-sky-500/10 hover:shadow-sky-500/25 active:scale-95 disabled:opacity-40 disabled:pointer-events-none h-[48px]"
            >
              {isStreaming ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </button>
          </form>
          <div className="text-center text-[10px] text-slate-500 mt-3">
            基于知识库生成的答案仅供参考，请以实际商品参数和官方规则为准。
          </div>
        </div>
      </main>

      {/* Settings Modal (Password Change) */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm px-4">
          <div className="glass-panel w-full max-w-md rounded-3xl p-6 relative border border-white/10 animate-fade-in shadow-2xl">
            <button
              onClick={() => {
                setShowSettingsModal(false);
                setSettingsError('');
                setSettingsSuccess('');
              }}
              className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-slate-200 rounded-lg hover:bg-white/5 transition"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-sky-500/10 rounded-xl text-sky-400 border border-sky-500/20">
                <Key className="w-5 h-5" />
              </div>
              <h2 className="text-base font-bold text-slate-200">修改登录密码</h2>
            </div>

            <form onSubmit={handlePasswordChange} className="space-y-4">
              {settingsError && (
                <div className="flex items-center gap-2 p-3 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  <span>{settingsError}</span>
                </div>
              )}

              {settingsSuccess && (
                <div className="flex items-center gap-2 p-3 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                  <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  <span>{settingsSuccess}</span>
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-2">原密码</label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl text-xs text-slate-200 glass-input focus:outline-none placeholder-slate-600"
                  placeholder="请输入旧密码"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-2">新密码</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl text-xs text-slate-200 glass-input focus:outline-none placeholder-slate-600"
                  placeholder="请输入新密码"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-2">确认新密码</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-xl text-xs text-slate-200 glass-input focus:outline-none placeholder-slate-600"
                  placeholder="请再次输入新密码"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={settingsLoading}
                className="w-full mt-2 py-3 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-xs font-semibold rounded-xl transition duration-200 flex items-center justify-center gap-2"
              >
                {settingsLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>确 认 修 改</span>
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
