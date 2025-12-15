import { WEBUI_BASE_URL } from '$lib/constants';

class VideoSynthesisService {
  async startSynthesis(payload: Record<string, any>) {
    const resp = await fetch(`${WEBUI_BASE_URL}/hsai/video-synthesis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload)
    });
    if (!resp.ok) throw new Error(`video synthesis failed ${resp.status}`);
    return resp.json();
  }
}

export const videoSynthesisService = new VideoSynthesisService();