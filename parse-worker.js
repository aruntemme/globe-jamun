// Keeps a 300 MB JSON.parse off the main thread so the globe stays interactive.
import { parseTimeline } from './timeline-core.js';

self.onmessage = async ({ data: file }) => {
  try {
    self.postMessage({ stage: 'reading' });
    const text = await file.text();
    self.postMessage({ stage: 'parsing' });
    const raw = JSON.parse(text);
    self.postMessage({ stage: 'normalizing' });
    const journey = parseTimeline(raw, (pct) =>
      self.postMessage({ stage: 'normalizing', pct }));
    journey.source = file.name;
    self.postMessage({ stage: 'done', journey });
  } catch (err) {
    self.postMessage({ stage: 'error', message: err.message });
  }
};
