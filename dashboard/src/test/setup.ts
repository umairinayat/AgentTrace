import '@testing-library/jest-dom/vitest';

// jsdom does not implement ResizeObserver; provide a stub so components that
// observe element width can render in tests.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = ResizeObserverStub as unknown as typeof ResizeObserver;
