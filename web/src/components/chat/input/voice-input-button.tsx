'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Tooltip, message } from 'antd';
import { AudioOutlined, LoadingOutlined } from '@ant-design/icons';
import classNames from 'classnames';
import { apiInterceptors } from '@/client/api/tools/interceptors';
import { postVoiceTranscribe } from '@/client/api/request';

interface VoiceInputButtonProps {
  /** 识别出的文本回调(父组件负责拼接进输入框) */
  onTranscript: (text: string) => void;
  disabled?: boolean;
  /** 识别语言,默认中文 */
  lang?: string;
}

/** 发送按钮旁的语音输入:MediaRecorder 录音 → 后端 ASR 转文字,识别中红色脉冲动画 */
export function VoiceInputButton({ onTranscript, disabled, lang = 'zh-CN' }: VoiceInputButtonProps) {
  const [recording, setRecording] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [supported, setSupported] = useState(true);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const onTranscriptRef = useRef(onTranscript);
  onTranscriptRef.current = onTranscript;

  const cleanup = useCallback(() => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state !== 'inactive') {
      try {
        rec.stop();
      } catch {
        /** noop */
      }
    }
    try {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    } catch {
      /** noop */
    }
    mediaRecorderRef.current = null;
    streamRef.current = null;
    chunksRef.current = [];
  }, []);

  useEffect(() => {
    if (typeof MediaRecorder === 'undefined' || !navigator.mediaDevices?.getUserMedia) setSupported(false);
    return () => cleanup();
  }, [cleanup]);

  const stop = () => {
    const rec = mediaRecorderRef.current;
    if (rec && rec.state !== 'inactive') rec.stop();
  };

  const start = async () => {
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      message.warning('无法访问麦克风，请允许麦克风权限');
      return;
    }
    const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4'].find((t) =>
      MediaRecorder.isTypeSupported(t),
    );
    const rec = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    streamRef.current = stream;
    chunksRef.current = [];
    rec.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
    };
    rec.onerror = () => {
      cleanup();
      setRecording(false);
      message.warning('录音出错，请重试');
    };
    rec.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: rec.mimeType || 'audio/webm' });
      cleanup();
      setRecording(false);
      if (!blob.size) return;
      setSubmitting(true);
      try {
        const [err, res] = await apiInterceptors(postVoiceTranscribe(blob, lang));
        if (err) {
          message.warning((err as Error)?.message || '语音转写失败');
        } else if (res?.text) {
          onTranscriptRef.current(res.text);
        } else {
          message.warning('未识别到内容，请重试');
        }
      } finally {
        setSubmitting(false);
      }
    };
    mediaRecorderRef.current = rec;
    rec.start();
    setRecording(true);
  };

  if (!supported) return null;

  return (
    <Tooltip title={recording ? '停止语音输入' : '语音输入'} placement="top">
      <button
        type="button"
        disabled={disabled || submitting}
        onClick={() => (recording ? stop() : start())}
        className={classNames(
          'h-8 w-8 rounded-full flex items-center justify-center border transition-all flex-shrink-0 disabled:opacity-40 disabled:cursor-not-allowed',
          recording
            ? 'border-red-300 dark:border-red-600 text-red-500 bg-red-50 dark:bg-red-900/20 animate-pulse'
            : 'border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:text-indigo-500 hover:border-indigo-300 dark:hover:border-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20',
        )}
      >
        {submitting ? <LoadingOutlined className="text-sm" spin /> : recording ? <LoadingOutlined className="text-sm" spin /> : <AudioOutlined className="text-sm" />}
      </button>
    </Tooltip>
  );
}
