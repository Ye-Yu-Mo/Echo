import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeft, Sparkles, Mic, MicOff, Wifi, WifiOff, Play, Pause } from 'lucide-react';
import { api } from '../api';
import { t } from '../i18n';
import { startRecording } from '../utils/audio';
import { LectureWebSocket, SubtitleMessage } from '../utils/ws';

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
  const [isRecording, setIsRecording] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [subtitles, setSubtitles] = useState<SubtitleMessage[]>([]);
  const [wsError, setWsError] = useState('');
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const navigate = useNavigate();

  const wsRef = useRef<LectureWebSocket | null>(null);
  const stopRecordingRef = useRef<(() => void) | null>(null);
  const subtitleEndRef = useRef<HTMLDivElement>(null);

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

      // 拉取历史字幕
      const { data: utterances } = await api.get<SubtitleMessage[]>(`/api/lectures/${id}/utterances`);
      if (utterances) {
        setSubtitles(utterances);
      }
    })();
  }, [id]);

  // 自动滚动到最新字幕
  useEffect(() => {
    subtitleEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [subtitles]);

  // 清理 WebSocket 和录音
  useEffect(() => {
    return () => {
      stopRecordingRef.current?.();
      wsRef.current?.close();
    };
  }, []);

  // 回放定时器
  useEffect(() => {
    if (!isPlaying) return;

    const interval = setInterval(() => {
      setCurrentTime((prev) => {
        // 获取最后一条字幕的结束时间作为总时长
        const maxTime = subtitles.length > 0 ? subtitles[subtitles.length - 1].end_ms : 0;
        if (prev >= maxTime) {
          setIsPlaying(false);
          return 0; // 回到开头
        }
        return prev + 100; // 每100ms前进
      });
    }, 100);

    return () => clearInterval(interval);
  }, [isPlaying, subtitles]);

  const handleStartRecording = async () => {
    if (!id) return;

    try {
      setWsError('');

      // 建立 WebSocket 连接
      const token = localStorage.getItem('echo_token');
      if (!token) {
        setWsError('No authentication token');
        return;
      }

      const ws = new LectureWebSocket(
        parseInt(id),
        token,
        (subtitle) => {
          setSubtitles((prev) => [...prev, subtitle].sort((a, b) => a.seq - b.seq));
        },
        (err) => {
          setWsError(err);
          setIsConnected(false);
        },
        (info) => {
          console.log('WS Info:', info);
          setIsConnected(true);
        }
      );

      ws.connect();
      wsRef.current = ws;

      // 等待连接建立（简单延迟）
      await new Promise((resolve) => setTimeout(resolve, 1000));

      // 开始录音
      const stopFn = await startRecording((pcm) => {
        ws.sendAudioFrame(pcm);
      });

      stopRecordingRef.current = stopFn;
      setIsRecording(true);
    } catch (err) {
      console.error('Failed to start recording:', err);
      setWsError(err instanceof Error ? err.message : 'Failed to start recording');
      setIsRecording(false);
    }
  };

  const handleStopRecording = () => {
    stopRecordingRef.current?.();
    stopRecordingRef.current = null;

    wsRef.current?.close();
    wsRef.current = null;

    setIsRecording(false);
    setIsConnected(false);
  };

  const handlePlayPause = () => {
    if (subtitles.length === 0) return;
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (newTime: number) => {
    setCurrentTime(newTime);
  };

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

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

          {/* 连接状态指示器 */}
          {isRecording && (
            <div className="flex items-center text-xs text-slate-600">
              {isConnected ? (
                <>
                  <Wifi size={14} className="text-green-500 mr-1" />
                  <span className="text-green-600">Connected</span>
                </>
              ) : (
                <>
                  <WifiOff size={14} className="text-red-500 mr-1" />
                  <span className="text-red-600">Connecting...</span>
                </>
              )}
            </div>
          )}

          {/* 录音控制按钮 */}
          <button
            onClick={isRecording ? handleStopRecording : handleStartRecording}
            className={`ml-3 p-2 rounded-full transition ${
              isRecording
                ? 'bg-red-500 text-white hover:bg-red-600'
                : 'bg-blue-500 text-white hover:bg-blue-600'
            }`}
          >
            {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
          </button>
        </div>

        {/* WebSocket 错误提示 */}
        {wsError && (
          <div className="px-4 py-2 bg-red-50 text-red-600 text-sm border-b border-red-100">
            {wsError}
          </div>
        )}

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
            <div className="space-y-4">
              {subtitles.length === 0 ? (
                <p className="text-slate-500 text-center py-12">
                  {isRecording ? 'Listening...' : 'Click the microphone button to start recording'}
                </p>
              ) : (
                <>
                  {/* 回放控制条 */}
                  {!isRecording && subtitles.length > 0 && (
                    <div className="sticky top-0 z-10 bg-white p-4 rounded-lg shadow-sm border border-slate-200 mb-4">
                      <div className="flex items-center space-x-4">
                        {/* 播放/暂停按钮 */}
                        <button
                          onClick={handlePlayPause}
                          className="flex-shrink-0 p-2 bg-blue-500 text-white rounded-full hover:bg-blue-600 transition"
                        >
                          {isPlaying ? <Pause size={20} /> : <Play size={20} />}
                        </button>

                        {/* 时间显示 */}
                        <div className="flex-shrink-0 text-sm text-slate-600 font-mono">
                          {formatTime(currentTime)} / {formatTime(subtitles[subtitles.length - 1]?.end_ms || 0)}
                        </div>

                        {/* 进度条 */}
                        <div className="flex-1">
                          <input
                            type="range"
                            min="0"
                            max={subtitles[subtitles.length - 1]?.end_ms || 0}
                            value={currentTime}
                            onChange={(e) => handleSeek(Number(e.target.value))}
                            className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                            style={{
                              background: `linear-gradient(to right, #3b82f6 0%, #3b82f6 ${
                                (currentTime / (subtitles[subtitles.length - 1]?.end_ms || 1)) * 100
                              }%, #e2e8f0 ${
                                (currentTime / (subtitles[subtitles.length - 1]?.end_ms || 1)) * 100
                              }%, #e2e8f0 100%)`,
                            }}
                          />
                        </div>
                      </div>
                    </div>
                  )}

                  {/* 字幕列表 */}
                  {subtitles.map((subtitle) => {
                    const isActive = !isRecording && currentTime >= subtitle.start_ms && currentTime < subtitle.end_ms;
                    return (
                      <div
                        key={subtitle.seq}
                        className={`flex space-x-3 p-4 rounded-lg transition ${
                          isActive
                            ? 'bg-blue-50 border-2 border-blue-300'
                            : 'bg-slate-50 hover:bg-slate-100 border-2 border-transparent'
                        }`}
                      >
                        <div className="flex-shrink-0 w-12 text-xs text-slate-500 font-mono pt-1">
                          #{subtitle.seq}
                        </div>
                        <div className="flex-1 space-y-2">
                          <p className={`leading-relaxed ${isActive ? 'text-blue-900 font-medium' : 'text-slate-800'}`}>
                            {subtitle.text_en}
                          </p>
                          {subtitle.text_zh && (
                            <p className={`leading-relaxed text-sm ${isActive ? 'text-blue-700' : 'text-slate-600'}`}>
                              {subtitle.text_zh}
                            </p>
                          )}
                          <p className="text-xs text-slate-400">
                            {Math.floor(subtitle.start_ms / 1000)}s - {Math.floor(subtitle.end_ms / 1000)}s
                          </p>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={subtitleEndRef} />
                </>
              )}
            </div>
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
