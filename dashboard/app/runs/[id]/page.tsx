import Link from 'next/link';

interface ValidationData {
  id: string;
  timestamp: string;
  tool_name: string;
  proposed_args: Record<string, any>;
  verdict: 'allowed' | 'blocked' | 'escalated';
  confidence: number;
  blocking_reason: string | null;
  retry_feedback: string | null;
  policy_triggered: string | null;
  latency_ms: number;
}

export const dynamic = "force-dynamic"; 

export default async function RunDetail({ params }: { params: { id: string } }) {
  const { id } = await params;
  const res = await fetch(`http://127.0.0.1:8000/runs/${id}`, { cache: 'no-store' });
  
  if (!res.ok) {
    return <div className="p-8 text-neutral-300">Run not found or API unreachable.</div>;
  }

  const { metadata, validations } = await res.json() as { metadata: any, validations: ValidationData[] };

  return (
    <main className="min-h-screen bg-neutral-950 text-white p-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-6 flex items-center space-x-4">
          <Link href="/" className="text-neutral-400 hover:text-white transition-colors">
            &larr; Back to runs
          </Link>
        </div>

        <div className="bg-neutral-900 border border-neutral-800 rounded-lg p-6 mb-8 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-bold mb-1 flex items-center space-x-3">
                <span>Run {metadata.run_id.substring(0, 8)}</span>
                {metadata.shadow_mode && (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-400 border border-purple-500/30">
                    Shadow Mode
                  </span>
                )}
              </h1>
              <p className="text-neutral-400 font-mono text-sm">{metadata.run_id}</p>
            </div>
            <div className="text-right">
              <div className="text-sm text-neutral-400 mb-1">Total Actions Evaluated</div>
              <div className="text-3xl font-light text-neutral-200">{metadata.total_tool_calls}</div>
            </div>
          </div>
          
          <div className="mt-8 grid grid-cols-4 gap-6 text-sm border-t border-neutral-800 pt-6">
            <div>
              <span className="block text-neutral-500 mb-1">Agent</span>
              <span className="font-medium">{metadata.agent_name}</span>
            </div>
            <div>
              <span className="block text-neutral-500 mb-1">Started</span>
              <span className="font-medium text-neutral-300">{new Date(metadata.started_at).toLocaleTimeString()}</span>
            </div>
            <div>
              <span className="block text-neutral-500 mb-1">Blocked Actions</span>
              <span className="font-bold text-red-400">{metadata.total_blocked}</span>
            </div>
            <div>
              <span className="block text-neutral-500 mb-1">System Prompt</span>
              <span className="font-mono text-neutral-300 text-xs">{metadata.prompt_hash.substring(0, 12)}</span>
            </div>
          </div>
        </div>

        <h2 className="text-xl font-bold mb-6 text-neutral-200">Validation Timeline</h2>
        
        <div className="space-y-4">
          {validations.map((val, idx) => {
            const isBlocked = val.verdict === 'blocked';
            const isEscalated = val.verdict === 'escalated';
            
            return (
              <div 
                key={val.id} 
                className={`flex flex-col relative overflow-hidden rounded-lg border p-5 shadow-sm transition-all
                  ${isBlocked 
                    ? 'bg-red-950/20 border-red-900/50 hover:bg-red-950/30' 
                    : isEscalated 
                    ? 'bg-yellow-950/20 border-yellow-900/50 hover:bg-yellow-950/30'
                    : 'bg-neutral-900 border-neutral-800 hover:bg-neutral-800/80'}`}
              >
                
                <div className={`absolute left-0 top-0 bottom-0 w-1 
                  ${isBlocked ? 'bg-red-500' : isEscalated ? 'bg-yellow-500' : 'bg-emerald-500'}`} />
                  
                <div className="flex items-start justify-between mb-4 pl-3">
                  <div className="flex items-center space-x-3">
                    <span className="font-mono text-xs text-neutral-500">#{idx + 1}</span>
                    <h3 className="font-semibold text-neutral-200 font-mono text-lg">{val.tool_name}</h3>
                  </div>
                  <div className="flex items-center space-x-4">
                    <span className="text-xs font-mono text-neutral-500">{val.latency_ms}ms</span>
                    <span className={`px-2.5 py-1 rounded text-xs font-bold uppercase tracking-wider
                      ${isBlocked ? 'text-red-400 bg-red-400/10' : isEscalated ? 'text-yellow-500 bg-yellow-500/10' : 'text-emerald-400 bg-emerald-400/10'}`}>
                      {val.verdict}
                    </span>
                  </div>
                </div>

                <div className="pl-3 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <h4 className="text-xs uppercase tracking-wider font-semibold text-neutral-500 mb-2">Proposed Arguments</h4>
                    <pre className="bg-neutral-950 border border-neutral-800 rounded p-3 text-xs text-neutral-300 font-mono overflow-auto max-h-48">
                      {JSON.stringify(val.proposed_args, null, 2)}
                    </pre>
                  </div>
                  
                  {isBlocked && (
                    <div className="space-y-4">
                      <div>
                        <h4 className="text-xs uppercase tracking-wider font-semibold text-red-500/70 mb-2">Blocking Reason</h4>
                        <div className="text-sm text-red-200 bg-red-950/40 p-3 rounded border border-red-900/30">
                          {val.blocking_reason}
                        </div>
                      </div>
                      <div>
                        <h4 className="text-xs uppercase tracking-wider font-semibold text-amber-500/70 mb-2">Retry Feedback Sent to Agent</h4>
                        <div className="text-sm font-mono text-amber-200/90 bg-amber-950/20 p-3 rounded border border-amber-900/30 leading-relaxed">
                          {val.retry_feedback}
                        </div>
                      </div>
                    </div>
                  )}

                  {isEscalated && (
                    <div>
                        <h4 className="text-xs uppercase tracking-wider font-semibold text-yellow-500/70 mb-2">Policy Pre-condition</h4>
                        <div className="text-sm text-yellow-200 bg-yellow-950/40 p-3 rounded border border-yellow-900/30">
                          {val.policy_triggered}
                        </div>
                    </div>
                  )}

                  {metadata.shadow_mode && val.blocking_reason && val.blocking_reason.includes('[SHADOW BLOCKED]') && (
                    <div className="space-y-4">
                      <div>
                        <h4 className="text-xs uppercase tracking-wider font-semibold text-purple-400 mb-2 flex items-center">
                          <span className="bg-purple-500/20 px-1.5 py-0.5 rounded mr-2 border border-purple-500/30 text-[9px] font-bold">SHADOW OVERRIDE</span>
                          WILL BLOCK
                        </h4>
                        <div className="text-sm text-purple-200 bg-purple-950/30 p-3 rounded border border-purple-900/40">
                          {val.blocking_reason.replace('[SHADOW BLOCKED] ', '')}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

              </div>
            );
          })}
          {validations.length === 0 && (
            <div className="text-center p-8 text-neutral-500">No actions intercepted for this run.</div>
          )}
        </div>
      </div>
    </main>
  );
}
