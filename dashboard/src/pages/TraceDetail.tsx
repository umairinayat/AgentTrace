import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useTrace, useTimeline } from '../hooks/useTraces';
import GanttTimeline from '../components/GanttTimeline';
import SpanInspector from '../components/SpanInspector';

export default function TraceDetail() {
  const { traceId } = useParams<{ traceId: string }>();
  const { data: trace, isLoading, error } = useTrace(traceId!);
  const { data: timeline } = useTimeline(traceId!);
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);

  const selectedSpan =
    trace?.spans.find((s) => s.id === selectedSpanId) ?? null;

  if (isLoading) {
    return <div className="p-6 text-gray-400">Loading trace...</div>;
  }

  if (error || !trace) {
    return (
      <div className="p-6">
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">
          {error ? (error as Error).message : 'Trace not found'}
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Breadcrumb */}
      <div className="border-b bg-white px-6 py-3">
        <nav className="text-sm text-gray-500">
          <Link to="/traces" className="hover:text-primary">
            Traces
          </Link>
          <span className="mx-2">/</span>
          <span className="text-gray-900">{trace.name}</span>
        </nav>
      </div>

      {/* Summary chips */}
      <div className="flex flex-wrap gap-3 border-b bg-white px-6 py-4">
        <Chip label="Duration" value={trace.duration_ms != null ? `${trace.duration_ms.toFixed(0)}ms` : '-'} />
        <Chip label="Tokens" value={trace.total_tokens?.toLocaleString() ?? '-'} />
        <Chip label="Cost" value={trace.total_cost_usd != null ? `$${trace.total_cost_usd.toFixed(4)}` : '-'} />
        <Chip label="Spans" value={String(trace.spans.length)} />
        <Chip
          label="Status"
          value={trace.status}
          color={trace.status === 'error' ? 'text-red-600' : trace.status === 'running' ? 'text-yellow-600' : 'text-green-600'}
        />
      </div>

      {/* Main section */}
      <div className="flex flex-1 overflow-hidden">
        {/* Gantt chart */}
        <div className="flex-1 overflow-auto border-r p-4">
          {timeline ? (
            <GanttTimeline
              spans={timeline.spans}
              totalDurationMs={timeline.total_duration_ms}
              selectedSpanId={selectedSpanId}
              onSelectSpan={setSelectedSpanId}
            />
          ) : (
            <div className="text-center text-gray-400">Loading timeline...</div>
          )}
        </div>

        {/* Span inspector */}
        <div className="w-96 overflow-auto bg-white">
          <SpanInspector span={selectedSpan} />
        </div>
      </div>
    </div>
  );
}

function Chip({
  label,
  value,
  color = 'text-gray-900',
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="rounded-lg border bg-gray-50 px-3 py-1.5">
      <span className="text-xs text-gray-500">{label}: </span>
      <span className={`text-sm font-medium ${color}`}>{value}</span>
    </div>
  );
}
