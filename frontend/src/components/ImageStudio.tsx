'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import styles from './ImageStudio.module.css';
import { animateImage, testUpload, refinePrompt } from '@/lib/api';

/* ─────────────────────────────────────────────────────────────
   Motion presets
───────────────────────────────────────────────────────────── */

/* ─────────────────────────────────────────────────────────────
   Social Media Presets
───────────────────────────────────────────────────────────── */
const SOCIAL_PRESETS = [
  { category: '📸 Instagram', formats: [
    { name: 'Post Quadrado',    w: 1080, h: 1080, ratio: '1:1'    },
    { name: 'Post Retrato',     w: 1080, h: 1350, ratio: '4:5'    },
    { name: 'Stories / Reels', w: 1080, h: 1920, ratio: '9:16'   },
    { name: 'Post Paisagem',   w: 1080, h:  608, ratio: '1.91:1' },
  ]},
  { category: '📘 Facebook', formats: [
    { name: 'Post Feed',    w: 1200, h:  630, ratio: '1.91:1' },
    { name: 'Stories',      w: 1080, h: 1920, ratio: '9:16'   },
    { name: 'Capa',         w:  851, h:  315, ratio: '2.7:1'  },
    { name: 'Foto Perfil',  w:  170, h:  170, ratio: '1:1'    },
    { name: 'Evento Capa',  w: 1920, h: 1005, ratio: '~1.9:1' },
  ]},
  { category: '🐦 Twitter / X', formats: [
    { name: 'Post Paisagem', w: 1600, h:  900, ratio: '16:9' },
    { name: 'Post Quadrado', w: 1200, h: 1200, ratio: '1:1'  },
    { name: 'Capa',          w: 1500, h:  500, ratio: '3:1'  },
    { name: 'Foto Perfil',   w:  400, h:  400, ratio: '1:1'  },
  ]},
  { category: '▶️ YouTube', formats: [
    { name: 'Thumbnail',    w: 1280, h:  720, ratio: '16:9' },
    { name: 'Banner Canal', w: 2560, h: 1440, ratio: '16:9' },
    { name: 'Shorts Cover', w: 1080, h: 1920, ratio: '9:16' },
  ]},
  { category: '💼 LinkedIn', formats: [
    { name: 'Post Feed',    w: 1200, h:  627, ratio: '1.91:1' },
    { name: 'Stories',      w: 1080, h: 1920, ratio: '9:16'   },
    { name: 'Capa Perfil',  w: 1584, h:  396, ratio: '4:1'    },
    { name: 'Foto Perfil',  w:  400, h:  400, ratio: '1:1'    },
  ]},
  { category: '🎵 TikTok', formats: [
    { name: 'Vídeo / Feed', w: 1080, h: 1920, ratio: '9:16' },
    { name: 'Capa',         w: 1080, h: 1080, ratio: '1:1'  },
  ]},
  { category: '📌 Pinterest', formats: [
    { name: 'Pin Padrão',   w: 1000, h: 1500, ratio: '2:3'   },
    { name: 'Pin Quadrado', w: 1000, h: 1000, ratio: '1:1'   },
    { name: 'Pin Longo',    w: 1000, h: 2100, ratio: '1:2.1' },
  ]},
  { category: '👻 Snapchat', formats: [
    { name: 'Snap / Story', w: 1080, h: 1920, ratio: '9:16' },
  ]},
  { category: '🎮 Twitch', formats: [
    { name: 'Panel Banner',   w:  320, h:  160, ratio: '2:1'  },
    { name: 'Offline Screen', w: 1920, h: 1080, ratio: '16:9' },
    { name: 'Profile Banner', w: 1200, h:  380, ratio: '~3:1' },
  ]},
  { category: '📱 WhatsApp', formats: [
    { name: 'Status',      w: 1080, h: 1920, ratio: '9:16' },
    { name: 'Foto Perfil', w:  500, h:  500, ratio: '1:1'  },
  ]},
  { category: '🖨️ Impressão', formats: [
    { name: 'A4 Retrato',    w: 2480, h: 3508, ratio: 'A4'  },
    { name: 'A4 Paisagem',   w: 3508, h: 2480, ratio: 'A4'  },
    { name: '4×6" (10×15)', w: 1800, h: 1200, ratio: '3:2' },
    { name: '8×10" (20×25)',w: 2400, h: 3000, ratio: '4:5' },
  ]},
];

