import { useParams } from "react-router-dom";

export default function DiffViewer() {
  const { jobId } = useParams();

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Diff # {jobId}</h2>

      <div className="rounded-lg bg-slate-900 border border-slate-800 p-4 font-mono text-sm">
        <p className="text-slate-500">
          El diff se cargara desde Inti cuando el job este en fase QA.
        </p>
      </div>

      <div className="flex gap-3">
        <button className="flex-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3 px-4 transition-colors">
          Approve
        </button>
        <button className="flex-1 rounded-lg bg-red-600 hover:bg-red-500 text-white font-semibold py-3 px-4 transition-colors">
          Reject
        </button>
      </div>
    </div>
  );
}
