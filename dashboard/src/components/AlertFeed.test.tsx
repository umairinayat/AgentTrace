import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import AlertFeed from './AlertFeed';
import type { DriftAlertResponse } from '../types';

function buildAlert(overrides: Partial<DriftAlertResponse> = {}): DriftAlertResponse {
  return {
    id: 1,
    agent_name: 'researcher',
    detected_at: '2024-01-01T00:00:00.000Z',
    alert_type: 'semantic',
    severity: 'high',
    score: 0.42,
    threshold: 0.15,
    description: 'Semantic drift detected',
    resolved: 0,
    ...overrides,
  };
}

describe('AlertFeed', () => {
  it('renders the empty state when there are no alerts', () => {
    render(<AlertFeed alerts={[]} />);
    expect(screen.getByText('No alerts')).toBeInTheDocument();
  });

  it('renders the alert type, description, and score', () => {
    render(<AlertFeed alerts={[buildAlert()]} />);
    expect(screen.getByText('semantic')).toBeInTheDocument();
    expect(screen.getByText('Semantic drift detected')).toBeInTheDocument();
    expect(screen.getByText(/Score:/)).toBeInTheDocument();
  });

  it('dims resolved alerts', () => {
    const { container } = render(<AlertFeed alerts={[buildAlert({ resolved: 1 })]} />);
    expect(container.querySelector('.opacity-50')).not.toBeNull();
  });

  it('renders each alert when given several', () => {
    render(
      <AlertFeed
        alerts={[
          buildAlert({ id: 1, alert_type: 'token' }),
          buildAlert({ id: 2, alert_type: 'latency' }),
        ]}
      />,
    );
    expect(screen.getByText('token')).toBeInTheDocument();
    expect(screen.getByText('latency')).toBeInTheDocument();
  });
});
