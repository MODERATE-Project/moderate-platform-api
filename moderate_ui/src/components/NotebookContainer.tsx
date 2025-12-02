import { Card } from "@mantine/core";
import axios from "axios";
import React, { ReactElement, useCallback, useEffect, useRef } from "react";
import { buildApiUrl } from "../api/utils";

export const NotebookContainer: React.FC<{
  title: ReactElement;
  description: ReactElement;
  notebookSrc: string;
  iframeResizeIntervalMs?: number;
}> = ({ title, description, notebookSrc, iframeResizeIntervalMs = 500 }) => {
  const [pingResult, setPingResult] = React.useState<boolean | undefined>(
    undefined,
  );

  const [frameHeight, setFrameHeight] = React.useState<string>("100vh");
  const iframeRef = useRef(null);

  const pingCallback = useCallback(() => {
    axios
      .get(buildApiUrl("ping"))
      .then(() => {
        setPingResult(true);
      })
      .catch(() => {
        setPingResult(false);
      });
  }, []);

  useEffect(pingCallback, [pingCallback]);

  const resizeCallback = useCallback(() => {
    if (!iframeRef?.current) {
      return;
    }

    const iframeDocument =
      (iframeRef.current as HTMLIFrameElement).contentDocument ||
      (iframeRef.current as HTMLIFrameElement).contentWindow?.document;

    if (iframeDocument) {
      setFrameHeight(`${iframeDocument.documentElement.scrollHeight}px`);
    }
  }, []);

  useEffect(() => {
    const intervalId = setInterval(resizeCallback, iframeResizeIntervalMs);
    return () => clearInterval(intervalId);
  }, [resizeCallback, iframeResizeIntervalMs]);

  return (
    <Card withBorder shadow="sm" radius="md">
      <Card.Section withBorder inheritPadding py="xs">
        {title}
      </Card.Section>

      {description}

      {pingResult === true && (
        <Card.Section withBorder>
          <iframe
            ref={iframeRef}
            src={notebookSrc}
            style={{ width: "100%", height: frameHeight, border: "none" }}
          />
        </Card.Section>
      )}
    </Card>
  );
};
