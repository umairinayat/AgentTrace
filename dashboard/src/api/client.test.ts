import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from './client';

describe('api client', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mockFetch(response: unknown, ok = true): ReturnType<typeof vi.fn> {
    const fetchMock = vi.fn();
    fetchMock.mockResolvedValue({
      ok,
      status: ok ? 200 : 500,
      statusText: ok ? 'OK' : 'Internal Server Error',
      json: async () => response,
    });
    globalThis.fetch = fetchMock as unknown as typeof fetch;
    return fetchMock;
  }

  it('encodes trace filters into query params', async () => {
    const fetchMock = mockFetch({ items: [], total: 0, page: 1, page_size: 50, pages: 1 });
    await api.getTraces({
      page: 1,
      page_size: 50,
      sort_by: 'started_at',
      sort_order: 'desc',
      agent_name: 'alpha-bot',
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain('/api/v1/traces');
    expect(url).toContain('agent_name=alpha-bot');
    expect(url).toContain('sort_by=started_at');
  });

  it('includes the agent_name query for drift alerts when provided', async () => {
    const fetchMock = mockFetch([]);
    await api.getDriftAlerts('agent-a');
    expect(String(fetchMock.mock.calls[0][0])).toContain('agent_name=agent-a');
  });

  it('omits the agent_name query for drift alerts when not provided', async () => {
    const fetchMock = mockFetch([]);
    await api.getDriftAlerts();
    expect(String(fetchMock.mock.calls[0][0])).not.toContain('agent_name');
  });

  it('throws on a non-ok response', async () => {
    mockFetch({}, false);
    await expect(api.getStats()).rejects.toThrow('API error');
  });

  it('posts JSON for rebuildBaseline', async () => {
    const fetchMock = mockFetch({ status: 'ok' });
    await api.rebuildBaseline('agent-a');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0];
    expect(init).toMatchObject({ method: 'POST' });
  });
});
