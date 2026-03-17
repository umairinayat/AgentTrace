import { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import type { DriftAlertResponse } from '../types';

interface Props {
  alerts: DriftAlertResponse[];
  threshold?: number;
}

export default function DriftChart({ alerts, threshold = 0.15 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current || alerts.length === 0) return;

    const container = containerRef.current;
    const margin = { top: 20, right: 20, bottom: 40, left: 50 };
    const width = container.clientWidth;
    const height = 200;

    d3.select(container).selectAll('*').remove();

    const svg = d3.select(container).append('svg').attr('width', width).attr('height', height);

    const data = alerts
      .filter((a) => a.score != null)
      .map((a) => ({ date: new Date(a.detected_at), score: a.score! }))
      .sort((a, b) => a.date.getTime() - b.date.getTime());

    if (data.length === 0) return;

    const xScale = d3
      .scaleTime()
      .domain(d3.extent(data, (d) => d.date) as [Date, Date])
      .range([margin.left, width - margin.right]);

    const yScale = d3
      .scaleLinear()
      .domain([0, Math.max(d3.max(data, (d) => d.score) || 0.3, threshold * 1.5)])
      .range([height - margin.bottom, margin.top]);

    // X axis
    svg
      .append('g')
      .attr('transform', `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(xScale).ticks(5))
      .selectAll('text')
      .attr('font-size', '10px');

    // Y axis
    svg
      .append('g')
      .attr('transform', `translate(${margin.left},0)`)
      .call(d3.axisLeft(yScale).ticks(5))
      .selectAll('text')
      .attr('font-size', '10px');

    // Threshold line
    svg
      .append('line')
      .attr('x1', margin.left)
      .attr('x2', width - margin.right)
      .attr('y1', yScale(threshold))
      .attr('y2', yScale(threshold))
      .attr('stroke', '#EF4444')
      .attr('stroke-dasharray', '6,3')
      .attr('stroke-width', 1.5);

    svg
      .append('text')
      .attr('x', width - margin.right - 4)
      .attr('y', yScale(threshold) - 4)
      .attr('text-anchor', 'end')
      .attr('font-size', '9px')
      .attr('fill', '#EF4444')
      .text(`threshold: ${threshold}`);

    // Line
    const line = d3
      .line<(typeof data)[0]>()
      .x((d) => xScale(d.date))
      .y((d) => yScale(d.score))
      .curve(d3.curveMonotoneX);

    svg
      .append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', '#3B82F6')
      .attr('stroke-width', 2)
      .attr('d', line);

    // Dots
    svg
      .selectAll('.dot')
      .data(data)
      .join('circle')
      .attr('cx', (d) => xScale(d.date))
      .attr('cy', (d) => yScale(d.score))
      .attr('r', 3)
      .attr('fill', (d) => (d.score >= threshold ? '#EF4444' : '#3B82F6'));
  }, [alerts, threshold]);

  if (alerts.length === 0) {
    return <p className="py-4 text-center text-sm text-gray-400">No drift data</p>;
  }

  return <div ref={containerRef} className="w-full" />;
}
