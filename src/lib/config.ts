export const MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024; // 500 MB

export const ACCEPTED_MIME_TYPES = [
  "audio/flac",
  "audio/mpeg",
  "audio/mp3",
  "audio/ogg",
  "audio/wav",
  "audio/x-wav",
  "audio/webm",
  "audio/mp4",
  "audio/m4a",
  "audio/x-m4a",
  "video/mp4",
  "video/webm",
] as const;

export const ACCEPTED_EXTENSIONS = ".flac,.mp3,.ogg,.wav,.mp4,.m4a,.webm";

export const SUPPORTED_LANGUAGES = [
  { code: "de", label: "Deutsch" },
  { code: "en", label: "English" },
  { code: "fr", label: "Français" },
  { code: "it", label: "Italiano" },
  { code: "es", label: "Español" },
  { code: "pt", label: "Português" },
  { code: "nl", label: "Nederlands" },
  { code: "pl", label: "Polski" },
  { code: "el", label: "Ελληνικά" },
  { code: "ar", label: "العربية" },
  { code: "zh", label: "中文" },
  { code: "ja", label: "日本語" },
  { code: "ko", label: "한국어" },
  { code: "vi", label: "Tiếng Việt" },
] as const;
