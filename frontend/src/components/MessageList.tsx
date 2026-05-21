'use client';

import React from 'react';
import styles from './MessageList.module.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type?: 'image' | 'video';
  mediaUrl?: string;
}

interface MessageListProps {
  messages: Message[];
  onInpaint: (messageId: string) => void;
  onAnimate: (imageUrl: string) => void;
  isAnimating: string | null;
}

export default function MessageList({ messages, onInpaint, onAnimate, isAnimating }: MessageListProps) {
  return (
    <div className={styles.container}>
      {messages.map((msg) => (
        <div 
          key={msg.id} 
          className={`${styles.message} ${msg.role === 'user' ? styles.user : styles.assistant} animate-fade-in`}
        >
          <div className={`${styles.bubble} ${msg.role === 'user' ? 'glass' : styles.assistantBubble}`}>
            {msg.content && <p>{msg.content}</p>}
            
            {msg.mediaUrl && (
              <div className={styles.mediaContainer}>
                {msg.type === 'video' ? (
                  <video src={msg.mediaUrl} controls className={styles.media} />
                ) : (
                  <div className={styles.imageWrapper}>
                    <img src={msg.mediaUrl} alt="Generated content" className={styles.media} />
                    <div className={styles.toolBar}>
                      <button 
                        className={`${styles.toolBtn} glass`}
                        onClick={() => onInpaint(msg.id)}
                      >
                        Edit / Inpaint
                      </button>
                      <button 
                        className={`${styles.toolBtn} glass`}
                        onClick={() => onAnimate(msg.mediaUrl!)}
                        disabled={!!isAnimating}
                      >
                        {isAnimating === msg.mediaUrl ? 'Animating...' : 'Animate (2s)'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
