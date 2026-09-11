const HTML_ENTITIES: Record<string, string> = {
  "&nbsp;": " ",
  "&lt;": "<",
  "&gt;": ">",
  "&amp;": "&",
  "&quot;": '"',
  "&#39;": "'",
};

export function cleanDisplayText(
  value: string | null | undefined,
  fallback = "",
): string {
  if (!value) {
    return fallback;
  }
  const cleaned = value
    .replace(/<[^>]*>/g, " ")
    .replace(
      /&(nbsp|lt|gt|amp|quot|#39);/gi,
      (entity) => HTML_ENTITIES[entity.toLowerCase()] ?? " ",
    )
    .replace(/\s+/g, " ")
    .trim();
  return cleaned || fallback;
}
