'use client';

import React, { useState, useRef, useEffect } from 'react';
import styles from './PromptBar.module.css';

interface PromptBarProps {
  onSend: (text: string) => void;
  onFaceUpload: (base64: string) => void;
  onBaseImageUpload: (base64: string | null) => void;
  mode: 'image' | 'video';
  setMode: (mode: 'image' | 'video') => void;
}

export default function PromptBar({ onSend, onFaceUpload, onBaseImageUpload, mode, setMode }: PromptBarProps) {
  const [text, setText] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const faceInputRef = useRef<HTMLInputElement>(null);

  // Backend state
  const [showSettings, setShowSettings] = useState(false);
  const [backendType, setBackendType] = useState<'modal' | 'colab' | 'local'>('modal');
  const [colabUrl, setColabUrl] = useState('');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const savedType = localStorage.getItem('grok007_backend_type') as 'modal' | 'colab' | 'local';
      if (savedType) setBackendType(savedType);
      const savedUrl = localStorage.getItem('grok007_colab_url') || 'https://joylessly-sculpture-wool.ngrok-free.dev';
      setColabUrl(savedUrl);
      if (!localStorage.getItem('grok007_colab_url')) {
        localStorage.setItem('grok007_colab_url', 'https://joylessly-sculpture-wool.ngrok-free.dev');
      }
    }
  }, []);

  const handleBackendChange = (type: 'modal' | 'colab' | 'local') => {
    setBackendType(type);
    localStorage.setItem('grok007_backend_type', type);
    window.dispatchEvent(new Event('backend_changed'));
  };

  const handleColabUrlChange = (val: string) => {
    setColabUrl(val);
    localStorage.setItem('grok007_colab_url', val);
    window.dispatchEvent(new Event('backend_changed'));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (text.trim()) {
      onSend(text);
      setText('');
    }
  };

  const handleBaseImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        onBaseImageUpload(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  return (
    <div className={styles.wrapper}>
      <form className={styles.form} onSubmit={handleSubmit}>
        <div className={styles.topRow}>
          <button type="button" className={styles.plusBtn} onClick={() => fileInputRef.current?.click()} title="Upload foto de entrada">
            <span className={styles.plus}>+</span>
          </button>
          <input 
            type="text" 
            placeholder="Digite para imaginar" 
            value={text}
            onChange={(e) => setText(e.target.value)}
            className={styles.input}
          />
          <button type="submit" className={styles.sendBtn} disabled={!text.trim()}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
            </svg>
          </button>
        </div>

        <div className={styles.selectors}>
          <div 
            className={`${styles.selector} ${styles.active}`}
            onClick={() => setShowSettings(true)}
            style={{ cursor: 'pointer', background: 'rgba(110, 69, 226, 0.2)', borderColor: '#6e45e2', color: '#a78bfa' }}
          >
            🤖 {backendType === 'modal' ? 'Modal' : backendType === 'colab' ? 'Colab' : 'Local'}
          </div>
          <div 
            className={`${styles.selector} ${mode === 'image' ? styles.active : ''}`}
            onClick={() => setMode('image')}
          >
            🖼️ Imagem
          </div>
          <div 
            className={`${styles.selector} ${mode === 'video' ? styles.active : ''}`}
            onClick={() => setMode('video')}
          >
            📹 Vídeo
          </div>
          <div className={styles.selector}>📐 2:3</div>
          <div className={styles.faceToggle} onClick={() => faceInputRef.current?.click()} title="Upload foto de rosto (FaceSwap)">👤</div>
        </div>
      </form>

      <input type="file" ref={fileInputRef} hidden accept="image/*" onChange={handleBaseImageUpload} />
      <input type="file" ref={faceInputRef} hidden accept="image/*" onChange={(e) => {
        const file = e.target.files?.[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = () => onFaceUpload(reader.result as string);
          reader.readAsDataURL(file);
        }
      }} />

      {/* Settings Modal */}
      {showSettings && (
        <div className={styles.settingsOverlay} onClick={() => setShowSettings(false)}>
          <div className={styles.settingsBox} onClick={e => e.stopPropagation()}>
            <h3 className={styles.settingsTitle}>Configurar Backend</h3>
            <p className={styles.settingsSub}>Escolha onde rodar o processamento de IA.</p>
            
            <div className={styles.settingsOptions}>
              <button 
                type="button"
                className={`${styles.settingsOptBtn} ${backendType === 'modal' ? styles.settingsOptActive : ''}`}
                onClick={() => handleBackendChange('modal')}
              >
                <strong>🚀 Modal Cloud</strong>
                <span>Servidor A100/T4 dedicado na nuvem.</span>
              </button>

              <button 
                type="button"
                className={`${styles.settingsOptBtn} ${backendType === 'colab' ? styles.settingsOptActive : ''}`}
                onClick={() => handleBackendChange('colab')}
              >
                <strong>🎓 Google Colab</strong>
                <span>Conectar ao seu notebook Colab via Ngrok.</span>
              </button>

              <button 
                type="button"
                className={`${styles.settingsOptBtn} ${backendType === 'local' ? styles.settingsOptActive : ''}`}
                onClick={() => handleBackendChange('local')}
              >
                <strong>💻 Local (PC)</strong>
                <span>Servidor rodando no PC em localhost:8000.</span>
              </button>
            </div>

            {backendType === 'colab' && (
              <div className={styles.urlInputGroup}>
                <label className={styles.urlLabel}>URL do Google Colab (Ngrok):</label>
                <input 
                  type="text" 
                  className={styles.urlInput}
                  placeholder="https://xxxx.ngrok-free.app" 
                  value={colabUrl}
                  onChange={(e) => handleColabUrlChange(e.target.value)}
                />
                <p className={styles.urlHint}>Insira o endereço ngrok exposto pelo notebook.</p>
              </div>
            )}

            <button type="button" className={styles.saveBtn} onClick={() => setShowSettings(false)}>
              Confirmar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
