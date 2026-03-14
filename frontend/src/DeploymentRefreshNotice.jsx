import { useEffect, useRef, useState } from "react";

const POLL_INTERVAL_MS = 60000;

function collectAssetSignature(doc) {
  return [...doc.querySelectorAll("script[type='module'][src], link[rel='modulepreload'][href], link[rel='stylesheet'][href]")]
    .map((node) => node.getAttribute("src") || node.getAttribute("href") || "")
    .filter(Boolean)
    .map((value) => {
      try {
        return new URL(value, window.location.origin).pathname;
      } catch {
        return value;
      }
    })
    .sort()
    .join("|");
}

async function fetchLatestAssetSignature(signal) {
  const response = await fetch(new URL("index.html", window.location.href), {
    cache: "no-store",
    headers: {
      "Cache-Control": "no-cache",
    },
    signal,
  });

  if (!response.ok) {
    throw new Error(`Unable to check deployment status (${response.status})`);
  }

  const html = await response.text();
  const parsed = new DOMParser().parseFromString(html, "text/html");
  return collectAssetSignature(parsed);
}

export default function DeploymentRefreshNotice() {
  const [showNotice, setShowNotice] = useState(false);
  const currentSignatureRef = useRef(collectAssetSignature(document));

  useEffect(() => {
    let isMounted = true;
    let activeController = null;

    async function checkForUpdate() {
      activeController?.abort();
      const controller = new AbortController();
      activeController = controller;

      try {
        const latestSignature = await fetchLatestAssetSignature(controller.signal);
        if (!isMounted || !latestSignature) {
          return;
        }

        if (!currentSignatureRef.current) {
          currentSignatureRef.current = latestSignature;
          return;
        }

        setShowNotice(latestSignature !== currentSignatureRef.current);
      } catch {
        // Ignore transient network or cache errors and retry on the next poll.
      }
    }

    checkForUpdate();
    const intervalId = window.setInterval(checkForUpdate, POLL_INTERVAL_MS);

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        checkForUpdate();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      isMounted = false;
      activeController?.abort();
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  if (!showNotice) {
    return null;
  }

  return (
    <button
      type="button"
      className="deployment-refresh"
      onClick={() => window.location.reload()}
      aria-live="polite"
    >
      <strong>Update available</strong>
      <span>Refresh to load the latest deployment.</span>
    </button>
  );
}
