---
id: streaming.live-streaming
category: streaming
name: Live Streaming
owning_agent: S-34
maturity: emerging
languages:
- python
- typescript
- go
tags:
- rtmp
- hls
- dash
- ffmpeg
- transcode
related:
- streaming.webrtc
- cdn.cdn
domain: core
---

# Live Streaming

## 1. Overview

Live Streaming captures, encodes, and delivers live video to viewers with adaptive bitrate. HLS and DASH are the dominant protocols, with RTMP remaining common for ingest.

## 2. Core Principles

- Live Streaming must be implemented with clear ownership and documented operational procedures.
- The implementation must be testable, observable, and recoverable in failure scenarios.
- Configuration must be externalised and never hardcoded in source control.
- Failure modes must be explicitly handled with appropriate fallbacks and timeouts.
- The concept's effectiveness must be measurable through metrics, logs, or traces.

## 3. Sub-Concepts


### 3.1 Ingest (RTMP / SRT)

**Definition:** The protocol used to send a live stream from broadcaster to the media server. RTMP is the legacy standard; SRT offers lower latency and better packet-loss recovery.

### 3.2 Transcoding & Packaging

**Definition:** Converting the incoming stream to multiple resolutions and bitrates (ABR ladder) and packaging into HLS (.m3u8 + .ts) or DASH (.mpd) segments.

**Implementation:** FFmpeg or GStreamer for transcoding; MediaServer (nginx-rtmp), Mux, or AWS MediaLive for managed pipelines.

### 3.3 Playback & Delivery

**Definition:** Serving segmented video to end users via CDN. HLS is supported natively on iOS; DASH is preferred on Android and web.

### 3.4 Latency Considerations

**Definition:** Live streaming latency depends on segment duration and CDN cache TTL. LL-HLS and LL-DASH reduce latency to 2–5 seconds.

## 4. Implementation Patterns

```bash
# FFmpeg — RTMP ingest → HLS output
ffmpeg -i rtmp://localhost/live/stream \
  -c:v libx264 -preset veryfast -crf 22 \
  -c:a aac -b:a 128k \
  -f hls -hls_time 4 -hls_list_size 6 \
  /var/www/hls/stream.m3u8
```

```html
<!-- HLS.js player -->
<video id='player' controls autoplay></video>
<script src='https://cdn.jsdelivr.net/npm/hls.js@latest'></script>
<script>
  const video = document.getElementById('player');
  const hls = new Hls();
  hls.loadSource('/hls/stream.m3u8');
  hls.attachMedia(video);
</script>
```

## 5. Anti-Patterns


**Fixed bitrate without ABR** — Streaming a single bitrate forces viewers with slow connections to buffer or drop out.

**Long segment durations** — HLS segments longer than 6 seconds increase channel change delay and live latency.


## 6. Real-World Examples


- **Twitch** — Uses RTMP ingest, FFmpeg transcoding, and HLS delivery with <3s latency.

- **YouTube Live** — DASH-based ABR with hardware-accelerated encoding.

- **Mux** — Managed live streaming API handling ingest, transcoding, and playback.


## 7. Detection Signals


**Presence:** Detects library imports, configuration files, and code patterns specific to Live Streaming.

**Absence:** No evidence of this concept's implementation in the codebase.

