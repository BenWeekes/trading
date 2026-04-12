"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type AgoraConfig = {
  appId: string;
  channel: string;
  token: string;
  uid: number;
  agentUid?: string;
};

type AgoraState = {
  connected: boolean;
  agentVideoTrack: any | null;
  agentAudioPlaying: boolean;
  error: string | null;
};

export function useAgoraAvatar() {
  const rtcClientRef = useRef<any>(null);
  const localAudioRef = useRef<any>(null);
  const videoContainerRef = useRef<HTMLDivElement | null>(null);
  const [state, setState] = useState<AgoraState>({
    connected: false,
    agentVideoTrack: null,
    agentAudioPlaying: false,
    error: null,
  });

  const join = useCallback(async (config: AgoraConfig) => {
    try {
      // Dynamic import — agora-rtc-sdk-ng only works in browser
      const AgoraRTC = (await import("agora-rtc-sdk-ng")).default;

      const rtcClient = AgoraRTC.createClient({ mode: "rtc", codec: "vp8" });
      rtcClientRef.current = rtcClient;

      // Subscribe to remote tracks (the avatar agent)
      rtcClient.on("user-published", async (user: any, mediaType: "audio" | "video") => {
        await rtcClient.subscribe(user, mediaType);
        if (mediaType === "audio") {
          user.audioTrack?.play();
          setState((s) => ({ ...s, agentAudioPlaying: true }));
        }
        if (mediaType === "video") {
          setState((s) => ({ ...s, agentVideoTrack: user.videoTrack }));
          // Play video into container
          if (videoContainerRef.current && user.videoTrack) {
            user.videoTrack.play(videoContainerRef.current);
          }
        }
      });

      rtcClient.on("user-unpublished", (_user: any, mediaType: "audio" | "video") => {
        if (mediaType === "video") {
          setState((s) => ({ ...s, agentVideoTrack: null }));
        }
        if (mediaType === "audio") {
          setState((s) => ({ ...s, agentAudioPlaying: false }));
        }
      });

      rtcClient.on("user-left", () => {
        setState((s) => ({ ...s, agentVideoTrack: null, agentAudioPlaying: false }));
      });

      // Join channel
      await rtcClient.join(config.appId, config.channel, config.token, config.uid);

      // Publish local microphone audio
      try {
        const audioTrack = await AgoraRTC.createMicrophoneAudioTrack({
          AEC: true,
          ANS: true,
          AGC: true,
        });
        localAudioRef.current = audioTrack;
        await rtcClient.publish([audioTrack]);
      } catch (micErr) {
        console.warn("Microphone not available:", micErr);
      }

      setState((s) => ({ ...s, connected: true, error: null }));
    } catch (err: any) {
      console.error("Agora join failed:", err);
      setState((s) => ({ ...s, error: err.message || "Failed to join" }));
    }
  }, []);

  const leave = useCallback(async () => {
    try {
      if (localAudioRef.current) {
        localAudioRef.current.close();
        localAudioRef.current = null;
      }
      if (rtcClientRef.current) {
        await rtcClientRef.current.leave();
        rtcClientRef.current = null;
      }
    } catch (err) {
      console.error("Agora leave error:", err);
    }
    setState({ connected: false, agentVideoTrack: null, agentAudioPlaying: false, error: null });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (rtcClientRef.current) {
        localAudioRef.current?.close();
        rtcClientRef.current.leave().catch(() => {});
      }
    };
  }, []);

  return { ...state, join, leave, videoContainerRef };
}
