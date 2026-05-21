'use client';

import React, { useState, useEffect, useRef } from 'react';
import PromptBar from '@/components/PromptBar';
import ImageStudio from '@/components/ImageStudio';
import InpaintEditor from '@/components/InpaintEditor';
import { generateImage, animateImage, inpaintImage } from '@/lib/api';
import { saveHistory, loadHistory } from '@/lib/storage';
import styles from './page.module.css';

interface HistoryItem {
  id: string;
  url: string;
  prompt: string;
  type: 'image' | 'video';
}

export default function Home() {
  const [messages, setMessages] = useState<any[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [faceImage, setFaceImage] = useState<string | null>(null);
  const [baseImage, setBaseImage] = useState<string | null>(null);
  const [showInpaintEditor, setShowInpaintEditor] = useState(false);
  const [mode, setMode] = useState<'image' | 'video'>('image');

  const [studioImg, setStudioImg] = useState<string | null>(null);
  const [studioPrompt, setStudioPrompt] = useState<string>('');
  const [studioInitialTab, setStudioInitialTab] = useState<'animate' | 'scales'>('animate');
  const [showQuickActions, setShowQuickActions] = useState<HistoryItem | null>(null);

  const isInitialized = useRef(false);

  // Carregar histórico do IndexedDB na inicialização
  useEffect(() => {
    // Limpar localStorage corrompido
    try { localStorage.removeItem('grok_history'); } catch {}

    loadHistory().then((saved) => {
      if (saved && saved.length > 0) {
        setMessages(saved);
      }
      isInitialized.current = true;
    });
  }, []);

  // Salvar no IndexedDB quando messages mudam
  useEffect(() => {
    if (isInitialized.current && messages.length >= 0) {
      saveHistory(messages);
    }
  }, [messages]);

  const deleteItem = (id: string) => {
    if (!window.confirm("Tem certeza que deseja excluir esta imagem permanentemente?")) return;
    setMessages(prev => prev.filter(m => m.id !== id));
  };

  const handleSend = async (text: string) => {
    setError(null);

    // Se temos uma imagem base selecionada e o modo é vídeo, animamos ela diretamente!
    if (baseImage && mode === 'video') {
      const userMsg = {
        id: Date.now().toString(),
        role: 'user',
        content: text,
        mode,
        image: baseImage,
      };
      setMessages(prev => [userMsg, ...prev]);
      setIsProcessing(true);

      try {
        const videoData = await animateImage(baseImage, text, faceImage || undefined);
        if (videoData.status === 'error' || !videoData.video) {
          throw new Error(videoData.message || 'Animação falhou');
        }
        setMessages(prev => [{
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          type: 'video',
          prompt: text,
          mediaUrl: videoData.video.startsWith('data:') || videoData.video.startsWith('http') 
            ? videoData.video 
            : `data:video/mp4;base64,${videoData.video}`,
        }, ...prev]);
      } catch (error: any) {
        console.error('Erro na animação:', error.message);
        setError(error.message || 'Erro ao animar imagem.');
      } finally {
        setIsProcessing(false);
      }
      return;
    }

    // Fluxo padrão (sem imagem base carregada na tela inicial)
    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      mode,
    };
    setMessages(prev => [userMsg, ...prev]);
    setIsProcessing(true);

    try {
      if (mode === 'image') {
        const data = await generateImage(text, faceImage || undefined);
        if (data.status === 'error' || !data.image) {
          throw new Error(data.message || 'Geração falhou');
        }
        setMessages(prev => [{
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          type: 'image',
          prompt: text,
          mediaUrl: data.image.startsWith('data:') || data.image.startsWith('http') 
            ? data.image 
            : `data:image/webp;base64,${data.image}`,
        }, ...prev]);
      } else {
        const baseData = await generateImage(text, faceImage || undefined);
        if (baseData.status === 'error' || !baseData.image) {
          throw new Error(baseData.message || 'Geração da imagem base falhou');
        }
        const baseImgUrl = baseData.image.startsWith('data:') || baseData.image.startsWith('http') 
          ? baseData.image 
          : `data:image/webp;base64,${baseData.image}`;
        
        const videoData = await animateImage(baseImgUrl, text);
        if (videoData.status === 'error' || !videoData.video) {
          throw new Error(videoData.message || 'Animação falhou');
        }
        setMessages(prev => [{
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          type: 'video',
          prompt: text,
          mediaUrl: videoData.video.startsWith('data:') || videoData.video.startsWith('http') 
            ? videoData.video 
            : `data:video/mp4;base64,${videoData.video}`,
        }, ...prev]);
      }
    } catch (error: any) {
      console.error('Erro na geração:', error.message);
      setError(error.message || 'Erro inesperado na geração. Tente novamente.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Animar imagem base enviada diretamente do painel
  const handleAnimateBaseImage = async () => {
    if (!baseImage) return;
    
    const text = window.prompt(
      "Digite o movimento desejado para a animação:",
      "câmera se aproximando lentamente, movimentos realistas e fluidos"
    );
    
    if (text === null) return;
    const promptText = text.trim() || "cinematic motion, high quality";
    
    setError(null);
    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: `Animar foto: ${promptText}`,
      mode: 'video',
      image: baseImage,
    };
    setMessages(prev => [userMsg, ...prev]);
    setIsProcessing(true);

    try {
      const videoData = await animateImage(baseImage, promptText, faceImage || undefined);
      if (videoData.status === 'error' || !videoData.video) {
        throw new Error(videoData.message || 'Animação falhou');
      }
      setMessages(prev => [{
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        type: 'video',
        prompt: promptText,
        mediaUrl: videoData.video.startsWith('data:') || videoData.video.startsWith('http') 
          ? videoData.video 
          : `data:video/mp4;base64,${videoData.video}`,
      }, ...prev]);
    } catch (error: any) {
      console.error('Erro na animação:', error.message);
      setError(error.message || 'Erro ao animar imagem.');
    } finally {
      setIsProcessing(false);
    }
  };

  // Editar imagem base (Inpaint) a partir do painel
  const handleInpaintBaseImage = async (maskBase64: string, inpaintPrompt: string) => {
    if (!baseImage) return;
    setShowInpaintEditor(false);
    setError(null);

    const userMsg = {
      id: Date.now().toString(),
      role: 'user',
      content: `Editar roupa/área: ${inpaintPrompt}`,
      mode: 'image',
      image: baseImage,
    };
    setMessages(prev => [userMsg, ...prev]);
    setIsProcessing(true);

    try {
      const data = await inpaintImage(baseImage, maskBase64, inpaintPrompt);
      if (data.status === 'error' || !data.image) {
        throw new Error(data.message || 'Edição falhou');
      }

      const newImgUrl = data.image.startsWith('data:') || data.image.startsWith('http') 
        ? data.image 
        : `data:image/webp;base64,${data.image}`;

      setMessages(prev => [{
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        type: 'image',
        prompt: inpaintPrompt,
        mediaUrl: newImgUrl,
      }, ...prev]);

      // Atualiza a imagem base com o resultado para edições em cadeia
      setBaseImage(newImgUrl);
    } catch (error: any) {
      console.error('Erro no inpaint:', error.message);
      setError(error.message || 'Erro ao aplicar inpaint.');
    } finally {
      setIsProcessing(false);
    }
  };

  const openStudio = (item: HistoryItem, tab: 'animate' | 'scales' = 'animate') => {
    setStudioImg(item.url);
    setStudioPrompt(item.prompt);
    setStudioInitialTab(tab);
    setShowQuickActions(null);
  };

  return (
    <div className={styles.container}>
      {/* ── Sidebar ── */}
      <aside className={styles.sidebar}>
        <div className={styles.sidebarTop}>
          <div className={styles.logo}>G</div>
          <nav className={styles.nav}>
            <div className={styles.navItem}><span className="icon">🔍</span> Buscar</div>
            <div className={styles.navItem}><span className="icon">💬</span> Novo bate-papo</div>
            <div className={`${styles.navItem} ${styles.active}`}><span className="icon">🖼️</span> Imagine</div>
          </nav>
        </div>
        <div className={styles.sidebarBottom}>
          <div className={styles.userProfile}>
            <div className={styles.avatar}>R</div>
            <div className={styles.userInfo}>
              <div className={styles.userName}>RIBEIRO DA SILVA</div>
              <div className={styles.userEmail}>ribeiro.022587@gmail.com</div>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className={styles.main}>
        {isProcessing && <div className={styles.topLoadingBar} />}

        {error && (
          <div className={styles.errorBanner}>
            <span className={styles.errorIcon}>⚠️</span>
            <div className={styles.errorText}>
              <strong>Erro na geração:</strong> {error}
            </div>
            <button className={styles.errorClose} onClick={() => setError(null)}>✕</button>
          </div>
        )}

        <div className={styles.masonryGrid}>
          {isProcessing && (
            <div className={`${styles.gridItem} ${styles.skeleton}`}>
              <div className={styles.skeletonMedia}>
                <div className={styles.skeletonShimmer} />
              </div>
              <div className={styles.skeletonText}>Grok está imaginando...</div>
            </div>
          )}

          {messages.filter(m => m.role === 'assistant' && m.mediaUrl && !m.mediaUrl.includes('undefined')).map((msg) => {
            const item: HistoryItem = {
              id: msg.id,
              url: msg.mediaUrl,
              prompt: msg.prompt || '',
              type: msg.type
            };
            return (
              <div key={msg.id} className={styles.gridItem}>
                <div className={styles.imageCard}>
                  {item.type === 'image' ? (
                    <img src={item.url} alt={item.prompt} />
                  ) : (
                    <video src={item.url} controls />
                  )}
                  <div className={styles.overlay}>
                    <p className={styles.promptText}>{item.prompt}</p>
                    <div className={styles.actions}>
                      <button 
                        className={styles.editBtn} 
                        onClick={() => setShowQuickActions(item)}
                      >
                        ✦ Opções
                      </button>
                      <button 
                        className={styles.deleteBtn} 
                        onClick={(e) => { e.stopPropagation(); deleteItem(item.id); }}
                        title="Apagar"
                      >
                        🗑️
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom bar */}
        <div className={styles.bottomBarContainer}>
          {/* Painel da Imagem Base selecionada */}
          {baseImage && (
            <div className={`${styles.homePreviewCard} glass`}>
              <div className={styles.homePreviewLeft}>
                <div style={{ position: 'relative' }}>
                  <img src={baseImage} alt="Base Preview" className={styles.homePreviewThumb} />
                  {faceImage && (
                    <img src={faceImage} alt="Face overlay" className={styles.homeFaceOverlayThumb} title="FaceSwap ativo!" />
                  )}
                </div>
                <div className={styles.homePreviewInfo}>
                  <span className={styles.homePreviewTitle}>Foto Carregada</span>
                  <span className={styles.homePreviewSub}>Aplique ações diretamente na tela inicial</span>
                </div>
              </div>
              <div className={styles.homePreviewActions}>
                <button 
                  className={`${styles.actionBtn} ${styles.animateBtn}`}
                  onClick={handleAnimateBaseImage}
                  disabled={isProcessing}
                >
                  🎬 Animar Foto
                </button>
                <button 
                  className={`${styles.actionBtn} ${styles.editBtn}`}
                  onClick={() => setShowInpaintEditor(true)}
                  disabled={isProcessing}
                >
                  👕 Trocar Roupa / Inpaint
                </button>
                <button 
                  className={styles.closePreviewBtn}
                  onClick={() => setBaseImage(null)}
                >
                  ✕ Limpar
                </button>
              </div>
            </div>
          )}

          {faceImage && (
            <div className={styles.faceStatus}>
              👤 Rosto carregado para FaceSwap <button onClick={() => setFaceImage(null)}>✕</button>
            </div>
          )}
          
          <PromptBar
            onSend={handleSend}
            mode={mode}
            setMode={setMode}
            onFaceUpload={(img) => setFaceImage(img)}
            onBaseImageUpload={(img) => setBaseImage(img)}
          />
        </div>
      </main>

      {/* ── Image Studio ── */}
      {showQuickActions && (
        <div className={styles.quickPopupOverlay} onClick={() => setShowQuickActions(null)}>
          <div className={styles.quickPopup} onClick={e => e.stopPropagation()}>
            <h3>O que deseja fazer?</h3>
            <p>Selecione uma ação para esta imagem</p>
            <div className={styles.quickGrid}>
              <button onClick={() => openStudio(showQuickActions, 'animate')}>
                <span className={styles.quickIcon}>🎨</span>
                <strong>Editar Foto</strong>
                <span>Ajustes manuais e retoques</span>
              </button>
              <button onClick={() => openStudio(showQuickActions, 'animate')}>
                <span className={styles.quickIcon}>🎬</span>
                <strong>Animar Foto</strong>
                <span>Criar vídeo com movimento</span>
              </button>
              <button onClick={() => openStudio(showQuickActions, 'scales')}>
                <span className={styles.quickIcon}>📐</span>
                <strong>Escalas &amp; Redes</strong>
                <span>Mudar formato e exportar</span>
              </button>
            </div>
            <button className={styles.cancelBtn} onClick={() => setShowQuickActions(null)}>Cancelar</button>
          </div>
        </div>
      )}

      {studioImg && (
        <ImageStudio
          imageUrl={studioImg}
          prompt={studioPrompt}
          onClose={() => setStudioImg(null)}
          initialTab={studioInitialTab}
        />
      )}

      {/* ── Inpaint Editor ── */}
      {showInpaintEditor && baseImage && (
        <InpaintEditor
          imageUrl={baseImage}
          onClose={() => setShowInpaintEditor(false)}
          onGenerate={handleInpaintBaseImage}
        />
      )}
    </div>
  );
}
