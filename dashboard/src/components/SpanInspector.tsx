import { useState } from 'react';
import type { SpanResponse } from '../types';

const tabs = ['Input', 'Output', 'Metadata'] as const;
type Tab = (typeof tabs)[number];

function JsonBlock({ data }: { data: unknown }) {
  const text = JSON.stringify(data, null, 2);

  return (
    <div className="relative">
      <button
        className="absolute right-2 top-2 rounded bg-gray-200 px-2 py-0.5 text-xs hover:bg-gray-300"
        onClick={() => navigator.clipboard.writeText(text)}
      >
        Copy
      </button>
      <pre className="max-h-96 overflow-auto rounded bg-gray-900 p-4 text-xs text-green-300">
        {text}
      </pre>
    </div>
  );
}

interface Props {
  span: SpanResponse | null;
}

export default function SpanInspector({ span }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>('Input');

  if (!span) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-gray-400">
        Click a span bar to inspect it
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b px-4 py-3">
        <h3 className="font-semibold">{span.agent_name}</h3>
        <p className="text-xs text-gray-500">
          {span.event_type} {span.model ? `\u00B7 ${span.model}` : ''}
          {span.latency_ms != null ? ` \u00B7 ${span.latency_ms.toFixed(0)}ms` : ''}
        </p>
        {span.error && (
          <p className="mt-1 text-xs text-red-600">Error: {span.error}</p>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        {tabs.map((tab) => (
          <button
            key={tab}
            className={`px-4 py-2 text-sm font-medium ${
              activeTab === tab
                ? 'border-b-2 border-primary text-primary'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {activeTab === 'Input' && <JsonBlock data={span.input_data ?? 'No input data'} />}
        {activeTab === 'Output' && <JsonBlock data={span.output_data ?? 'No output data'} />}
        {activeTab === 'Metadata' && (
          <JsonBlock
            data={{
              id: span.id,
              trace_id: span.trace_id,
              parent_span_id: span.parent_span_id,
              event_type: span.event_type,
              model: span.model,
              prompt_tokens: span.prompt_tokens,
              completion_tokens: span.completion_tokens,
              total_tokens: span.total_tokens,
              cost_usd: span.cost_usd,
              started_at: span.started_at,
              ended_at: span.ended_at,
              latency_ms: span.latency_ms,
              ...span.metadata,
            }}
          />
        )}
      </div>
    </div>
  );
}
