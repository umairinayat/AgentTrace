import { useEffect, useRef, useState } from 'react';

/**
 * Observe an element's width and re-render the caller when it changes.
 *
 * The D3 chart components draw synchronously in an effect and read the
 * container width once; without observing resize they never redraw when the
 * viewport or layout changes. This hook exposes the live width so it can be
 * included in the drawing effect's dependency array.
 */
export function useContainerWidth<T extends HTMLElement>(): [
  React.RefObject<T>,
  number,
] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.clientWidth);
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setWidth(entry.contentRect.width);
      }
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return [ref, width];
}
