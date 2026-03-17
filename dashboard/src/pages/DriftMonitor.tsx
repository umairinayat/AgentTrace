import { useDriftAlerts, useRebuildBaseline } from '../hooks/useDrift';
import DriftChart from '../components/DriftChart';
import AlertFeed from '../components/AlertFeed';

export default function DriftMonitor() {
  const { data: alerts, isLoading, error } = useDriftAlerts();
  const rebuildMutation = useRebuildBaseline();

  if (isLoading) return <div className="p-6 text-gray-400">Loading drift data...</div>;
  if (error) {
    return (
      <div className="p-6">
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">
          Failed to load drift data: {(error as Error).message}
        </div>
      </div>
    );
  }

  const allAlerts = alerts ?? [];

  // Group alerts by agent
  const byAgent = new Map<string, typeof allAlerts>();
  for (const alert of allAlerts) {
    const list = byAgent.get(alert.agent_name) ?? [];
    list.push(alert);
    byAgent.set(alert.agent_name, list);
  }

  const agents = Array.from(byAgent.entries());

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold">Drift Monitor</h1>

      {agents.length === 0 && (
        <div className="rounded-lg border bg-white p-8 text-center text-gray-400">
          No drift data yet. Drift detection runs automatically when baselines are built.
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {agents.map(([agentName, agentAlerts]) => {
          const activeCount = agentAlerts.filter((a) => !a.resolved).length;
          return (
            <div key={agentName} className="rounded-lg border bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <h3 className="font-semibold">{agentName}</h3>
                  {activeCount > 0 && (
                    <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                      {activeCount} active alert{activeCount > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                <button
                  className="rounded bg-primary px-3 py-1 text-xs text-white hover:bg-blue-600 disabled:opacity-50"
                  disabled={rebuildMutation.isPending}
                  onClick={() => rebuildMutation.mutate(agentName)}
                >
                  {rebuildMutation.isPending ? 'Rebuilding...' : 'Rebuild Baseline'}
                </button>
              </div>
              <DriftChart alerts={agentAlerts} />
            </div>
          );
        })}
      </div>

      {/* Alert list */}
      {allAlerts.length > 0 && (
        <div className="mt-8">
          <h2 className="mb-4 text-lg font-semibold">All Alerts</h2>
          <div className="rounded-lg border bg-white p-4 shadow-sm">
            <AlertFeed alerts={allAlerts} />
          </div>
        </div>
      )}
    </div>
  );
}
