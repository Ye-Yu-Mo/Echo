import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic } from 'lucide-react';
import { api } from '../api';
import { t } from '../i18n';
import { LanguageSwitcher } from '../components/LanguageSwitcher';

export function LoginView() {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!username || !password) {
      setError(t('error_auth'));
      return;
    }

    setLoading(true);
    const { data, error: apiError, status } = await api.post<{
      token: string;
      user_id: number;
      username: string;
      role: string;
    }>('/api/auth/login', { username, password });

    setLoading(false);

    if (apiError || !data) {
      setError(status === 401 ? t('error_auth') : t('error_network'));
      return;
    }

    localStorage.setItem('echo_token', data.token);
    localStorage.setItem(
      'echo_user',
      JSON.stringify({ id: data.user_id, username: data.username, role: data.role })
    );

    navigate('/dashboard');
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 p-4 relative">
      <div className="absolute top-4 right-4">
        <LanguageSwitcher />
      </div>

      <div className="bg-white p-8 rounded-2xl shadow-xl w-full max-w-sm">
        <div className="flex justify-center mb-6">
          <div className="bg-blue-600 p-3 rounded-xl">
            <Mic className="text-white w-8 h-8" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-center text-slate-800 mb-2">{t('app_name')}</h1>
        <p className="text-center text-slate-500 mb-8">{t('slogan')}</p>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('access_code')}
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              {t('password')}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
            />
          </div>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <button
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition duration-200 flex justify-center items-center"
          >
            {loading ? t('verifying') : t('enter_class')}
          </button>
        </form>
      </div>
    </div>
  );
}
