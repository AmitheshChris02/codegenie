export interface MarkdownItToken {
  attrJoin: (name: string, value: string) => void;
  tag: string;
}

export interface MarkdownItRenderer {
  rules: Record<string, unknown>;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function markdownToHtml(input: string): string {
  const lines = input.split(/\r?\n/);
  const html: string[] = [];

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line.trim()) {
      continue;
    }

    if (line.startsWith("###### ")) {
      html.push(`<h6>${escapeHtml(line.slice(7))}</h6>`);
      continue;
    }
    if (line.startsWith("##### ")) {
      html.push(`<h5>${escapeHtml(line.slice(6))}</h5>`);
      continue;
    }
    if (line.startsWith("#### ")) {
      html.push(`<h4>${escapeHtml(line.slice(5))}</h4>`);
      continue;
    }
    if (line.startsWith("### ")) {
      html.push(`<h3>${escapeHtml(line.slice(4))}</h3>`);
      continue;
    }
    if (line.startsWith("## ")) {
      html.push(`<h2>${escapeHtml(line.slice(3))}</h2>`);
      continue;
    }
    if (line.startsWith("# ")) {
      html.push(`<h1>${escapeHtml(line.slice(2))}</h1>`);
      continue;
    }

    const bulletMatch = line.match(/^[-*]\s+(.*)$/);
    if (bulletMatch) {
      html.push(`<ul><li>${escapeHtml(bulletMatch[1])}</li></ul>`);
      continue;
    }

    html.push(`<p>${escapeHtml(line)}</p>`);
  }

  return html.join("\n");
}

export default class MarkdownIt {
  renderer: MarkdownItRenderer;

  constructor() {
    this.renderer = { rules: {} };
  }

  render(text: string): string {
    return markdownToHtml(text);
  }
}
