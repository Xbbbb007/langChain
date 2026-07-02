import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { ShoppingBag, Lock, User, AlertCircle, RefreshCw } from 'lucide-react';

export default function Login() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccessMsg('');

    if (!username.trim() || !password) {
      setError('请填写所有必填字段');
      return;
    }

    if (!isLogin && password !== confirmPassword) {
      setError('两次填写的密码不一致');
      return;
    }

    setLoading(true);
    try {
      if (isLogin) {
        // Form Data format for OAuth2 Password Flow
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await api.post('/api/auth/login', formData, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        });

        const { access_token } = response.data;
        localStorage.setItem('token', access_token);

        // Fetch User Info
        const userRes = await api.get('/api/auth/me');
        localStorage.setItem('user', JSON.stringify(userRes.data));

        // Redirect based on role
        if (userRes.data.role === 'admin') {
          navigate('/admin');
        } else {
          navigate('/chat');
        }
      } else {
        await api.post('/api/auth/register', {
          username,
          password,
        });
        setSuccessMsg('注册成功！正在跳转至登录...');
        setTimeout(() => {
          setIsLogin(true);
          setSuccessMsg('');
          setPassword('');
          setConfirmPassword('');
        }, 1500);
      }
    } catch (err: any) {
      setError(
        err.response?.data?.detail || 
        (isLogin ? '登录失败，请检查用户名或密码' : '注册失败，请稍后重试')
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center bg-slate-950 px-4">
      {/* Background glowing decorations */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-[350px] h-[350px] bg-sky-500/10 rounded-full blur-[100px] animate-glow"></div>
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-[300px] h-[300px] bg-indigo-500/10 rounded-full blur-[90px] animate-glow" style={{ animationDelay: '-2s' }}></div>

      <div className="w-full max-w-md z-10">
        {/* Logo and title */}
        <div className="flex flex-col items-center mb-8 text-center animate-fade-in">
          <div className="p-3 bg-gradient-to-tr from-sky-500 to-indigo-600 rounded-2xl shadow-lg shadow-sky-500/20 mb-4 ring-1 ring-white/10">
            <ShoppingBag className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
            电商 RAG 智能问答系统
          </h1>
          <p className="text-sm text-slate-400 mt-2">
            企业级商品知识库 & 智能客服助手
          </p>
        </div>

        {/* Card */}
        <div className="glass-panel rounded-3xl p-8 shadow-2xl relative overflow-hidden border border-white/5">
          <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-sky-500/0 via-sky-500/40 to-indigo-500/0"></div>
          
          <h2 className="text-xl font-semibold text-slate-100 mb-6">
            {isLogin ? '用户登录' : '新用户注册'}
          </h2>

          <form onSubmit={handleAuth} className="space-y-5">
            {error && (
              <div className="flex items-center gap-2 p-3.5 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {successMsg && (
              <div className="flex items-center gap-2 p-3.5 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2">用户名</label>
              <div className="relative">
                <User className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 rounded-xl text-sm text-slate-200 glass-input focus:outline-none placeholder-slate-500"
                  placeholder="请输入用户名"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-2">密码</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-400" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 rounded-xl text-sm text-slate-200 glass-input focus:outline-none placeholder-slate-500"
                  placeholder="请输入密码"
                  required
                />
              </div>
            </div>

            {!isLogin && (
              <div className="animate-slide-down">
                <label className="block text-xs font-medium text-slate-400 mb-2">确认密码</label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-3.5 w-4 h-4 text-slate-400" />
                  <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 rounded-xl text-sm text-slate-200 glass-input focus:outline-none placeholder-slate-500"
                    placeholder="请再次输入密码"
                    required={!isLogin}
                  />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 px-4 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-400 hover:to-indigo-500 text-white text-sm font-semibold rounded-xl transition duration-300 shadow-lg shadow-sky-500/15 focus:outline-none hover:-translate-y-[1px] active:translate-y-0 disabled:opacity-50 disabled:pointer-events-none flex items-center justify-center gap-2"
            >
              {loading ? (
                <RefreshCw className="w-4 h-4 animate-spin" />
              ) : null}
              {isLogin ? '登 录' : '注 册'}
            </button>
          </form>

          <div className="mt-6 text-center text-xs text-slate-400">
            {isLogin ? (
              <span>
                没有账号？{' '}
                <button
                  type="button"
                  onClick={() => {
                    setIsLogin(false);
                    setError('');
                    setPassword('');
                  }}
                  className="text-sky-400 hover:underline hover:text-sky-300 font-medium"
                >
                  立即注册
                </button>
              </span>
            ) : (
              <span>
                已有账号？{' '}
                <button
                  type="button"
                  onClick={() => {
                    setIsLogin(true);
                    setError('');
                    setPassword('');
                    setConfirmPassword('');
                  }}
                  className="text-sky-400 hover:underline hover:text-sky-300 font-medium"
                >
                  返回登录
                </button>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
