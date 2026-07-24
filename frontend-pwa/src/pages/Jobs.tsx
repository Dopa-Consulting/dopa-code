import { useNavigate } from "react-router-dom";

interface MockJob {
  id: string;
  title: string;
  status: string;
  branchName: string;
  updatedAt: string;
}

const MOCK_JOBS: MockJob[] = [];

export default function Jobs() {
  const navigate = useNavigate();

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Jobs</h2>

      {MOCK_JOBS.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-slate-500">
          <p className="text-4xl mb-3">[ ]</p>
          <p className="text-sm">No hay jobs todavia</p>
          <p className="text-xs mt-1">
            Inti espera tus instrucciones desde la PC
          </p>
        </div>
      ) : (
        MOCK_JOBS.map((job) => (
          <div
            key={job.id}
            onClick={() => navigate(`/jobs/${job.id}/diff`)}
            className="rounded-lg bg-slate-900 border border-slate-800 p-4 active:bg-slate-800 transition-colors cursor-pointer"
          >
            <h3 className="font-medium">{job.title}</h3>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
                {job.status}
              </span>
              <span className="text-xs text-slate-500">{job.branchName}</span>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
