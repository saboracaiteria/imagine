export function getBackendUrl(): string {
  if (typeof window !== 'undefined') {
    const type = localStorage.getItem('grok007_backend_type') || 'modal';
    if (type === 'colab') {
      const colabUrl = localStorage.getItem('grok007_colab_url') || 'https://joylessly-sculpture-wool.ngrok-free.dev';
      if (colabUrl) return colabUrl.replace(/\/$/, '');
    } else if (type === 'local') {
      return 'http://localhost:8000';
    }
  }
  return (process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000').replace(/\/$/, '');
}

export async function generateImage(prompt: string, faceImageBase64?: string) {
  const formData = new FormData();
  formData.append('prompt', prompt);
  if (faceImageBase64) formData.append('face_img', faceImageBase64);

  const response = await fetch(`${getBackendUrl()}/api/generate`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Generation failed');
  const result = await response.json();
  if (result.status === 'success' && result.image && result.image.startsWith('outputs/')) {
    result.image = `${getBackendUrl()}/${result.image}`;
  }
  return result;
}

export async function inpaintImage(image: string, mask: string, prompt: string) {
  const formData = new FormData();
  formData.append('image', image);
  formData.append('mask', mask);
  formData.append('prompt', prompt);

  const response = await fetch(`${getBackendUrl()}/api/inpaint`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Inpainting failed');
  const result = await response.json();
  if (result.status === 'success' && result.image && result.image.startsWith('outputs/')) {
    result.image = `${getBackendUrl()}/${result.image}`;
  }
  return result;
}

export async function animateImage(
  image: string,
  prompt: string = '',
  faceImg?: string,
  onLogUpdate?: (logs: string[]) => void,
  width: number = 704,
  height: number = 480,
  motionIntensity: string = 'normal'
) {
  const canvas = document.createElement('canvas');
  canvas.width = 1024;
  canvas.height = 576;
  const ctx = canvas.getContext('2d');
  const img = new Image();
  img.crossOrigin = 'anonymous';
  img.src = image;
  await new Promise((resolve) => { img.onload = resolve; });
  ctx?.drawImage(img, 0, 0, 1024, 576);
  const resizedImage = canvas.toDataURL('image/jpeg');

  // Iniciar a geração via endpoint de Polling
  const startResponse = await fetch(`${getBackendUrl()}/api/animate/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      image: resizedImage, 
      prompt, 
      face_img: faceImg,
      width,
      height,
      motion_intensity: motionIntensity
    }),
  });
  
  if (!startResponse.ok) {
    const err = await startResponse.json().catch(() => ({ message: 'Failed to start animation' }));
    throw new Error(err.message || 'Failed to start animation');
  }

  const { job_id } = await startResponse.json();

  // Polling loop (checar a cada 5 segundos)
  while (true) {
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    const statusResponse = await fetch(`${getBackendUrl()}/api/animate/status?job_id=${job_id}`);
    if (!statusResponse.ok) continue; // Ignora erros de rede temporários
    
    const result = await statusResponse.json();
    
    if (result.logs && onLogUpdate) {
      onLogUpdate(result.logs);
    }

    if (result.status === 'success') {
      if (result.video && result.video.startsWith('outputs/')) {
        result.video = `${getBackendUrl()}/${result.video}`;
      }
      return result;
    } else if (result.status === 'error') {
      throw new Error(result.message || 'Erro durante a geração');
    }
    // se for 'processing', continua o loop
  }
}

/** Testa se o backend está online (usa endpoint raiz que sempre existe) */
export async function testUpload(): Promise<{ ok: boolean; message: string }> {
  try {
    const res = await fetch(`${getBackendUrl()}/`, {
      signal: AbortSignal.timeout(8000), // 8s timeout
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, message: data.status || 'Backend online ✅' };
    }
    return { ok: false, message: `Erro HTTP ${res.status}` };
  } catch (e: any) {
    if (e.name === 'TimeoutError') return { ok: false, message: 'Backend offline (timeout)' };
    return { ok: false, message: 'Backend offline — Modal pode estar dormindo' };
  }
}

/** Usa o Cérebro (Brain AI) para expandir o prompt */
export async function refinePrompt(prompt: string): Promise<{ refined: string }> {
  const formData = new FormData();
  formData.append('prompt', prompt);

  const response = await fetch(`${getBackendUrl()}/api/refine`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) throw new Error('Refinement failed');
  return response.json();
}
