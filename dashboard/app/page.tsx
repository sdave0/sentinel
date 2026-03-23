import Link from 'next/link';

interface RunTelemetry {
  run_id: string;
  agent_name: string;
  started_at: string;
  shadow_mode: boolean;
  total_tool_calls: number;
  total_blocked: number;
  total_escalated: number;
  block_rate_pct: number;
}

export const dynamic = "force-dynamic";

export default async function Home() {
  const res = await fetch('http://127.0.0.1:8000/runs?limit=30', { cache: 'no-store' });
  
  if (!res.ok) {
    return (
      <div className="p-8 text-red-500">
        <h1>Error connecting to Sentinel API</h1>
        <p>Ensure the FastAPI server is running horizontally at localhost:8000</p>
      </div>
    );
  }

  const runs: RunTelemetry[] = await res.json();

  return (
    <main className="min-h-screen bg-neutral-950 text-white p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white mb-2">Sentinel Oversight</h1>
            <p className="text-neutral-400">Recent activity and blocked agent actions.</p>
          </div>
        </header>

        <div className="bg-neutral-900 border border-neutral-800 rounded-lg overflow-hidden shrink-0 shadow-xl">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="lowercase bg-neutral-900 border-b border-neutral-800 text-neutral-400">
              <tr>
                <th className="px-6 py-4 font-medium">Run ID</th>
                <th className="px-6 py-4 font-medium">Time</th>
                <th className="px-6 py-4 font-medium">Agent</th>
                <th className="px-6 py-4 font-medium">Mode</th>
                <th className="px-6 py-4 font-medium text-right">Calls</th>
                <th className="px-6 py-4 font-medium text-right">Blocked</th>
                <th className="px-6 py-4 font-medium text-right">Escalated</th>
                <th className="px-6 py-4 font-medium text-right">Block Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {runs.map((run) => (
                <tr key={run.run_id} className="hover:bg-neutral-800/50 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs text-blue-400">
                    <Link href={`/runs/${run.run_id}`} className="hover:underline">
                      {run.run_id.substring(0, 8)}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-neutral-300">
                    {new Date(run.started_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 font-medium text-neutral-200">
                    {run.agent_name}
                  </td>
                  <td className="px-6 py-4">
                    {run.shadow_mode ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-500/10 text-purple-400 border border-purple-500/20">
                        Shadow
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Active
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right text-neutral-300">{run.total_tool_calls}</td>
                  <td className="px-6 py-4 text-right text-red-400 font-medium">{run.total_blocked}</td>
                  <td className="px-6 py-4 text-right text-yellow-500">{run.total_escalated}</td>
                  <td className="px-6 py-4 text-right">
                    <span className={`inline-flex items-center justify-center px-2.5 py-1 rounded-full text-xs font-medium border
                      ${run.block_rate_pct === 0 
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
                        : run.block_rate_pct <= 20 
                        ? 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                        : 'bg-red-500/10 text-red-500 border-red-500/20'}`}>
                      {run.block_rate_pct}%
                    </span>
                  </td>
                </tr>
              ))}
              {runs.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-neutral-500">
                    No runs found. Execute a scenario to generate telemetry.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
