/**
 * Shared types for Vis components.
 * Previously referenced via a global `TS` namespace that was never defined.
 */

export interface CodeIde {
  language?: string;
  markdown?: string;
  path?: string;
  cost?: number;
  exit_success?: boolean;
  env?: string;
  console?: string;
}

export interface LLM {
  llm_model?: string;
  llm_avatar?: string;
  token_use?: number;
  cost?: number;
  token_speed?: number;
  markdown?: string;
  link_url?: string;
}
