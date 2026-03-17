import { useStats } from '../hooks/useStats';
import CostBreakdown from '../components/CostBreakdown';

export default function CostAnalytics() {
  const { data: stats, isLoading, error } = useStats();

  if (isLoading) return <div className="p-6 text-gray-400">Loading analytics...</div>;
  if (error) {
    return (
      <div className="p-6">
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">
          Failed to load stats: {(error as Error).message}
        </div>
      </div>
    );
  }
  if (!stats) return null;

  const agentItems = stats.top_agents.map((a) => ({ label: a.name, value: a.total_cost }));
  const modelItems = stats.top_models.map((m) => ({ label: m.name, value: m.total_cost }));

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold">Cost Analytics</h1>

      {/* Summary cards */}
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <SummaryCard label="Total Spend" value={`$${stats.total_cost_usd.toFixed(2)}`} />
        <SummaryCard label="Total Tokens" value={stats.total_tokens.toLocaleString()} />
        <SummaryCard label="Total Traces" value={stats.total_traces.toLocaleString()} />
        <SummaryCard
          label="Avg Cost / Trace"
          value={`$${stats.avg_cost_per_trace.toFixed(4)}`}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <CostBreakdown title="Cost by Agent (Top 10)" items={agentItems} color="#3B82F6" />
        <CostBreakdown
          title="Cost by Model (Top 10)"
          items={modelItems}
          color="#10B981"
        />
      </div>

      {/* Top models table */}
      <div className="mt-6 overflow-x-auto rounded-lg border bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Model</th>
              <th className="px-4 py-3">Total Tokens</th>
              <th className="px-4 py-3">Total Cost</th>
              <th className="px-4 py-3">Call Count</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {stats.top_models.map((m) => (
              <tr key={m.name}>
                <td className="px-4 py-3 font-medium">{m.name}</td>
                <td className="px-4 py-3">{m.total_tokens.toLocaleString()}</td>
                <td className="px-4 py-3">${m.total_cost.toFixed(4)}</td>
                <td className="px-4 py-3">{m.call_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-bold">{value}</p>
    </div>
  );
}