/* ─────────────────────────────────────────────────────────────
   Types
───────────────────────────────────────────────────────────── */
type StudioTab = 'animate' | 'scales';
interface Format { name: string; w: number; h: number; ratio: string }

interface ImageStudioProps {
  imageUrl: string;
  prompt: string;
  onClose: () => void;
  initialTab?: 'animate' | 'scales';
}

/* helper: File → base64 data url */
function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

/* ─────────────────────────────────────────────────────────────
   Component
───────────────────────────────────────────────────────────── */
export default function ImageStudio({ imageUrl, prompt, onClose, initialTab = 'animate' }: ImageStudioProps) {
  const [activeTab, setActiveTab] = useState<StudioTab>(initialTab);

  /* ── Animate state ── */
  const [motionPrompt, setMotionPrompt]   = useState('');
  const [uploadedImg, setUploadedImg]     = useState<string | null>(null);  // custom image to animate
  const [faceImg, setFaceImg]             = useState<string | null>(null);  // face for swap
  const [videoUrl, setVideoUrl]           = useState('');
  const [animating, setAnimating]         = useState(false);
  const [animError, setAnimError]         = useState('');
  const [uploadStatus, setUploadStatus]   = useState<'idle'|'testing'|'ok'|'fail'>('idle');
  const [uploadMsg, setUploadMsg]         = useState('');
  const [refining, setRefining]           = useState(false);
  const [brainRefinedPrompt, setBrainRefinedPrompt] = useState('');
  const [serverLogs, setServerLogs]       = useState<string[]>([]);
  const [resolution, setResolution]       = useState('704x480');
  const [motionIntensity, setMotionIntensity] = useState<string>('normal');
  const [progress, setProgress]           = useState(0);
  const [elapsed, setElapsed]             = useState(0);

  useEffect(() => {
    let timer: any;
    if (animating) {
      const start = Date.now();
      timer = setInterval(() => {
        setElapsed(Math.floor((Date.now() - start) / 1000));
      }, 1000);
    } else {
      setElapsed(0);
      setProgress(0);
    }
    return () => clearInterval(timer);
  }, [animating]);

  useEffect(() => {
    // Parse progress from logs: "📊 Progresso: 25% (Processando frames...)"
    const lastProgressLog = [...serverLogs].reverse().find(l => l.includes('📊 Progresso:'));
    if (lastProgressLog) {
      const match = lastProgressLog.match(/(\d+)%/);
      if (match) setProgress(parseInt(match[1]));
    }
  }, [serverLogs]);

  /* ── Scales state ── */
  const [selected, setSelected] = useState<Format | null>(null);

  const imgFileRef  = useRef<HTMLInputElement>(null);
  const faceFileRef = useRef<HTMLInputElement>(null);

  const activeImage = uploadedImg ?? imageUrl;

  /* ── Test upload on mount ── */
  const checkBackend = useCallback(async () => {
    setUploadStatus('testing');
    setUploadMsg('');
    const { ok, message } = await testUpload();
    setUploadStatus(ok ? 'ok' : 'fail');
    setUploadMsg(message);
  }, []);

  useEffect(() => { checkBackend(); }, [checkBackend]);

  /* ── Handle custom image upload ── */
  const handleImgUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const b64 = await fileToBase64(file);
    setUploadedImg(b64);
    setVideoUrl('');
  };

  /* ── Handle face upload ── */
  const handleFaceUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const b64 = await fileToBase64(file);
    setFaceImg(b64);
  };


  /* ── Generate animation ── */
  /* ── Generate animation ── */
  const handleAnimate = async () => {
    setAnimating(true); setAnimError(''); setVideoUrl('');
    setBrainRefinedPrompt('');
    setServerLogs([]); // reseta os logs
    const [w, h] = resolution.split('x').map(Number);
    try {
      const data = await animateImage(
        activeImage, 
        motionPrompt, 
        faceImg ?? undefined,
        (logs) => setServerLogs(logs),
        w,
        h,
        motionIntensity
      );
      if (data.status === 'error') throw new Error(data.message);
      
      // Checar se data.video já vem com prefixo
      const vidData = data.video.startsWith('data:') ? data.video : `data:video/mp4;base64,${data.video}`;
      setVideoUrl(vidData);
    } catch (e: any) {
      setAnimError(e.message ?? 'Erro ao animar. Tente novamente.');
    } finally {
      setAnimating(false);
      setRefining(false);
    }
  };

  /* ── Export scaled ── */
  const handleExport = useCallback(() => {
    if (!selected) return;
    const { w, h, name } = selected;
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = activeImage;
    img.onload = () => {
      const canvas = document.createElement('canvas');
      canvas.width = w; canvas.height = h;
      const ctx = canvas.getContext('2d')!;
      const iA = img.width / img.height;
      const tA = w / h;
      let sx = 0, sy = 0, sw = img.width, sh = img.height;
      if (iA > tA) { sw = img.height * tA; sx = (img.width - sw) / 2; }
      else          { sh = img.width  / tA; sy = (img.height - sh) / 2; }
      ctx.drawImage(img, sx, sy, sw, sh, 0, 0, w, h);
      canvas.toBlob(blob => {
        if (!blob) return;
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `grok007_${name.replace(/[\s/]/g,'_')}_${w}x${h}.png`;
        a.click(); URL.revokeObjectURL(url);
      }, 'image/png');
    };
  }, [activeImage, selected]);

  return (
    <div className={styles.overlay} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className={styles.studio}>

        {/* ── Header ── */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <span className={styles.headerIcon}>✦</span>
            <span className={styles.headerTitle}>Image Studio</span>

            {/* Upload status badge */}
            <div className={`${styles.uploadBadge} ${styles[`badge_${uploadStatus}`]}`}
              title={uploadStatus === 'fail' ? 'O Modal pode estar dormindo (cold start). Clique em Retry ou aguarde 30s.' : uploadMsg}
            >
              {uploadStatus === 'testing' && <span className={styles.badgeSpinner}/>}
              {uploadStatus === 'ok'   && '✅'}
              {uploadStatus === 'fail' && '⚠️'}
              {uploadStatus === 'idle' && '⏳'}
              <span>
                {uploadStatus === 'testing' && 'Verificando backend...'}
                {uploadStatus === 'ok'      && 'Backend online'}
                {uploadStatus === 'fail'    && 'Backend offline'}
                {uploadStatus === 'idle'    && 'Aguardando...'}
              </span>
              {uploadStatus === 'fail' && (
                <button
                  className={styles.retryBtn}
                  onClick={checkBackend}
                  title="Tentar novamente (Modal demora ~30s para acordar)"
                >
                  🔄 Retry
                </button>
              )}
            </div>

            <div className={styles.tabs}>
              <button
                id="tab-animate"
                className={`${styles.tab} ${activeTab === 'animate' ? styles.tabActive : ''}`}
                onClick={() => setActiveTab('animate')}
              >🎬 Animar</button>
              <button
                id="tab-scales"
                className={`${styles.tab} ${activeTab === 'scales' ? styles.tabActive : ''}`}
                onClick={() => setActiveTab('scales')}
              >📐 Escalas &amp; Redes</button>
            </div>
          </div>
          <button id="studio-close" className={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        {/* ── Body ── */}
        <div className={styles.body}>

          {/* Left preview */}
          <div className={styles.preview}>
            <p className={styles.previewLabel}>Imagem Ativa</p>
            <img src={activeImage} alt="Preview" className={styles.previewImg} />
            {uploadedImg && (
              <button className={styles.resetImgBtn} onClick={() => { setUploadedImg(null); setVideoUrl(''); }}>
                ↩ Usar original
              </button>
            )}

            {/* Upload custom photo */}
            <div className={styles.uploadSection}>
              <p className={styles.uploadLabel}>📤 Sua foto</p>
              <button
                id="btn-upload-img"
                className={styles.uploadBtn}
                onClick={() => imgFileRef.current?.click()}
              >
                {uploadedImg ? '🔄 Trocar foto' : '📁 Upload foto'}
              </button>
              <input
                ref={imgFileRef}
                type="file"
                accept="image/*"
                style={{ display: 'none' }}
                onChange={handleImgUpload}
              />
            </div>

            {/* FaceSwap section */}
            <div className={styles.uploadSection}>
              <p className={styles.uploadLabel}>👤 FaceSwap</p>
              {faceImg && (
                <img src={faceImg} alt="Face" className={styles.faceThumb} />
              )}
              <button
                id="btn-upload-face"
                className={`${styles.uploadBtn} ${faceImg ? styles.uploadBtnActive : ''}`}
                onClick={() => faceFileRef.current?.click()}
              >
                {faceImg ? '✅ Rosto carregado' : '🤳 Upload rosto'}
              </button>
              {faceImg && (
                <button className={styles.clearFaceBtn} onClick={() => setFaceImg(null)}>
                  ✕ Remover rosto
                </button>
              )}
              <input
                ref={faceFileRef}
                type="file"
                accept="image/*"
                style={{ display: 'none' }}
                onChange={handleFaceUpload}
              />
            </div>

            <p className={styles.previewPrompt} title={prompt}>{prompt}</p>
          </div>

          {/* ── Right panel ── */}
          <div className={styles.panel}>

            {/* ══ ANIMATE TAB ══ */}
            {activeTab === 'animate' && (
              <div className={styles.panelContent}>
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Animar Foto</h2>
                  <p className={styles.panelSub}>Digite o movimento desejado e gere o vídeo instantaneamente.</p>
                </div>

                {/* Prompt input */}
                <div className={styles.promptWrap}>
                  <textarea
                    id="motion-prompt"
                    className={styles.promptInput}
                    placeholder="Descreva o movimento... ex: gato come o peixe e pula feliz"
                    value={motionPrompt}
                    onChange={e => setMotionPrompt(e.target.value)}
                    rows={2}
                  />
                  {motionPrompt && (
                    <button className={styles.clearPromptBtn} onClick={() => setMotionPrompt('')}>✕</button>
                  )}
                </div>

                <div style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center' }}>
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <label style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>Resolução:</label>
                    <select 
                      value={resolution} 
                      onChange={(e) => setResolution(e.target.value)}
                      style={{ background: '#222', color: '#fff', border: '1px solid #444', borderRadius: '4px', fontSize: '12px', padding: '4px 8px', outline: 'none' }}
                    >
                      <option value="512x320">512x320 (Ultra Rápido)</option>
                      <option value="704x480">704x480 (Padrão LTX)</option>
                      <option value="896x512">896x512 (Widescreen High)</option>
                    </select>
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    <label style={{ fontSize: '11px', color: 'rgba(255,255,255,0.5)', textTransform: 'uppercase' }}>Força do Movimento:</label>
                    <select 
                      value={motionIntensity} 
                      onChange={(e) => setMotionIntensity(e.target.value)}
                      style={{ background: '#222', color: '#fff', border: '1px solid #444', borderRadius: '4px', fontSize: '12px', padding: '4px 8px', outline: 'none' }}
                    >
                      <option value="low">Sutil (Leve / Panning)</option>
                      <option value="normal">Padrão (Físico Realista)</option>
                      <option value="high">Intensa (Ação Dinâmica)</option>
                      <option value="extreme">Extrema (Movimento Explosivo 🔥)</option>
                    </select>
                  </div>
                </div>


                {/* Animate action + result */}
                <div className={styles.animateRow}>
                  {/* Left: image */}
                  <div className={styles.animateSide}>
                    <p className={styles.animateSideLabel}>Entrada</p>
                    <img src={activeImage} alt="entrada" className={styles.animateThumb} />
                    {faceImg && (
                      <div className={styles.faceOverlay}>
                        <img src={faceImg} alt="face" className={styles.faceOverlayImg} />
                        <span>FaceSwap ON</span>
                      </div>
                    )}
                  </div>

                  <div className={styles.animateArrow}>→</div>

                  {/* Right: result */}
                  <div className={styles.animateSide}>
                    <p className={styles.animateSideLabel}>Vídeo gerado</p>
                    <div className={styles.animateResultBox}>
                      {!animating && !videoUrl && !animError && (
                        <div className={styles.animateEmpty}>
                          <span className={styles.animatePlayIcon}>▶</span>
                          <span>Aguardando geração</span>
                        </div>
                      )}
                      {animating && (
                        <div className={styles.animateEmpty}>
                          <div className={styles.animateSpinner} />
                          <span>
                            {refining ? '🧠 Cérebro ativado: Refinando prompt...' : '👁️ Analisando imagem e gerando vídeo...'}
                          </span>
                          {brainRefinedPrompt && !refining && (
                            <p className={styles.brainPromptHint}>
                              <strong>🧠 Brain AI:</strong> {brainRefinedPrompt}
                            </p>
                          )}
                        </div>
                      )}
                      {animError && !animating && (
                        <div className={styles.animateEmpty} style={{ color: '#ff6b6b', textAlign: 'center', padding: '12px' }}>
                          ❌ {animError}
                        </div>
                      )}
                      {videoUrl && !animating && (
                        <video src={videoUrl} autoPlay loop muted playsInline className={styles.animateVideo} />
                      )}
                    </div>
                  </div>
                </div>
                
                {/* PROGRESS AND LOGS */}
                {animating && (
                  <div style={{ marginTop: '16px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px', color: '#aaa' }}>
                      <span>Tempo Decorrido: {elapsed}s</span>
                      {progress > 0 && <span>ETA: ~{Math.round((elapsed / progress) * (100 - progress))}s</span>}
                    </div>
                    <div style={{ height: '8px', background: '#222', borderRadius: '4px', overflow: 'hidden', border: '1px solid #333' }}>
                      <div style={{ height: '100%', width: `${progress}%`, background: 'linear-gradient(90deg, #6e45e2, #88d3ce)', transition: 'width 0.5s ease' }} />
                    </div>
                  </div>
                )}

                {serverLogs.length > 0 && !videoUrl && (
                  <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(0,0,0,0.4)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)', maxHeight: '150px', overflowY: 'auto' }}>
                    <h4 style={{ fontSize: '11px', fontWeight: 'bold', color: 'rgba(255,255,255,0.5)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '1px' }}>
                      Logs do Servidor (Tempo Real)
                    </h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {serverLogs.map((log, idx) => (
                        <div key={idx} style={{ fontSize: '12px', color: idx === serverLogs.length - 1 ? '#fff' : 'rgba(255,255,255,0.5)', fontFamily: 'monospace' }}>
                          {log}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* CTA buttons */}
                <div className={styles.animateActions}>
                  <button
                    id="btn-animate"
                    className={styles.animateCta}
                    onClick={handleAnimate}
                    disabled={animating}
                  >
                    {animating
                      ? <><span className={styles.spinner} /> Processando...</>
                      : '🎬 Gerar Animação'}
                  </button>
                  {videoUrl && !animating && (
                    <button
                      id="btn-download-video"
                      className={styles.downloadVideoBtn}
                      onClick={() => {
                        const a = document.createElement('a');
                        a.href = videoUrl; a.download = 'grok007_animation.mp4'; a.click();
                      }}
                    >⬇ Baixar MP4</button>
                  )}
                </div>

              </div>
            )}

            {/* ══ SCALES TAB ══ */}
            {activeTab === 'scales' && (
              <div className={styles.panelContent}>
                <div className={styles.panelHeader}>
                  <h2 className={styles.panelTitle}>Escolha o Formato</h2>
                  <p className={styles.panelSub}>Selecione o tamanho e baixe a imagem recortada e centralizada.</p>
                </div>

                {selected && (
                  <div className={styles.exportBar}>
                    <span className={styles.exportBarInfo}>
                      📐 <strong>{selected.name}</strong> — {selected.w}×{selected.h}px ({selected.ratio})
                    </span>
                    <button id="btn-export" className={styles.exportBtn} onClick={handleExport}>
                      ⬇ Baixar PNG
                    </button>
                  </div>
                )}

                <div className={styles.scalesScroll}>
                  {SOCIAL_PRESETS.map(cat => (
                    <div key={cat.category} className={styles.category}>
                      <div className={styles.categoryLabel}>{cat.category}</div>
                      <div className={styles.formatRow}>
                        {cat.formats.map(fmt => {
                          const isActive = selected?.name === fmt.name && selected?.w === fmt.w;
                          const ms = 36;
                          const bw = fmt.w >= fmt.h ? ms : Math.round(ms * fmt.w / fmt.h);
                          const bh = fmt.h >= fmt.w ? ms : Math.round(ms * fmt.h / fmt.w);
                          return (
                            <button
                              key={`${fmt.name}_${fmt.w}`}
                              className={`${styles.fmtBtn} ${isActive ? styles.fmtBtnActive : ''}`}
                              onClick={() => setSelected(isActive ? null : fmt)}
                              title={`${fmt.w}×${fmt.h}px`}
                            >
                              <div className={styles.fmtViz}>
                                <div className={styles.fmtRect} style={{ width: bw, height: bh }} />
                              </div>
                              <span className={styles.fmtName}>{fmt.name}</span>
                              <span className={styles.fmtDims}>{fmt.w}×{fmt.h}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
