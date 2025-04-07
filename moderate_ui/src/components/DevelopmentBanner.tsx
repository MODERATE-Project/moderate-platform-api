import { Alert, Badge, Group, Text } from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";

const LOCAL_STORAGE_KEY = "moderate-banner-closed";

export function DevelopmentBanner() {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const isClosed = localStorage.getItem(LOCAL_STORAGE_KEY) === "true";
    setIsVisible(!isClosed);
  }, []);

  const handleClose = useCallback(() => {
    localStorage.setItem(LOCAL_STORAGE_KEY, "true");
    setIsVisible(false);
  }, []);

  if (!isVisible) {
    return null;
  }

  return (
    <Alert
      withCloseButton
      variant="light"
      onClose={handleClose}
      icon={<IconInfoCircle size={16} />}
      style={{ paddingRight: "2rem" }}
    >
      <Group>
        <Badge color="gray">MODERATE is in development</Badge>
        <Text>
          Please sign up first, then{" "}
          <a href="mailto:andres.garcia@fundacionctic.org">
            contact the MODERATE team
          </a>{" "}
          to request access approval
        </Text>
      </Group>
    </Alert>
  );
}
