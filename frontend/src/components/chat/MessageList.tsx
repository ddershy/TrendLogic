import { useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { AgentMessage } from "../../types";

export interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  content: string;
  trace?: AgentMessage;
}

type RenderItem =
  | { kind: "message"; entry: ChatEntry }
  | { kind: "traceGroup"; id: string; traces: AgentMessage[] };

export default function MessageList({ entries }: { entries: ChatEntry[] }) {
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const items = groupEntries(entries);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [entries, openGroups]);

  return (
    <div className="messageList">
      {items.map((item) => {
        if (item.kind === "traceGroup") {
          const isOpen = Boolean(openGroups[item.id]);
          const Icon = isOpen ? ChevronDown : ChevronRight;
          return (
            <div key={item.id} className="traceGroup">
              <button
                type="button"
                className="traceToggle"
                onClick={() => setOpenGroups((current) => ({ ...current, [item.id]: !current[item.id] }))}
              >
                <Icon size={15} />
                <span>Agent 执行过程 · {item.traces.length} 条</span>
              </button>
              {isOpen ? (
                <div className="tracePanel">
                  {item.traces.map((trace, index) => (
                    <div key={`${item.id}-${index}`} className="traceLine">
                      <strong>[{trace.agent}/{trace.function ?? "执行日志"}]</strong>
                      <p>{trace.content}</p>
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
          );
        }

        return (
          <div key={item.entry.id} className={`bubbleRow ${item.entry.role}`}>
            <div className="bubble">{item.entry.content}</div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}

function groupEntries(entries: ChatEntry[]): RenderItem[] {
  const items: RenderItem[] = [];
  let traceBuffer: AgentMessage[] = [];
  let groupStartId = "";

  function flushTraceGroup() {
    if (!traceBuffer.length) return;
    items.push({ kind: "traceGroup", id: groupStartId, traces: traceBuffer });
    traceBuffer = [];
    groupStartId = "";
  }

  for (const entry of entries) {
    if (entry.trace) {
      if (!traceBuffer.length) {
        groupStartId = entry.id;
      }
      traceBuffer.push(entry.trace);
    } else {
      flushTraceGroup();
      items.push({ kind: "message", entry });
    }
  }
  flushTraceGroup();
  return items;
}
