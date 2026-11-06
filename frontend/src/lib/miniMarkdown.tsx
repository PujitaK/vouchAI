"use client";

import { clsx } from "clsx";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/Button";

const focusRing =
  "focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-offset-2 focus-visible:outline-accent";

const LONG_BELIEF_THRESHOLD = 700;

type Block =
  | { kind: "paragraph"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "heading"; text: string };

function renderInline(text: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);

  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={`bold-${index}`} className="font-bold text-text-primary">
          {part.slice(2, -2)}
        </strong>
      );
    }

    if (part.startsWith("`") && part.endsWith("`")) {
      return (
        <code key={`code-${index}`} className="font-mono text-[0.85em]">
          {part.slice(1, -1)}
        </code>
      );
    }

    return part;
  });
}

function parseBlocks(text: string): Block[] {
  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let list: string[] = [];

  function flushParagraph() {
    if (paragraph.length > 0) {
      blocks.push({ kind: "paragraph", text: paragraph.join(" ") });
      paragraph = [];
    }
  }

  function flushList() {
    if (list.length > 0) {
      blocks.push({ kind: "list", items: list });
      list = [];
    }
  }

  for (const rawLine of text.replace(/\r\n/g, "\n").split("\n")) {
    const line = rawLine.trimEnd();

    if (line.trim().length === 0) {
      flushParagraph();
      flushList();
      continue;
    }

    const listMatch = line.match(/^\s*[*-]\s+(.*)$/);

    if (listMatch) {
      flushParagraph();
      list.push(listMatch[1]);
      continue;
    }

    const headingMatch = line.match(/^\s{0,3}#{1,6}\s+(.*)$/);

    if (headingMatch) {
      flushParagraph();
      flushList();
      blocks.push({ kind: "heading", text: headingMatch[1] });
      continue;
    }

    flushList();
    paragraph.push(line.trim());
  }

  flushParagraph();
  flushList();

  return blocks;
}

export interface MiniMarkdownProps {
  text: string;
  className?: string;
}

export function MiniMarkdown({ text, className }: MiniMarkdownProps) {
  const blocks = parseBlocks(text);

  return (
    <div className={clsx("space-y-3", className)}>
      {blocks.map((block, index) => {
        if (block.kind === "heading") {
          return (
            <h3
              key={`heading-${index}`}
              className="font-display text-base font-bold tracking-tight text-text-primary"
            >
              {renderInline(block.text)}
            </h3>
          );
        }

        if (block.kind === "list") {
          return (
            <ul key={`list-${index}`} className="space-y-1.5">
              {block.items.map((item, itemIndex) => (
                <li
                  key={`item-${index}-${itemIndex}`}
                  className="flex gap-3"
                >
                  <span
                    className="mt-[0.55rem] h-1.5 w-1.5 shrink-0 bg-base"
                    aria-hidden="true"
                  />
                  <span>{renderInline(item)}</span>
                </li>
              ))}
            </ul>
          );
        }

        return <p key={`paragraph-${index}`}>{renderInline(block.text)}</p>;
      })}
    </div>
  );
}

export interface ClampedMiniMarkdownProps {
  text: string;
  className?: string;
}

export function ClampedMiniMarkdown({
  text,
  className,
}: ClampedMiniMarkdownProps) {
  const [expanded, setExpanded] = useState(false);
  const isLong = text.length > LONG_BELIEF_THRESHOLD;

  return (
    <div className={className}>
      <div
        className={clsx(
          !expanded && isLong && "max-h-[18rem] overflow-hidden",
        )}
      >
        <MiniMarkdown text={text} />
      </div>

      {isLong ? (
        <Button
          variant="ghost"
          onClick={() => setExpanded((value) => !value)}
          aria-expanded={expanded}
          className={clsx("mt-4", focusRing)}
        >
          {expanded ? "SHOW LESS" : "READ MORE"}
        </Button>
      ) : null}
    </div>
  );
}
