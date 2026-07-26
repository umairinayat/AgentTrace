import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import SpanInspector from './SpanInspector';
import type { SpanResponse } from '../types';

const span: SpanResponse = {
  id: 'span-1',
  trace_id: 'trace-1',
  parent_span_id: null,
  agent_name: 'my_agent',
  event_type: 'llm_call',
  started_at: '2024-01-01T00:00:00.000Z',
  ended_at: null,
  latency_ms: 42,
  model: 'gpt-4o',
  prompt_tokens: 5,
  completion_tokens: 3,
  total_tokens: 8,
  cost_usd: 0.001,
  error: null,
  input_data: { prompt: 'hello' },
  output_data: { response: 'world' },
  metadata: { foo: 'bar' },
};

describe('SpanInspector', () => {
  it('shows the empty prompt when no span is selected', () => {
    render(<SpanInspector span={null} />);
    expect(screen.getByText(/Click a span bar/i)).toBeInTheDocument();
  });

  it('renders the agent name and the Input tab by default', () => {
    render(<SpanInspector span={span} />);
    expect(screen.getByText('my_agent')).toBeInTheDocument();
    // Input data is shown by default.
    expect(screen.getByText(/"prompt"/)).toBeInTheDocument();
    expect(screen.getByText(/"hello"/)).toBeInTheDocument();
  });

  it('switches to the Output tab', () => {
    render(<SpanInspector span={span} />);
    fireEvent.click(screen.getByRole('button', { name: 'Output' }));
    expect(screen.getByText(/"response"/)).toBeInTheDocument();
    expect(screen.getByText(/"world"/)).toBeInTheDocument();
  });

  it('shows the span id on the Metadata tab', () => {
    render(<SpanInspector span={span} />);
    fireEvent.click(screen.getByRole('button', { name: 'Metadata' }));
    expect(screen.getByText(/"id": "span-1"/)).toBeInTheDocument();
  });
});
