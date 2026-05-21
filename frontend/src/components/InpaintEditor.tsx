'use client';

import React, { useRef, useState, useEffect } from 'react';
import styles from './InpaintEditor.module.css';

interface InpaintEditorProps {
  imageUrl: string;
  onClose: () => void;
  onGenerate: (maskBase64: string, prompt: string) => void;
}

export default function InpaintEditor({ imageUrl, onClose, onGenerate }: InpaintEditorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isDrawing, setIsDrawing] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [ctx, setCtx] = useState<CanvasRenderingContext2D | null>(null);

  useEffect(() => {
    if (canvasRef.current) {
      const canvas = canvasRef.current;
      const context = canvas.getContext('2d');
      if (context) {
        context.lineCap = 'round';
        context.lineJoin = 'round';
        context.strokeStyle = 'white'; // Mask is usually white on black
        context.lineWidth = 40;
        setCtx(context);
        
        // Fill with black (initially no mask)
        context.fillStyle = 'black';
        context.fillRect(0, 0, canvas.width, canvas.height);
      }
    }
  }, []);

  const startDrawing = (e: React.MouseEvent | React.TouchEvent) => {
    setIsDrawing(true);
    draw(e);
  };

  const stopDrawing = () => {
    setIsDrawing(false);
    ctx?.beginPath();
  };

  const draw = (e: React.MouseEvent | React.TouchEvent) => {
    if (!isDrawing || !ctx || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = ('touches' in e ? e.touches[0].clientX : e.clientX) - rect.left;
    const y = ('touches' in e ? e.touches[0].clientY : e.clientY) - rect.top;

    // Scale coordinates if canvas size differs from display size
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    ctx.lineTo(x * scaleX, y * scaleY);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x * scaleX, y * scaleY);
  };

  const handleGenerate = () => {
    if (!canvasRef.current) return;
    const maskBase64 = canvasRef.current.toDataURL('image/png').split(',')[1];
    onGenerate(maskBase64, prompt);
  };

  const clearCanvas = () => {
    if (ctx && canvasRef.current) {
      ctx.fillStyle = 'black';
      ctx.fillRect(0, 0, canvasRef.current.width, canvasRef.current.height);
    }
  };

  return (
    <div className={styles.overlay}>
      <div className={`${styles.modal} glass`}>
        <div className={styles.modalHeader}>
          <h3>Inpainting Editor</h3>
          <button onClick={onClose} className={styles.closeBtn}>✕</button>
        </div>
        
        <div className={styles.canvasContainer}>
          <img src={imageUrl} alt="Background" className={styles.bgImg} />
          <canvas 
            ref={canvasRef}
            width={1024} // Internal resolution
            height={1024}
            className={styles.canvas}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={startDrawing}
            onTouchMove={draw}
            onTouchEnd={stopDrawing}
          />
        </div>

        <div className={styles.modalFooter}>
          <div className={styles.controls}>
            <button onClick={clearCanvas} className={`${styles.btn} glass`}>Clear Mask</button>
            <div className={styles.brushSize}>
              <span>Brush Size</span>
              <input 
                type="range" min="10" max="100" defaultValue="40" 
                onChange={(e) => ctx && (ctx.lineWidth = parseInt(e.target.value))} 
              />
            </div>
          </div>
          <input 
            type="text" 
            placeholder="What to change in the painted area?" 
            className={styles.promptInput}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
          />
          <button 
            className={styles.generateBtn}
            onClick={handleGenerate}
            disabled={!prompt.trim()}
          >
            Regenerate Selected Area
          </button>
        </div>
      </div>
    </div>
  );
}
