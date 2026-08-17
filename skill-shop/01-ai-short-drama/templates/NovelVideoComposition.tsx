import {
  AbsoluteFill,
  Img,
  staticFile,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Audio,
  continueRender,
  delayRender,
} from "remotion";
import React, { useMemo, useEffect, useState } from "react";

// ─── 全局配置 ───
export const NOVEL_FPS = 30;
export const TITLE_FRAMES = 70;
export const TRANSITION_FRAMES = 15;
export const HOOK_LEAD_IN = 75;
export const KEN_BURNS_SCALE = 1.08;

// ─── 场景配置接口 ───
export interface NovelSceneConfig {
  id: string;
  title: string;
  durationInFrames: number;
  imageFile: string;
}

const ACCENT = "#ffb800";
const ACCENT_GLOW = "rgba(255, 180, 0, 0.4)";
const DARK_BG = "#0a0a0a";

// ─── 片头 ───
const TitleCard: React.FC<{ title: string; epLabel: string; seriesName: string }> = ({
  title, epLabel, seriesName
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const ts = spring({ frame, fps, config: { damping: 12, mass: 0.7 } });
  const ss = spring({ frame: frame - 15, fps, config: { damping: 14, mass: 0.6 } });
  const ls = spring({ frame: frame - 25, fps, config: { damping: 10, mass: 0.5 } });

  return (
    <AbsoluteFill style={{
      background: "linear-gradient(135deg, #0a0a0a, #1a1a2e 40%, #16213e 70%, #0a0a0a)",
      overflow: "hidden",
    }}>
      <AbsoluteFill style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <div style={{
          fontSize: 22, color: "rgba(255,255,255,0.3)",
          fontFamily: "'Microsoft YaHei',sans-serif", letterSpacing: 8, marginBottom: 30,
          opacity: interpolate(frame, [0, 40], [0, 0.3]),
          transform: `translateY(${interpolate(frame, [0, 40], [20, 0])}px)`,
        }}>{seriesName}</div>
        <div style={{
          fontSize: 80, fontWeight: 900, color: "#fff",
          fontFamily: "'Microsoft YaHei','SimHei',sans-serif", letterSpacing: 10,
          textShadow: `0 0 60px ${ACCENT_GLOW}, 0 4px 16px rgba(0,0,0,0.8)`,
          transform: `scale(${ts})`, opacity: ts, marginBottom: 20,
        }}>{title}</div>
        <div style={{
          width: interpolate(ls, [0, 1], [0, 140]), height: 3, background: ACCENT,
          borderRadius: 2, marginBottom: 24, boxShadow: `0 0 20px ${ACCENT_GLOW}`, opacity: ls,
        }} />
        <div style={{
          fontSize: 28, color: ACCENT, fontFamily: "'Microsoft YaHei',sans-serif",
          letterSpacing: 6, opacity: ss,
          transform: `translateY(${interpolate(ss, [0, 1], [20, 0])}px)`,
        }}>{epLabel}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─── 场景播放器 (Ken Burns) ───
const ScenePlayer: React.FC<{
  imageFile: string; totalFrames: number; isFirst: boolean; isLast: boolean;
}> = ({ imageFile, totalFrames, isFirst, isLast }) => {
  const frame = useCurrentFrame();
  const fi = isFirst ? 1 : interpolate(frame, [0, TRANSITION_FRAMES], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const fo = isLast ? 1 : interpolate(frame, [totalFrames - TRANSITION_FRAMES, totalFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const p = frame / totalFrames;
  const scale = interpolate(p, [0, 1], [1, KEN_BURNS_SCALE], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const tx = interpolate(p, [0, 1], [0, -15]);
  const ty = interpolate(p, [0, 1], [0, -10]);

  return (
    <AbsoluteFill style={{ opacity: Math.min(fi, fo) }}>
      <Img src={staticFile(imageFile)} style={{
        width: "100%", height: "100%", objectFit: "cover",
        transform: `scale(${scale}) translate(${tx}px, ${ty}px)`,
      }} />
    </AbsoluteFill>
  );
};

// ─── 字幕 ───
const SubtitleOverlay: React.FC<{
  subs: { startFrame: number; endFrame: number; text: string }[];
  offset: number;
}> = ({ subs, offset }) => {
  const frame = useCurrentFrame();
  const adj = frame + offset;
  const cur = subs.find(s => adj >= s.startFrame && adj < s.endFrame);
  if (!cur) return null;
  const prog = (adj - cur.startFrame) / (cur.endFrame - cur.startFrame);
  const op = interpolate(prog, [0, 0.08, 0.92, 1], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <div style={{
      position: "absolute", bottom: 140, left: 50, right: 50, textAlign: "center",
      color: "#fff", fontSize: 36, fontFamily: "'Microsoft YaHei','SimHei',sans-serif",
      fontWeight: "bold", lineHeight: 1.7,
      textShadow: "0 2px 8px rgba(0,0,0,0.95), 0 0 40px rgba(0,0,0,0.6)",
      padding: "16px 32px",
      background: "linear-gradient(transparent 0%, rgba(0,0,0,0.6) 20%, rgba(0,0,0,0.6) 80%, transparent 100%)",
      borderRadius: 12, border: "1px solid rgba(255,255,255,0.08)",
      opacity: op, transform: `translateY(${interpolate(op, [0, 1], [12, 0])}px)`,
    }}>{cur.text}</div>
  );
};

// ─── 进度条 ───
const ProgressBar: React.FC<{ cur: number; total: number }> = ({ cur, total }) => {
  const p = total > 0 ? cur / total : 0;
  return (
    <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 4, zIndex: 10 }}>
      <div style={{ width: "100%", height: "100%", background: "rgba(255,255,255,0.1)" }}>
        <div style={{
          width: `${p * 100}%`, height: "100%",
          background: `linear-gradient(90deg, ${ACCENT}, #ff6b00)`,
          boxShadow: `0 0 12px ${ACCENT_GLOW}`,
        }} />
      </div>
    </div>
  );
};

// ─── 片尾预告 ───
const HookScreen: React.FC<{ text: string; title: string }> = ({ text, title }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const es = spring({ frame, fps, config: { damping: 14, mass: 0.8 } });
  return (
    <AbsoluteFill style={{
      display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
      background: "radial-gradient(ellipse at center, #1a1a1a 0%, #000 100%)", padding: "0 60px",
    }}>
      <div style={{
        fontSize: 26, color: ACCENT, fontFamily: "'Microsoft YaHei',sans-serif",
        fontWeight: "bold", letterSpacing: 6, marginBottom: 20,
        opacity: es, transform: `translateY(${interpolate(es, [0, 1], [30, 0])}px)`,
        textShadow: `0 0 30px ${ACCENT_GLOW}`,
      }}>— 下集预告 —</div>
      <div style={{
        width: interpolate(es, [0, 1], [0, 100]), height: 3, background: ACCENT,
        borderRadius: 2, marginBottom: 36, boxShadow: `0 0 20px ${ACCENT_GLOW}`, opacity: es,
      }} />
      <div style={{
        fontSize: 42, color: "#fff", fontFamily: "'Microsoft YaHei','SimHei',sans-serif",
        fontWeight: 900, textAlign: "center", lineHeight: 1.6,
        textShadow: `0 2px 20px ${ACCENT_GLOW}`,
        opacity: es, transform: `scale(${interpolate(es, [0, 1], [0.8, 1])})`,
      }}>{text}</div>
    </AbsoluteFill>
  );
};

// ─── 主合成 ───
export interface NovelVideoProps {
  title: string;
  epLabel: string;
  seriesName: string;
  scenes: NovelSceneConfig[];
  audioFile: string;
  srtFile: string;
  hookText: string;
  totalDurationInFrames: number;
}

export const NovelVideoComposition: React.FC<NovelVideoProps> = ({
  title, epLabel, seriesName, scenes, audioFile, srtFile, hookText, totalDurationInFrames,
}) => {
  const [subs, setSubs] = useState<{ startFrame: number; endFrame: number; text: string }[]>([]);
  const [handle] = useState(() => delayRender());

  useEffect(() => {
    let dead = false;
    (async () => {
      try {
        const resp = await fetch(srtFile);
        const text = await resp.text();
        const parsed = parseSrt(text);
        if (!dead) { setSubs(parsed); continueRender(handle); }
      } catch {
        if (!dead) { setSubs([]); continueRender(handle); }
      }
    })();
    return () => { dead = true; };
  }, [srtFile, handle]);

  const frame = useCurrentFrame();
  const timeline = useMemo(() => {
    let c = 0;
    return (scenes || []).map((s, i) => {
      const st = i === 0 ? 0 : c;
      c += s.durationInFrames;
      return { ...s, start: st, index: i };
    });
  }, [scenes]);

  const shotsEnd = timeline.length > 0
    ? timeline[timeline.length - 1].start + timeline[timeline.length - 1].durationInFrames
    : 0;
  const hookStart = TITLE_FRAMES + shotsEnd - HOOK_LEAD_IN;

  return (
    <AbsoluteFill style={{ background: DARK_BG }}>
      {audioFile && <Sequence from={TITLE_FRAMES}><Audio src={staticFile(audioFile)} volume={0.85} /></Sequence>}
      <Sequence from={0} durationInFrames={TITLE_FRAMES}>
        <TitleCard title={title} epLabel={epLabel} seriesName={seriesName} />
      </Sequence>
      <Sequence from={TITLE_FRAMES} durationInFrames={shotsEnd}>
        <AbsoluteFill style={{ background: DARK_BG }}>
          {timeline.map(sc => (
            <Sequence key={sc.id} from={sc.start} durationInFrames={sc.durationInFrames}>
              <ScenePlayer imageFile={sc.imageFile} totalFrames={sc.durationInFrames}
                isFirst={sc.index === 0} isLast={sc.index === timeline.length - 1} />
            </Sequence>
          ))}
          <div style={{
            position: "absolute", top: 50, left: 40, fontSize: 18, color: "rgba(255,255,255,0.5)",
            fontFamily: "'Microsoft YaHei',sans-serif", letterSpacing: 2,
            background: "rgba(0,0,0,0.5)", padding: "6px 16px", borderRadius: 20,
            border: "1px solid rgba(255,255,255,0.08)", zIndex: 10,
          }}>{epLabel}</div>
          <SubtitleOverlay subs={subs} offset={0} />
          <ProgressBar cur={Math.max(0, frame - TITLE_FRAMES)} total={shotsEnd} />
        </AbsoluteFill>
      </Sequence>
      <Sequence from={hookStart} durationInFrames={HOOK_LEAD_IN}>
        <AbsoluteFill style={{ background: "rgba(0,0,0,0.65)" }} />
      </Sequence>
      <Sequence from={hookStart}>
        <HookScreen text={hookText} title={title} />
      </Sequence>
    </AbsoluteFill>
  );
};

// ─── SRT 解析 ───
function parseSrt(text: string): { startFrame: number; endFrame: number; text: string }[] {
  if (!text) return [];
  const tf = (t: string) => {
    const [h, m, s] = t.split(":"); const [sec, ms] = s.split(",");
    return (parseInt(h)*3600+parseInt(m)*60+parseInt(sec))*30+Math.round(parseInt(ms)/33.33);
  };
  return text.trim().split(/\n\n+/).map(b => {
    const l = b.split("\n"); const tl = l.find(x => x.includes("-->"));
    if (!tl) return null;
    const [st, en] = tl.split("-->").map(x=>x.trim());
    return {startFrame: tf(st), endFrame: tf(en), text: l.slice(l.indexOf(tl)+1).join("\n")};
  }).filter(Boolean) as any;
}
