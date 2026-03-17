import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTraces } from '../hooks/useTraces';
import type { TraceFilters } from '../types';

const statusColors: Record<string, string> = {
  completed: 'bg-green-100 text-green-800',
  running: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
};

export default function TraceList() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<TraceFilters>({
    page: 1,
    page_size: 50,
    sort_by: 'started_at',
    sort_order: 'desc',
  });

  const { data, isLoading, error } = useTraces(filters);

  function toggleSort(column: string) {
    setFilters((f) => ({
      ...f,
      sort_by: column,
      sort_order: f.sort_by === column && f.sort_order === 'desc' ? 'asc' : 'desc',
    }));
  }

  function SortIcon({ column }: { column: string }) {
    if (filters.sort_by !== column) return null;
    return <span className="ml-1">{filters.sort_order === 'asc' ? '\u25B2' : '\u25BC'}</span>;
  }

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold">Traces</h1>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <input
          type="text"
          placeholder="Filter by agent name..."
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-primary focus:outline-none"
          value={filters.agent_name || ''}
          onChange={(e) =>
            setFilters((f) => ({ ...f, agent_name: e.target.value || undefined, page: 1 }))
          }
        />
        <select
          className="rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-primary focus:outline-none"
          value={filters.status || ''}
          onChange={(e) =>
            setFilters((f) => ({ ...f, status: e.target.value || undefined, page: 1 }))
          }
        >
          <option value="">All statuses</option>
          <option value="completed">Completed</option>
          <option value="running">Running</option>
          <option value="error">Error</option>
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 rounded bg-red-50 p-3 text-sm text-red-700">
          Failed to load traces: {(error as Error).message}
        </div>
      )}

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white shadow-sm">
        <table className="w-full text-left text-sm">
          <thead className="border-b bg-gray-50 text-xs uppercase text-gray-500">
            <tr>
              {[
                { key: 'name', label: 'Trace Name' },
                { key: 'agent_name', label: 'Agent' },
                { key: 'started_at', label: 'Started' },
                { key: 'duration_ms', label: 'Duration' },
                { key: 'total_tokens', label: 'Tokens' },
                { key: 'total_cost_usd', label: 'Cost ($)' },
                { key: 'status', label: 'Status' },
              ].map((col) => (
                <th
                  key={col.key}
                  className="cursor-pointer px-4 py-3 hover:text-gray-700"
                  onClick={() => toggleSort(col.key)}
                >
                  {col.label}
                  <SortIcon column={col.key} />
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {isLoading && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  Loading...
                </td>
              </tr>
            )}
            {data?.items.map((trace) => (
              <tr
                key={trace.id}
                className="cursor-pointer hover:bg-gray-50"
                onClick={() => navigate(`/traces/${trace.id}`)}
              >
                <td className="px-4 py-3 font-medium">{trace.name}</td>
                <td className="px-4 py-3">{trace.name}</td>
                <td className="px-4 py-3">
                  {new Date(trace.started_at).toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  {trace.duration_ms != null ? `${trace.duration_ms.toFixed(0)}ms` : '-'}
                </td>
                <td className="px-4 py-3">
                  {trace.total_tokens?.toLocaleString() ?? '-'}
                </td>
                <td className="px-4 py-3">
                  {trace.total_cost_usd != null ? `$${trace.total_cost_usd.toFixed(4)}` : '-'}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                      statusColors[trace.status] || 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {trace.status}
                  </span>
                </td>
              </tr>
            ))}
            {data && data.items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-gray-400">
                  No traces found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm text-gray-500">
            Page {data.page} of {data.pages} ({data.total} total)
          </span>
          <div className="flex gap-2">
            <button
              disabled={data.page <= 1}
              className="rounded border px-3 py-1 text-sm disabled:opacity-40"
              onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
            >
              Previous
            </button>
            <button
              disabled={data.page >= data.pages}
              className="rounded border px-3 py-1 text-sm disabled:opacity-40"
              onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
