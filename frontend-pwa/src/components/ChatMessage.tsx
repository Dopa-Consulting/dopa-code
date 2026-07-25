import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessageProps {
  role: "intl" | "user" | "architect" | "builder" | "reviewer" | "system";
  content: string;
  timestamp?: string;
  jobId?: string;
  actions?: ActionButton[];
  onAction?: (action: string, jobId: string) => void;
}

interface ActionButton {
  id: string;
  label: string;
  variant: "approve" | "reject" | "deploy" | "merge" | "default";
}

const ROLE_ICONS: Record<string, string> = {
  intl: "I",
  user: "U",
  architect: "A",
  builder: "B",
  reviewer: "R",
  system: "S",
};

const ROLE_COLORS: Record<string, string> = {
  intl: "border-amber-500 bg-amber-500/5",
  user: "border-blue-500 bg-blue-500/5",
  architect: "border-purple-500 bg-purple-500/5",
  builder: "border-emerald-500 bg-emerald-500/5",
  reviewer: "border-cyan-500 bg-cyan-500/5",
  system: "border-slate-600 bg-slate-800/50",
};

const ACTION_STYLES: Record<string, string> = {
  approve: "bg-emerald-600 hover:bg-emerald-500 text-white",
  reject: "bg-red-600 hover:bg-red-500 text-white",
  deploy: "bg-blue-600 hover:bg-blue-500 text-white",
  merge: "bg-amber-600 hover:bg-amber-500 text-white",
  default: "bg-slate-700 hover:bg-slate-600 text-slate-300",
};

export default function ChatMessage({ role, content, timestamp, jobId, actions, onAction }: ChatMessageProps) {
  return (
    <div className={`border-l-2 rounded-r-lg p-3 mb-3 ${ROLE_COLORS[role] || ROLE_COLORS.system}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="w-5 h-5 rounded-full bg-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
          {ROLE_ICONS[role] || "?"}
        </span>
        <span className="text-xs font-medium text-slate-300">{role}</span>
        {timestamp && <span className="text-xs text-slate-600 ml-auto">{timestamp}</span>}
        {jobId && <span className="text-xs text-slate-600">#{jobId.slice(0, 8)}</span>}
      </div>

      <div className="prose prose-invert prose-sm max-w-none text-slate-300 text-sm [&_pre]:bg-slate-950 [&_pre]:border [&_pre]:border-slate-800 [&_pre]:rounded [&_pre]:p-3 [&_pre]:overflow-x-auto [&_code]:bg-slate-800 [&_code]:px-1 [&_code]:rounded [&_code]:text-xs [&_table]:w-full [&_table]:text-xs [&_th]:bg-slate-800 [&_th]:p-2 [&_th]:text-left [&_td]:p-2 [&_td]:border-t [&_td]:border-slate-800 [&_a]:text-amber-400">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
      </div>

      {actions && actions.length > 0 && (
        <div className="flex gap-2 mt-3 flex-wrap">
          {actions.map((a) => (
            <button
              key={a.id}
              onClick={() => onAction?.(a.id, jobId || "")}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${ACTION_STYLES[a.variant] || ACTION_STYLES.default}`}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
