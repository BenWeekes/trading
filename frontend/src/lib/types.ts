export type EventItem = {
  id: string;
  type: string;
  symbol?: string | null;
  headline: string;
  body_excerpt?: string | null;
  source?: string | null;
  timestamp: string;
  importance: number;
};

export type RoleMessage = {
  id: string;
  role: string;
  sender: string;
  message_text: string;
  structured_payload: Record<string, unknown>;
  provider?: string | null;
  model_used?: string | null;
  input_tokens?: number;
  output_tokens?: number;
  cost_usd?: number;
  timestamp: string;
};

export type Recommendation = {
  id: string;
  symbol: string;
  direction?: string | null;
  status: string;
  strategy_type: string;
  thesis?: string | null;
  entry_price?: number | null;
  entry_logic?: string | null;
  stop_price?: number | null;
  stop_logic?: string | null;
  target_price?: number | null;
  target_logic?: string | null;
  position_size_shares?: number | null;
  position_size_dollars?: number | null;
  conviction?: number | null;
};

export type TraderAvatarSession = {
  recommendation_id: string;
  channel: string;
  agent_id: string;
  profile: string;
  started_at: string;
};

export type TraderAvatarStatus = {
  enabled: boolean;
  backend_url: string;
  client_url: string;
  profile: string;
  session?: TraderAvatarSession | null;
};

export type Summary = {
  summary_text?: string | null;
  bull_case?: string | null;
  bear_case?: string | null;
  key_disagreement?: string | null;
};

export type Position = {
  id: string;
  symbol: string;
  direction: string;
  entry_price?: number | null;
  current_price?: number | null;
  shares?: number | null;
  unrealized_pnl?: number | null;
};
