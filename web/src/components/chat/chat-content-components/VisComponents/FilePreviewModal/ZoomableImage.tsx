import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import styles from './FilePreviewModal.module.css';

const MIN_SCALE = 0.1;
const MAX_SCALE = 10;
const SCALE_STEP = 1.25;

const clamp = (v: number, min: number, max: number) => Math.min(max, Math.max(min, v));

interface ZoomableImageProps {
  src: string;
  alt?: string;
  /** 图片加载失败回调（用于顺延到下一个候选 URL） */
  onError?: () => void;
}

/**
 * 图片查看器：滚轮缩放（以指针为锚点）、拖拽平移、双击切换 1:1 / 适应窗口，
 * 底部工具栏提供 缩小 / 百分比 / 放大 / 1:1 / 适应窗口。零第三方依赖。
 */
const ZoomableImage: React.FC<ZoomableImageProps> = ({ src, alt, onError }) => {
  const stageRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);

  const [ready, setReady] = useState(false);
  const [scale, setScale] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const [natural, setNatural] = useState({ w: 0, h: 0 });

  const dragStart = useRef({ px: 0, py: 0, ox: 0, oy: 0 });

  /** 让图片完整装进舞台所需的缩放比（不超过 1，小图不放大） */
  const computeFitScale = useCallback(() => {
    const stage = stageRef.current;
    if (!stage || !natural.w || !natural.h) return 1;
    const cw = stage.clientWidth - 32;
    const ch = stage.clientHeight - 32;
    if (cw <= 0 || ch <= 0) return 1;
    return Math.min(cw / natural.w, ch / natural.h, 1);
  }, [natural]);

  const fitToStage = useCallback(() => {
    setScale(computeFitScale());
    setOffset({ x: 0, y: 0 });
  }, [computeFitScale]);

  // 图片加载完成后自动适应窗口
  const handleLoad = () => {
    const img = imgRef.current;
    if (!img) return;
    setNatural({ w: img.naturalWidth, h: img.naturalHeight });
    setReady(true);
  };

  useLayoutEffect(() => {
    if (!ready) return;
    fitToStage();
    // Modal 首帧可能尚未完成布局（clientHeight 为 0），下一帧再适应一次兜底
    const timer = setTimeout(fitToStage, 0);
    return () => clearTimeout(timer);
  }, [ready, fitToStage]);

  // 窗口尺寸变化时，若当前处于"适应"状态则重新适应
  useEffect(() => {
    if (!ready) return;
    const onResize = () => fitToStage();
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [ready, fitToStage]);

  // 滚轮缩放：必须用非 passive 监听才能 preventDefault 阻止页面滚动
  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;

    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = stage.getBoundingClientRect();
      // 指针位置相对舞台中心
      const mx = e.clientX - (rect.left + rect.width / 2);
      const my = e.clientY - (rect.top + rect.height / 2);

      setScale((prev) => {
        const factor = e.deltaY < 0 ? SCALE_STEP : 1 / SCALE_STEP;
        const next = clamp(prev * factor, MIN_SCALE, MAX_SCALE);
        const ratio = next / prev;
        setOffset((o) => ({
          x: mx - (mx - o.x) * ratio,
          y: my - (my - o.y) * ratio,
        }));
        return next;
      });
    };

    stage.addEventListener('wheel', onWheel, { passive: false });
    return () => stage.removeEventListener('wheel', onWheel);
  }, [ready]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.preventDefault();
    dragStart.current = { px: e.clientX, py: e.clientY, ox: offset.x, oy: offset.y };
    setDragging(true);
  };

  useEffect(() => {
    if (!dragging) return;
    const onMove = (e: MouseEvent) => {
      setOffset({
        x: dragStart.current.ox + (e.clientX - dragStart.current.px),
        y: dragStart.current.oy + (e.clientY - dragStart.current.py),
      });
    };
    const onUp = () => setDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, [dragging]);

  const zoomBy = (factor: number) => {
    setScale((prev) => clamp(prev * factor, MIN_SCALE, MAX_SCALE));
  };

  const handleDoubleClick = () => {
    if (Math.abs(scale - 1) < 0.01) {
      setScale(2);
    } else {
      setScale(1);
      setOffset({ x: 0, y: 0 });
    }
  };

  return (
    <div className={styles.zoomWrap}>
      <div
        ref={stageRef}
        className={`${styles.zoomStage} ${dragging ? styles.zoomStageGrabbing : ''}`}
        onMouseDown={handleMouseDown}
        onDoubleClick={handleDoubleClick}
      >
        <img
          ref={imgRef}
          src={src}
          alt={alt || 'preview'}
          className={styles.zoomImage}
          draggable={false}
          onLoad={handleLoad}
          onError={onError}
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`,
            opacity: ready ? 1 : 0,
          }}
        />
      </div>

      <div className={styles.zoomToolbar} onMouseDown={(e) => e.stopPropagation()}>
        <button
          type="button"
          className={styles.zoomBtn}
          onClick={() => zoomBy(1 / SCALE_STEP)}
          disabled={scale <= MIN_SCALE}
          title="缩小"
          aria-label="缩小"
        >
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <path d="M3 8h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" fill="none" />
          </svg>
        </button>
        <span className={styles.zoomScale}>{Math.round(scale * 100)}%</span>
        <button
          type="button"
          className={styles.zoomBtn}
          onClick={() => zoomBy(SCALE_STEP)}
          disabled={scale >= MAX_SCALE}
          title="放大"
          aria-label="放大"
        >
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" fill="none" />
          </svg>
        </button>
        <span className={styles.zoomDivider} />
        <button type="button" className={styles.zoomTextBtn} onClick={() => { setScale(1); setOffset({ x: 0, y: 0 }); }} title="按原始尺寸显示">
          1:1
        </button>
        <button type="button" className={styles.zoomTextBtn} onClick={fitToStage} title="缩放至适应窗口">
          适应窗口
        </button>
      </div>
    </div>
  );
};

export default ZoomableImage;
