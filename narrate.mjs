// Requires Node 20+, FFmpeg, and a Cartesia API key. Never prints credentials.
// node narrate.mjs --env-file /path/to/private.env
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = path.dirname(fileURLToPath(import.meta.url));
const envFlag = process.argv.indexOf('--env-file');
const envFile = envFlag >= 0 ? process.argv[envFlag + 1] : (process.env.CARTESIA_ENV_FILE || path.join(root, '.env'));
if (envFile && fs.existsSync(envFile)) {
  for (const line of fs.readFileSync(envFile, 'utf8').split(/\r?\n/)) {
    const match = line.match(/^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$/);
    if (!match) continue;
    const value = match[2].replace(/^(['"])(.*)\1$/, '$2');
    if (!process.env[match[1]]) process.env[match[1]] = value;
  }
}
const key = process.env.CARTESIA_API_KEY;
if (!key) throw new Error('Set CARTESIA_API_KEY in your private env file.');
const response = await fetch('https://api.cartesia.ai/tts/bytes', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${key}`,
    'Cartesia-Version': process.env.CARTESIA_API_VERSION || '2026-08-14',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model_id: process.env.CARTESIA_MODEL || 'sonic-3.6',
    transcript: fs.readFileSync(path.join(root, 'media/narration.txt'), 'utf8').trim(),
    voice: process.env.CARTESIA_VOICE_ID || 'db6b0ed5-d5d3-463d-ae85-518a07d3c2b4',
    output_format: { container: 'wav', encoding: 'pcm_s16le', sample_rate: 44100 },
    language: 'en',
    generation_config: { speed: 1.05 },
  }),
  signal: AbortSignal.timeout(120000),
});
if (!response.ok) throw new Error(`Cartesia returned HTTP ${response.status}. Check credentials and model access.`);
const audio = path.join(root, 'media/narration.wav');
fs.writeFileSync(audio, Buffer.from(await response.arrayBuffer()));
const duration = Number(execFileSync('ffprobe', ['-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',audio], {encoding:'utf8'}).trim());
if (!Number.isFinite(duration) || duration < 1) throw new Error('Invalid narration audio.');
const total = Math.max(34, duration + 0.5);
execFileSync('ffmpeg', ['-y','-i',path.join(root,'media/demo-silent.mp4'),'-i',audio,'-vf',`tpad=stop_mode=clone:stop_duration=${total}`,'-af','apad','-t',String(total),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',path.join(root,'media/demo.mp4')], {stdio:['ignore','ignore','pipe']});
console.log(`Created narrated demo (${total.toFixed(1)} seconds).`);
