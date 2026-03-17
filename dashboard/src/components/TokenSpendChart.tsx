import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface DataPoint {
  date: string;
  tokens: number;
  cost: number;
}

interface TokenSpendChartProps {
  data: DataPoint[];
}

export default function TokenSpendChart({ data }: TokenSpendChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || data.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = { top: 20, right: 60, bottom: 40, left: 60 };
    const width = svgRef.current.clientWidth - margin.left - margin.right;
    const height = 240 - margin.top - margin.bottom;

    const g = svg
      .attr('width', width + margin.left + margin.right)
      .attr('height', height + margin.top + margin.bottom)
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const parseDate = d3.timeParse('%Y-%m-%d');
    const parsed = data.map((d) => ({
      date: parseDate(d.date) || new Date(d.date),
      tokens: d.tokens,
      cost: d.cost,
    }));

    const x = d3
      .scaleTime()
      .domain(d3.extent(parsed, (d) => d.date) as [Date, Date])
      .range([0, width]);

    const yTokens = d3
      .scaleLinear()
      .domain([0, d3.max(parsed, (d) => d.tokens) || 1])
      .nice()
      .range([height, 0]);

    const yCost = d3
      .scaleLinear()
      .domain([0, d3.max(parsed, (d) => d.cost) || 0.01])
      .nice()
      .range([height, 0]);

    // Axes
    g.append('g')
      .attr('transform', `translate(0,${height})`)
      .call(d3.axisBottom(x).ticks(6).tickFormat(d3.timeFormat('%b %d') as any))
      .selectAll('text')
      .attr('fill', '#6B7280')
      .style('font-size', '10px');

    g.append('g')
      .call(d3.axisLeft(yTokens).ticks(5).tickFormat(d3.format('.2s')))
      .selectAll('text')
      .attr('fill', '#3B82F6')
      .style('font-size', '10px');

    g.append('g')
      .attr('transform', `translate(${width},0)`)
      .call(d3.axisRight(yCost).ticks(5).tickFormat((d) => `$${d3.format('.2f')(d as number)}`))
      .selectAll('text')
      .attr('fill', '#10B981')
      .style('font-size', '10px');

    // Token line
    const tokenLine = d3
      .line<(typeof parsed)[0]>()
      .x((d) => x(d.date))
      .y((d) => yTokens(d.tokens))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(parsed)
      .attr('fill', 'none')
      .attr('stroke', '#3B82F6')
      .attr('stroke-width', 2)
      .attr('d', tokenLine);

    // Cost line
    const costLine = d3
      .line<(typeof parsed)[0]>()
      .x((d) => x(d.date))
      .y((d) => yCost(d.cost))
      .curve(d3.curveMonotoneX);

    g.append('path')
      .datum(parsed)
      .attr('fill', 'none')
      .attr('stroke', '#10B981')
      .attr('stroke-width', 2)
      .attr('stroke-dasharray', '4,2')
      .attr('d', costLine);

    // Legend
    const legend = g.append('g').attr('transform', `translate(${width - 140}, -5)`);
    legend.append('line').attr('x1', 0).attr('x2', 16).attr('y1', 0).attr('y2', 0).attr('stroke', '#3B82F6').attr('stroke-width', 2);
    legend.append('text').attr('x', 20).attr('y', 4).text('Tokens').attr('fill', '#6B7280').style('font-size', '10px');
    legend.append('line').attr('x1', 70).attr('x2', 86).attr('y1', 0).attr('y2', 0).attr('stroke', '#10B981').attr('stroke-width', 2).attr('stroke-dasharray', '4,2');
    legend.append('text').attr('x', 90).attr('y', 4).text('Cost').attr('fill', '#6B7280').style('font-size', '10px');

    // Dots
    g.selectAll('.token-dot')
      .data(parsed)
      .enter()
      .append('circle')
      .attr('cx', (d) => x(d.date))
      .attr('cy', (d) => yTokens(d.tokens))
      .attr('r', 3)
      .attr('fill', '#3B82F6');
  }, [data]);

  return (
    <div className="rounded-lg border bg-white p-4 shadow-sm">
      <h3 className="mb-3 text-sm font-semibold text-gray-700">Daily Token Spend</h3>
      <svg ref={svgRef} className="w-full" style={{ minHeight: 240 }} />
    </div>
  );
}
