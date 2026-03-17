import type { DriftAlertResponse } from '../types';

const severityColors: Record<string, string> = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-yellow-100 text-yellow-800',
  low: 'bg-blue-100 text-blue-800',
};

interface Props {
  alerts: DriftAlertResponse[];
}

export default function AlertFeed({ alerts }: Props) {
  if (alerts.length === 0) {
    return <p className="py-4 text-center text-sm text-gray-400">No alerts</p>;
  }

  return (
    <div className="space-y-2">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className={`rounded-lg border p-3 ${alert.resolved ? 'opacity-50' : ''}`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  severityColors[alert.severity] || 'bg-gray-100 text-gray-600'
                }`}
              >
                {alert.severity}
              </span>
              <span className="text-sm font-medium">{alert.alert_type.replace(/_/g, ' ')}</span>
            </div>
            <span className="text-xs text-gray-400">
              {new Date(alert.detected_at).toLocaleString()}
            </span>
          </div>
          {alert.description && (
            <p className="mt-1 text-xs text-gray-600">{alert.description}</p>
          )}
          {alert.score != null && (
            <p className="mt-1 text-xs text-gray-500">
              Score: {alert.score.toFixed(4)}
              {alert.threshold != null ? ` / Threshold: ${alert.threshold}` : ''}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
