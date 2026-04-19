import { useState } from 'react';
import { API_BASE } from '../api/client';

export default function Auth({ setToken }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit() {
    if (!email.trim() || !password.trim()) {
      setError('Email and password are required');
      return;
    }

    setLoading(true);
    setError('');

    const endpoint = mode === 'login' ? '/login' : '/signup';

    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || data?.error || 'Error');
      }

      if (mode === 'login') {
        localStorage.setItem('token', data.token);
        setToken(data.token);
      } else {
        setMode('login');
      }
    } catch (e) {
      setError(e.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#060b18] px-4">
      <div className="w-full max-w-[440px] rounded-3xl border border-white/10 bg-white/5 p-8 shadow-2xl backdrop-blur-xl sm:p-10">
        <h1 className="mb-2 text-center text-3xl font-semibold text-white">
          {mode === 'login' ? 'Login' : 'Sign Up'}
        </h1>

        <p className="mb-6 text-center text-sm text-[#a7b2c1]">
          Sign in to analyze your videos
        </p>

        <input
          className="mb-3 h-[52px] w-full rounded-2xl border border-[#2b3447] bg-[#1a222f] px-4 text-base text-[#e2e8f0] placeholder:text-[#6f7a8e] focus:border-[#4d5e7e] focus:outline-none"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />

        <input
          type="password"
          className="mb-4 h-[52px] w-full rounded-2xl border border-[#2b3447] bg-[#1a222f] px-4 text-base text-[#e2e8f0] placeholder:text-[#6f7a8e] focus:border-[#4d5e7e] focus:outline-none"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />

        <button
          className="h-[52px] w-full rounded-2xl bg-gradient-to-r from-[#7c3aed] to-[#3b82f6] text-base font-semibold text-white shadow-[0_14px_34px_rgba(59,130,246,0.35)] transition hover:brightness-110 disabled:opacity-60"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Sign Up'}
        </button>

        {error && <p className="mt-3 text-center text-sm text-red-400">{error}</p>}

        <p
          className="mt-4 cursor-pointer text-center text-sm text-[#a7b2c1] hover:text-[#d2d9e4]"
          onClick={() => {
            setMode(mode === 'login' ? 'signup' : 'login');
            setError('');
          }}
        >
          {mode === 'login'
            ? "Don't have an account? Sign up"
            : 'Already have an account? Login'}
        </p>
      </div>
    </div>
  );
}
