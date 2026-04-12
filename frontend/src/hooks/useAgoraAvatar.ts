"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type AgoraConfig = {
  appId: string;
  channel: string;
  token: string;
  uid: number;
};

export function useAgoraAvatar() {
  const rtcClientRef = useRef<any>(null);
  const localAudioRef = useRef<any>(null);
  const remoteVideoRef = useRef<any>(null);
  const videoContainerRef = useRef<HTMLDivElement | null>(null);

  const [connected, setConnected] = useState(false);
  const [hasVideo, setHasVideo] = useState(false);
  const [hasAudio, setHasAudio] = useState(false);
  const [muted, setMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const join = useCallback(async (config: AgoraConfig) => {
    try {
      setError(null);
      const AgoraRTC = (await import("agora-rtc-sdk-ng")).default;
      const rtcClient = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
      rtcClientRef.current = rtcClient;

      // When agent publishes tracks
      rtcClient.on("user-published", async (user: any, mediaType: "audio" | "video") => {
        await rtcClient.subscribe(user, mediaType);
        if (mediaType === "audio") {
          user.audioTrack?.play();
          setHasAudio(true);
        }
        if (mediaType === "video") {
          remoteVideoRef.current = user.videoTrack;
          setHasVideo(true);
          // Play into container using Agora's play() method
          if (videoContainerRef.current && user.videoTrack) {
            user.videoTrack.play(videoContainerRef.current);
          }
        }
      });

      rtcClient.on("user-unpublished", (_user: any, mediaType: "audio" | "video") => {
        if (mediaType === "video") { remoteVideoRef.current = null; setHasVideo(false); }
        if (mediaType === "audio") { setHasAudio(false); }
      });

      rtcClient.on("user-left", () => {
        remoteVideoRef.current = null;
        setHasVideo(false);
        setHasAudio(false);
      });

      // Join
      await rtcClient.join(config.appId, config.channel, config.token, config.uid);

      // Publish microphone
      try {
        const audioTrack = await AgoraRTC.createMicrophoneAudioTrack({ AEC: true, ANS: true, AGC: true });
        localAudioRef.current = audioTrack;
        await rtcClient.publish([audioTrack]);
      } catch (micErr) {
        console.warn("Mic not available:", micErr);
      }

      setConnected(true);
    } catch (err: any) {
      console.error("Agora join failed:", err);
      setError(err.message || "Failed to connect");
    }
  }, []);

  const leave = useCallback(async () => {
    try {
      if (localAudioRef.current) { localAudioRef.current.close(); localAudioRef.current = null; }
      if (remoteVideoRef.current) { remoteVideoRef.current.stop(); remoteVideoRef.current = null; }
      if (rtcClientRef.current) { await rtcClientRef.current.leave(); rtcClientRef.current = null; }
    } catch (err) { console.error("Leave error:", err); }
    setConnected(false);
    setHasVideo(false);
    setHasAudio(false);
    setMuted(false);
    setError(null);
  }, []);

  const toggleMute = useCallback(async () => {
    const track = localAudioRef.current;
    if (!track) return;
    try {
      await track.setEnabled(muted); // if muted, enable; if unmuted, disable
      setMuted(!muted);
    } catch (err) { console.error("Mute toggle error:", err); }
  }, [muted]);

  useEffect(() => {
    return () => {
      localAudioRef.current?.close();
      rtcClientRef.current?.leave().catch(() => {});
    };
  }, []);

  // Re-attach video when container ref changes
  useEffect(() => {
    if (videoContainerRef.current && remoteVideoRef.current && connected) {
      remoteVideoRef.current.play(videoContainerRef.current);
    }
  }, [connected]);

  return { connected, hasVideo, hasAudio, muted, error, join, leave, toggleMute, videoContainerRef };
}
