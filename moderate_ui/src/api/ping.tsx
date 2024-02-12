import axios from "axios";
import { useEffect, useState } from "react";
import { buildApiUrl } from "./utils";

export function usePing() {
  const [pingResult, setPingResult] = useState<object | false | undefined>(
    undefined
  );

  useEffect(() => {
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

  return { pingResult };
}
