import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, Sparkles } from 'lucide-react';
import { api } from '../api';
import { t } from '../i18n';

interface Lecture {
  id: number;
  title: string;
  creator_id: number;
  status: 'init' | 'recording' | 'summarizing' | 'done';
  created_at: string;
  ended_at: string | null;
}

export function LectureDetailView() {
  const { id } = useParams<{ id: string }>();
  const [lecture, setLecture] = useState<Lecture | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('transcript');
  const navigate = useNavigate();

  useEffect(() => {
    if (!id) return;

    (async () => {
      setLoading(true);
      setError('');
      const { data, error: apiError, status } = await api.get<Lecture>(`/api/lectures/${id}`);

      setLoading(false);

      if (apiError || !data) {
        if (status === 404) setError(t('error_not_found'));
        else if (status === 403) setError(t('error_forbidden'));
        else setError(t('error_network'));
        return;
      }

      setLecture(data);
    })();
  }, [id]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-50">
        <p className="text-slate-500">{t('loading')}</p>
      </div>
    );
  }

  if (error || !lecture) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50">
        <p className="text-red-500 mb-4">{error}</p>
        <button
          onClick={() => navigate('/dashboard')}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          {t('my_lectures')}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      <header className="bg-white shadow-sm sticky top-0 z-10">
        <div className="flex items-center p-4">
          <button
            onClick={() => navigate('/dashboard')}
            className="p-2 -ml-2 text-slate-500 hover:bg-slate-100 rounded-full"
          >
            <ChevronLeft size={24} />
          </button>

          <div className="ml-2 flex-1 min-w-0">
            <h1 className="font-bold text-slate-800 truncate">{lecture.title}</h1>
            <p className="text-xs text-slate-500">{formatDate(lecture.created_at)}</p>
          </div>
        </div>

        <div className="flex px-4 space-x-6 border-b border-slate-100">
          <button
            onClick={() => setActiveTab('transcript')}
            className={`pb-3 text-sm font-medium transition border-b-2 ${
              activeTab === 'transcript'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-slate-500'
            }`}
          >
            {t('transcript')}
          </button>
          <button
            onClick={() => setActiveTab('summary')}
            className={`pb-3 text-sm font-medium transition border-b-2 flex items-center ${
              activeTab === 'summary'
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-slate-500'
            }`}
          >
            <Sparkles size={14} className="mr-1" />
            {t('ai_summary')}
          </button>
          <button
            onClick={() => setActiveTab('export')}
            className={`pb-3 text-sm font-medium transition border-b-2 ${
              activeTab === 'export'
                ? 'border-slate-800 text-slate-800'
                : 'border-transparent text-slate-500'
            }`}
          >
            {t('export')}
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-4 md:p-8 max-w-4xl mx-auto w-full bg-white md:bg-transparent md:mt-4">
        <div className="md:bg-white md:p-8 md:rounded-xl md:shadow-sm">
          {activeTab === 'transcript' && (
            <p className="text-slate-500 text-center py-12">
              逐字稿功能将在 M1 阶段实现
            </p>
          )}

          {activeTab === 'summary' && (
            <p className="text-slate-500 text-center py-12">
              AI 总结功能将在 M3 阶段实现
            </p>
          )}

          {activeTab === 'export' && (
            <p className="text-slate-500 text-center py-12">
              导出功能将在 M3 阶段实现
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
