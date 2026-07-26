import { useState } from 'react';
import { api } from '../api/client';

export default function Settings() {
  const [collectorUrl, setCollectorUrl] = useState(
    import.meta.env.VITE_COLLECTOR_URL || 'http://localhost:8000',
  );
  const [healthStatus, setHealthStatus] = useState<string | null>(null);
  const [slackWebhook, setSlackWebhook] = useState('');
  const [discordWebhook, setDiscordWebhook] = useState('');
  const [customWebhook, setCustomWebhook] = useState('');
  const [retention, setRetention] = useState('30');
  const [deleteConfirm, setDeleteConfirm] = useState('');

  async function testConnection() {
    setHealthStatus('testing...');
    try {
      const res = await api.healthCheck();
      setHealthStatus(res.status === 'ok' ? 'Connected' : `Status: ${res.status}`);
    } catch (e) {
      setHealthStatus(`Failed: ${(e as Error).message}`);
    }
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="mb-6 text-2xl font-bold">Settings</h1>

      {/* Collector URL */}
      <Section title="Collector Connection">
        <label className="mb-1 block text-xs text-gray-500">Collector URL</label>
        <div className="flex gap-2">
          <input
            id="collector-url"
            type="text"
            className="flex-1 rounded border px-3 py-2 text-sm focus:border-primary focus:outline-none"
            placeholder="http://localhost:8000"
            title="Enter the URL of the Collector service"
            value={collectorUrl}
            onChange={(e) => setCollectorUrl(e.target.value)}
          />
          <button
            className="rounded bg-primary px-4 py-2 text-sm text-white hover:bg-blue-600"
            onClick={testConnection}
          >
            Test
          </button>
        </div>
        {healthStatus && (
          <p
            className={`mt-2 text-sm ${
              healthStatus === 'Connected' ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {healthStatus}
          </p>
        )}
      </Section>

      {/* Alert Webhooks */}
      <Section
        title="Alert Webhooks"
        note="Alert channels are configured via environment variables on the drift-detector service (SLACK_WEBHOOK_URL, DISCORD_WEBHOOK_URL, CUSTOM_WEBHOOK_URL, SMTP_*). Editing from the dashboard is coming soon."
      >
        <label className="mb-1 block text-xs text-gray-500">Slack Webhook URL</label>
        <input
          type="text"
          className="mb-3 w-full rounded border px-3 py-2 text-sm focus:border-primary focus:outline-none"
          placeholder="https://hooks.slack.com/services/..."
          value={slackWebhook}
          onChange={(e) => setSlackWebhook(e.target.value)}
        />
        <label className="mb-1 block text-xs text-gray-500">Discord Webhook URL</label>
        <input
          type="text"
          className="mb-3 w-full rounded border px-3 py-2 text-sm focus:border-primary focus:outline-none"
          placeholder="https://discord.com/api/webhooks/..."
          value={discordWebhook}
          onChange={(e) => setDiscordWebhook(e.target.value)}
        />
        <label className="mb-1 block text-xs text-gray-500">Custom Webhook URL</label>
        <input
          type="text"
          className="w-full rounded border px-3 py-2 text-sm focus:border-primary focus:outline-none"
          placeholder="https://your-webhook.example.com/..."
          value={customWebhook}
          onChange={(e) => setCustomWebhook(e.target.value)}
        />
      </Section>

      {/* Retention */}
      <Section title="Data Retention" note="Automatic retention enforcement is coming soon.">
        <label className="mb-1 block text-xs text-gray-500" htmlFor="retention-period">
          Auto-delete traces older than
        </label>
        <select
          id="retention-period"
          className="rounded border px-3 py-2 text-sm focus:border-primary focus:outline-none"
          value={retention}
          onChange={(e) => setRetention(e.target.value)}
        >
          <option value="7">7 days</option>
          <option value="14">14 days</option>
          <option value="30">30 days</option>
          <option value="60">60 days</option>
          <option value="90">90 days</option>
          <option value="never">Never</option>
        </select>
      </Section>

      {/* Danger Zone */}
      <Section
        title="Danger Zone"
        danger
        note="Bulk trace deletion from the dashboard is coming soon. Until then, clear traces by removing the collector's database volume."
      >
        <p className="mb-3 text-sm text-gray-600">
          Type <code className="rounded bg-red-50 px-1 text-red-600">DELETE</code> to confirm
          deleting all traces.
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 rounded border border-red-300 px-3 py-2 text-sm focus:border-red-500 focus:outline-none"
            placeholder='Type "DELETE" to confirm'
            value={deleteConfirm}
            onChange={(e) => setDeleteConfirm(e.target.value)}
          />
          <button
            className="rounded bg-red-600 px-4 py-2 text-sm text-white hover:bg-red-700 disabled:opacity-40"
            disabled={deleteConfirm !== 'DELETE'}
          >
            Delete All Traces
          </button>
        </div>
      </Section>
    </div>
  );
}

function Section({
  title,
  danger,
  note,
  children,
}: {
  title: string;
  danger?: boolean;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`mb-6 rounded-lg border p-4 ${
        danger ? 'border-red-200 bg-red-50' : 'bg-white'
      }`}
    >
      <h2 className={`mb-1 text-sm font-semibold ${danger ? 'text-red-700' : 'text-gray-700'}`}>
        {title}
      </h2>
      {note && <p className="mb-3 text-xs text-gray-400">{note}</p>}
      {children}
    </div>
  );
}
