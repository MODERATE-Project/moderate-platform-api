import axios from "axios";
import { useCallback, useEffect, useState } from "react";
import { buildApiUrl } from "./utils";

export function usePing({ intervalMs }: { intervalMs?: number } = {}) {
  const [pingResult, setPingResult] = useState<object | false | undefined>(
    undefined,
  );

  const ping = useCallback(() => {
    axios
      .get(buildApiUrl("ping"))
      .then((response) => {
        setPingResult(response.data);
      })
      .catch((error) => {
        console.error(error);
        setPingResult(false);
      });
  }, []);

  useEffect(() => {
    if (!intervalMs) {
      ping();
      return;
    }

    const intervalId = setInterval(() => {
      ping();
    }, intervalMs);

    return () => clearInterval(intervalId);
  }, [intervalMs, ping]);

  return { pingResult };
}
