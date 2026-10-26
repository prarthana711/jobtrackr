import { useCallback, useEffect, useRef, useState } from "react";

// Loads data whenever `key` changes. Call reload() to fetch again.
//
//   const { data, error, loading, reload } = useQuery("resumes", () => api.listResumes());
//
// Like the jobs page, it never stores "loading": it works it out by checking whether
// the latest result belongs to the current request. While a new request is running,
// the previous data stays available, so the screen doesn't flash empty.
export function useQuery(key, fetcher) {
  const [reloadCount, setReloadCount] = useState(0);
  const [result, setResult] = useState({ key: null, data: null, error: "" });
  const fetcherRef = useRef(fetcher);
  const requestKey = `${key}|${reloadCount}`;

  // Always remember the newest fetcher function, without re-running the fetch for it
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  useEffect(() => {
    let ignore = false; // becomes true if this request is outdated
    fetcherRef
      .current()
      .then((data) => {
        if (!ignore) setResult({ key: requestKey, data, error: "" });
      })
      .catch((err) => {
        if (!ignore) {
          setResult((previous) => ({ key: requestKey, data: previous.data, error: err.message }));
        }
      });
    return () => {
      ignore = true;
    };
  }, [requestKey]);

  const reload = useCallback(() => setReloadCount((count) => count + 1), []);
  const loading = result.key !== requestKey;

  return { data: result.data, error: loading ? "" : result.error, loading, reload };
}