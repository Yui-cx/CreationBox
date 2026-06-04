import { Fragment } from "react";
import type { ReactNode } from "react";

function renderInlineMarkdown(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    const key = `${match.index}-${token}`;
    if (token.startsWith("`")) {
      nodes.push(<code key={key}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("**")) {
      nodes.push(<strong key={key}>{token.slice(2, -2)}</strong>);
    } else {
      nodes.push(<em key={key}>{token.slice(1, -1)}</em>);
    }
    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
}

export function MarkdownRenderer({ markdown, emptyText = "暂无内容" }: { markdown: string; emptyText?: string }) {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let list: string[] = [];
  let orderedList: string[] = [];
  let codeLines: string[] = [];
  let inCode = false;

  function flushParagraph() {
    if (paragraph.length === 0) return;
    blocks.push(<p key={`p-${blocks.length}`}>{renderInlineMarkdown(paragraph.join(" "))}</p>);
    paragraph = [];
  }

  function flushList() {
    if (list.length > 0) {
      blocks.push(
        <ul key={`ul-${blocks.length}`}>
          {list.map((item, index) => <li key={`${index}-${item}`}>{renderInlineMarkdown(item)}</li>)}
        </ul>
      );
      list = [];
    }
    if (orderedList.length > 0) {
      blocks.push(
        <ol key={`ol-${blocks.length}`}>
          {orderedList.map((item, index) => <li key={`${index}-${item}`}>{renderInlineMarkdown(item)}</li>)}
        </ol>
      );
      orderedList = [];
    }
  }

  lines.forEach((line) => {
    if (line.trim().startsWith("```")) {
      flushParagraph();
      flushList();
      if (inCode) {
        blocks.push(<pre key={`code-${blocks.length}`}><code>{codeLines.join("\n")}</code></pre>);
        codeLines = [];
      }
      inCode = !inCode;
      return;
    }

    if (inCode) {
      codeLines.push(line);
      return;
    }

    if (!line.trim()) {
      flushParagraph();
      flushList();
      return;
    }

    const heading = /^(#{1,3})\s+(.+)$/.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      const content = renderInlineMarkdown(heading[2]);
      if (level === 1) blocks.push(<h1 key={`h-${blocks.length}`}>{content}</h1>);
      if (level === 2) blocks.push(<h2 key={`h-${blocks.length}`}>{content}</h2>);
      if (level === 3) blocks.push(<h3 key={`h-${blocks.length}`}>{content}</h3>);
      return;
    }

    const quote = /^>\s?(.+)$/.exec(line);
    if (quote) {
      flushParagraph();
      flushList();
      blocks.push(<blockquote key={`q-${blocks.length}`}>{renderInlineMarkdown(quote[1])}</blockquote>);
      return;
    }

    const unordered = /^[-*]\s+(.+)$/.exec(line);
    if (unordered) {
      flushParagraph();
      orderedList = [];
      list.push(unordered[1]);
      return;
    }

    const ordered = /^\d+\.\s+(.+)$/.exec(line);
    if (ordered) {
      flushParagraph();
      list = [];
      orderedList.push(ordered[1]);
      return;
    }

    paragraph.push(line);
  });

  if (inCode) {
    blocks.push(<pre key={`code-${blocks.length}`}><code>{codeLines.join("\n")}</code></pre>);
  }
  flushParagraph();
  flushList();

  return (
    <div className="markdown-body">
      {blocks.length > 0 ? blocks.map((block, index) => <Fragment key={index}>{block}</Fragment>) : <p className="muted">{emptyText}</p>}
    </div>
  );
}

