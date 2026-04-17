/**
 * sessionStorage を使ったシンプルな状態管理
 * ページ遷移・リロード後も復元される
 */

import type { MeetingContext } from "./api";

const KEY_UPLOAD = "giji_upload";
const KEY_FORM = "giji_form";

export interface UploadState {
  gcs_blob: string;
  gcs_refs: string[];
  file_name: string;
  file_size: number;
  ref_names: string[];
}

export const DEFAULT_FORM: MeetingContext = {
  date: new Date().toISOString().slice(0, 10),
  time: "",
  topic: "",
  participants: "",
  keywords: "",
  glossary: "",
  custom_instructions: "",
  lang: "ja",
  template_key: "standard",
  custom_template: "",
};

function safeSession() {
  try {
    return typeof sessionStorage !== "undefined" ? sessionStorage : null;
  } catch {
    return null;
  }
}

export function saveUploadState(state: UploadState) {
  safeSession()?.setItem(KEY_UPLOAD, JSON.stringify(state));
}

export function loadUploadState(): UploadState | null {
  const raw = safeSession()?.getItem(KEY_UPLOAD);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function clearUploadState() {
  safeSession()?.removeItem(KEY_UPLOAD);
}

export function saveFormState(state: MeetingContext) {
  safeSession()?.setItem(KEY_FORM, JSON.stringify(state));
}

export function loadFormState(): MeetingContext {
  const raw = safeSession()?.getItem(KEY_FORM);
  if (!raw) return DEFAULT_FORM;
  try {
    return { ...DEFAULT_FORM, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_FORM;
  }
}
