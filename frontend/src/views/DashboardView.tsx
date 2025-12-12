import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Mic, Clock, Play, CheckCircle } from 'lucide-react';
import { api } from '../api';
import { t } from '../i18n';
import { LanguageSwitcher } from '../components/LanguageSwitcher';

interface Lecture {
  id: number;
  title: string;
  creator_id: number;
  status: 'init' | 'recording' | 'summarizing' | 'done';
  created_at: string;
  ended_at: string | null;
}

export function DashboardView() {
  const [lectures, setLectures] = useState<Lecture[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [creating, setCreating] = useState(false);
  const navigate = useNavigate();

  const loadLectures = async () => {
    setLoading(true);
    setError('');
    const { data, error: apiError } = await api.get<Lecture[]>('/api/lectures?limit=20&offset=0');

    setLoading(false);

    if (apiError || !data) {
      setError(apiError || t('error_network'));
      return;
    }

    setLectures(data);
  };

  useEffect(() => {
    loadLectures();
  }, []);

  const handleLogout = async () => {
    await api.post('/api/auth/logout');
    localStorage.removeItem('echo_token');
    localStorage.removeItem('echo_user');
    navigate('/login');
  };

  const handleCreateLecture = async () => {
    if (!newTitle.trim()) return;

    setCreating(true);
    const { data, error: apiError } = await api.post<Lecture>('/api/lectures', {
      title: newTitle,
    });

    setCreating(false);

    if (apiError || !data) {
      alert(apiError || t('error_network'));
      return;
    }

    setShowCreateModal(false);
    setNewTitle('');
    navigate(`/lectures/${data.id}`);
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-24">
      <header className="bg-white px-6 py-4 shadow-sm flex justify-between items-center sticky top-0 z-10">
        <div>
          <h1 className="text-xl font-bold text-slate-800">{t('my_lectures')}</h1>
          <p className="text-xs text-slate-500">{t('welcome')}</p>
        </div>
        <div className="flex items-center space-x-3">
          <LanguageSwitcher />
          <button
            onClick={handleLogout}
            className="p-2 text-slate-400 hover:text-red-500 transition rounded-full hover:bg-red-50"
          >
            <LogOut size={20} />
          </button>
        </div>
      </header>

      <div className="p-4 space-y-4 max-w-2xl mx-auto">
        {loading && <p className="text-center text-slate-500">{t('loading')}</p>}

        {error && (
          <div className="text-center">
            <p className="text-red-500 mb-2">{error}</p>
            <button onClick={loadLectures} className="text-blue-600 hover:underline">
              {t('retry')}
            </button>
          </div>
        )}

        {!loading && !error && lectures.length === 0 && (
          <p className="text-center text-slate-500">{t('empty_lectures')}</p>
        )}

        {!loading && !error && lectures.map((lecture) => (
          <div
            key={lecture.id}
            onClick={() => navigate(`/lectures/${lecture.id}`)}
            className="bg-white p-4 rounded-xl shadow-sm border border-slate-100 active:scale-95 transition-transform cursor-pointer hover:shadow-md"
          >
            <div className="flex justify-between items-start mb-2">
              <h3 className="font-semibold text-slate-800 line-clamp-2">{lecture.title}</h3>
              {lecture.status === 'done' ? (
                <CheckCircle size={16} className="text-green-500 shrink-0 ml-2" />
              ) : (
                <span className="shrink-0 ml-2 text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full whitespace-nowrap">
                  {t('processing')}
                </span>
              )}
            </div>
            <div className="flex items-center text-sm text-slate-500 space-x-4">
              <span className="flex items-center">
                <Clock size={14} className="mr-1" /> {formatDate(lecture.created_at)}
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="fixed bottom-6 right-6 md:right-1/2 md:translate-x-[320px]">
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-blue-600 text-white p-4 rounded-full shadow-lg hover:bg-blue-700 hover:scale-105 transition flex items-center shadow-blue-500/30"
        >
          <Mic size={24} />
          <span className="ml-2 font-semibold pr-2">{t('start_new')}</span>
        </button>
      </div>

      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-xl shadow-xl max-w-md w-full mx-4">
            <h2 className="text-lg font-bold mb-4">{t('start_new')}</h2>
            <input
              type="text"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder={t('edit_title')}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none mb-4"
              autoFocus
            />
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition"
              >
                {t('cancel')}
              </button>
              <button
                onClick={handleCreateLecture}
                disabled={creating || !newTitle.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition"
              >
                {creating ? t('loading') : t('save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
