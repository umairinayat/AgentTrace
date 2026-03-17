import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { TimelineSpan } from '../types';

const EVENT_COLORS: Record<string, string> = {
  llm_call_start: '#3B82F6',
  llm_call_end: '#3B82F6',
  tool_call_start: '#F59E0B',
  tool_call_end: '#F59E0B',
  agent_start: '#10B981',
  agent_end: '#10B981',
  error: '#EF4444',
};

function barColor(span: TimelineSpan): string {
  if (span.error) return '#EF4444';
  return EVENT_COLORS[span.event_type] || '#6B7280';
}

interface Props {
  spans: TimelineSpan[];
  totalDurationMs: number;
  selectedSpanId: string | null;
  onSelectSpan: (spanId: string) => void;
}

export default function GanttTimeline({
  spans,
  totalDurationMs,
  selectedSpanId,
  onSelectSpan,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || spans.length === 0) return;

    const container = containerRef.current;
    const margin = { top: 20, right: 30, bottom: 30, left: 160 };
    const rowHeight = 28;
    const width = container.clientWidth;
    const height = Math.max(200, spans.length * rowHeight + margin.top + margin.bottom);

    // Clear previous
    d3.select(container).selectAll('*').remove();

    const svg = d3
      .select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height);

    // Scales
    const xScale = d3
      .scaleLinear()
      .domain([0, totalDurationMs])
      .range([margin.left, width - margin.right]);

    const yScale = d3
      .scaleBand<number>()
      .domain(spans.map((_, i) => i))
      .range([margin.top, height - margin.bottom])
      .padding(0.2);

    // X axis
    svg
      .append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(
        d3
          .axisBottom(xScale)
          .ticks(6)
          .tickFormat((d) => `${d}ms`),
      )
      .selectAll('text')
      .attr('font-size', '11px');

    // Y axis labels
    svg
      .append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .selectAll('text')
      .data(spans)
      .join('text')
      .attr('x', -6)
      .attr('y', (_, i) => (yScale(i) ?? 0) + yScale.bandwidth() / 2)
      .attr('text-anchor', 'end')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', '11px')
      .attr('fill', '#374151')
      .text((d) => `${d.agent_name} (${d.event_type.replace(/_/g, ' ')})`);

    // Tooltip
    const tooltip = d3
      .select(container)
      .append('div')
      .attr(
        'class',
        'absolute hidden rounded bg-gray-800 px-3 py-2 text-xs text-white shadow-lg pointer-events-none z-10',
      );

    // Bars
    svg
      .selectAll('.bar')
      .data(spans)
      .join('rect')
      .attr('class', 'bar cursor-pointer')
      .attr('x', (d) => xScale(d.start_offset_ms))
      .attr('y', (_, i) => yScale(i) ?? 0)
      .attr('width', (d) => Math.max(2, xScale(d.start_offset_ms + d.duration_ms) - xScale(d.start_offset_ms)))
      .attr('height', yScale.bandwidth())
      .attr('rx', 3)
      .attr('fill', (d) => barColor(d))
      .attr('opacity', (d) => (selectedSpanId && d.span_id !== selectedSpanId ? 0.4 : 1))
      .attr('stroke', (d) => (d.span_id === selectedSpanId ? '#1E3A5F' : 'none'))
      .attr('stroke-width', 2)
      .on('click', (_, d) => onSelectSpan(d.span_id))
      .on('mouseenter', (event, d) => {
        const lines = [
          d.model ? `Model: ${d.model}` : null,
          d.total_tokens != null ? `Tokens: ${d.total_tokens}` : null,
          d.cost_usd != null ? `Cost: $${d.cost_usd.toFixed(4)}` : null,
          `Latency: ${d.duration_ms.toFixed(0)}ms`,
          d.error ? `Error: ${d.error}` : null,
        ].filter(Boolean);

        tooltip
          .html(lines.join('<br/>'))
          .classed('hidden', false)
          .style('left', `${event.offsetX + 10}px`)
          .style('top', `${event.offsetY - 10}px`);
      })
      .on('mouseleave', () => tooltip.classed('hidden', true));

    // Legend
    const legend = svg
      .append('g')
      .attr('transform', `translate(${margin.left}, ${margin.top - 10})`);

    const legendItems = [
      { label: 'LLM Call', color: '#3B82F6' },
      { label: 'Tool Call', color: '#F59E0B' },
      { label: 'Agent', color: '#10B981' },
      { label: 'Error', color: '#EF4444' },
    ];

    legendItems.forEach((item, i) => {
      const g = legend.append('g').attr('transform', `translate(${i * 100}, 0)`);
      g.append('rect').attr('width', 10).attr('height', 10).attr('rx', 2).attr('fill', item.color);
      g.append('text')
        .attr('x', 14)
        .attr('y', 9)
        .attr('font-size', '10px')
        .attr('fill', '#6B7280')
        .text(item.label);
    });
  }, [spans, totalDurationMs, selectedSpanId, onSelectSpan]);

  if (spans.length === 0) {
    return <div className="p-8 text-center text-gray-400">No spans to display</div>;
  }

  return <div ref={containerRef} className="relative w-full" />;
}
