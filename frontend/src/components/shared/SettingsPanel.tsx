"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "./Toast";

type Group = { id: string; label: string; keys: string[] };

export function SettingsPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [settings, setSettings] = useState<Record<string, string>>({});
  const [groups, setGroups] = useState<Group[]>([]);
  const [dirty, setDirty] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    api.settings().then((d) => { setSettings(d.settings); setGroups(d.groups); setDirty({}); }).catch(console.error);
  }, [open]);

  if (!open) return null;

  function handleChange(key: string, value: string) {
    setDirty((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSave() {
    if (Object.keys(dirty).length === 0) { onClose(); return; }
    setSaving(true);
    try {
      await api.updateSettings(dirty);
      setSettings((prev) => ({ ...prev, ...dirty }));
      setDirty({});
      toast("Settings saved", "success");
      onClose();
    } catch (err) {
      toast("Save failed: " + (err instanceof Error ? err.message : ""), "error");
    } finally {
      setSaving(false);
    }
  }

  function getValue(key: string) { return dirty[key] ?? settings[key] ?? ""; }
  function isBoolean(val: string) { return val === "true" || val === "false"; }

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 1000,
      background: "rgba(0,0,0,0.6)", display: "flex", justifyContent: "center", alignItems: "flex-start",
      paddingTop: 60, overflowY: "auto",
    }} onClick={onClose}>
      <div style={{
        background: "var(--bg-panel)", border: "1px solid var(--line)", borderRadius: 16,
        width: 560, maxHeight: "80vh", overflowY: "auto", boxShadow: "0 20px 60px rgba(0,0,0,0.5)",
      }} onClick={(e) => e.stopPropagation()}>

        {/* Header */}
        <div style={{
          padding: "16px 20px", borderBottom: "1px solid var(--line)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
          position: "sticky", top: 0, background: "var(--bg-panel)", zIndex: 1,
        }}>
          <strong style={{ fontSize: 16 }}>Strategy Settings</strong>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-accent" onClick={handleSave} disabled={saving}>
              {saving ? "Saving..." : Object.keys(dirty).length > 0 ? `Save (${Object.keys(dirty).length})` : "Close"}
            </button>
            <button className="btn" onClick={onClose}>Cancel</button>
          </div>
        </div>

        {/* Groups */}
        <div style={{ padding: "12px 20px 20px" }}>
          {groups.map((group) => (
            <div key={group.id} style={{ marginBottom: 20 }}>
              <div style={{
                fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.1em",
                color: "var(--accent)", marginBottom: 10, paddingBottom: 6, borderBottom: "1px solid var(--line)",
              }}>
                {group.label}
              </div>
              <div style={{ display: "grid", gap: 8 }}>
                {group.keys.map((key) => {
                  const val = getValue(key);
                  const label = key.replace(/_/g, " ").replace(/pct$/, "%").replace(/^weight /, "");
                  const isDirty = key in dirty;

                  return (
                    <div key={key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                      <label style={{
                        fontSize: 13, color: isDirty ? "var(--accent)" : "var(--text-soft)",
                        flex: 1, textTransform: "capitalize",
                      }}>
                        {label}
                      </label>
                      {isBoolean(val) ? (
                        <button
                          onClick={() => handleChange(key, val === "true" ? "false" : "true")}
                          style={{
                            padding: "4px 12px", borderRadius: 6, fontSize: 12, fontWeight: 600, cursor: "pointer",
                            border: `1px solid ${val === "true" ? "var(--accent)" : "var(--line)"}`,
                            background: val === "true" ? "var(--accent-glow)" : "transparent",
                            color: val === "true" ? "var(--accent)" : "var(--text-muted)",
                          }}
                        >
                          {val === "true" ? "ON" : "OFF"}
                        </button>
                      ) : (
                        <input
                          value={val}
                          onChange={(e) => handleChange(key, e.target.value)}
                          style={{
                            width: key === "strategies_enabled" ? 160 : 90,
                            padding: "4px 8px", borderRadius: 6, fontSize: 13,
                            border: `1px solid ${isDirty ? "var(--accent)" : "var(--line)"}`,
                            background: "var(--bg)", color: "var(--text)", textAlign: "right",
                          }}
                        />
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
