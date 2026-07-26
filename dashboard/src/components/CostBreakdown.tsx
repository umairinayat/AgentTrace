import { useEffect } from 'react';
import * as d3 from 'd3';
import { useContainerWidth } from '../hooks/useContainerWidth';

interface BarItem {
  label: string;
  value: number;
}

interface Props {
  title: string;
  items: BarItem[];
  formatValue?: (v: number) => string;
  color?: string;
}

export default function CostBreakdown({
  title,
  items,
  formatValue = (v) => `$${v.toFixed(4)}`,
  color = '#3B82F6',
}: Props) {
  const [containerRef, width] = useContainerWidth<HTMLDivElement>();

  useEffect(() => {
    if (!containerRef.current || items.length === 0 || width === 0) return;

    const container = containerRef.current;
    const margin = { top: 10, right: 60, bottom: 30, left: 120 };
    const barHeight = 24;
    const height = items.length * barHeight + margin.top + margin.bottom;

    d3.select(container).selectAll('*').remove();

    const svg = d3.select(container).append('svg').attr('width', width).attr('height', height);

    const xScale = d3
      .scaleLinear()
      .domain([0, d3.max(items, (d) => d.value) || 1])
      .range([margin.left, width - margin.right]);

    const yScale = d3
      .scaleBand<number>()
      .domain(items.map((_, i) => i))
      .range([margin.top, height - margin.bottom])
      .padding(0.3);

    // Labels
    svg
      .selectAll('.label')
      .data(items)
      .join('text')
      .attr('x', margin.left - 6)
      .attr('y', (_, i) => (yScale(i) ?? 0) + yScale.bandwidth() / 2)
      .attr('text-anchor', 'end')
      .attr('dominant-baseline', 'middle')
      .attr('font-size', '11px')
      .attr('fill', '#374151')
      .text((d) => d.label.length > 16 ? d.label.slice(0, 14) + '...' : d.label);

    // Bars
    svg
      .selectAll('.bar')
      .data(items)
      .join('rect')
      .attr('x', margin.left)
      .attr('y', (_, i) => yScale(i) ?? 0)
      .attr('width', (d) => Math.max(0, xScale(d.value) - margin.left))
      .attr('height', yScale.bandwidth())
      .attr('rx', 3)
      .attr('fill', color);

    // Values
    svg
      .selectAll('.value')
      .data(items)
      .join('text')
      .attr('x', (d) => xScale(d.value) + 4)
      .attr('y', (_, i) => (yScale(i) ?? 0) + yScale.bandwidth() / 2)
      .attr('dominant-baseline', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#6B7280')
      .text((d) => formatValue(d.value));
  }, [items, formatValue, color, width]);

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">{title}</h3>
      {items.length === 0 ? (
        <p className="py-4 text-center text-sm text-gray-400">No data</p>
      ) : (
        <div ref={containerRef} className="w-full" />
      )}
    </div>
  );
}
