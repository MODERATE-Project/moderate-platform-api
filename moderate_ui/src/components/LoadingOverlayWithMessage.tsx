import { Loader, LoadingOverlay, Stack, Text } from "@mantine/core";
import React from "react";

export interface LoadingOverlayWithMessageProps {
  visible: boolean;
  message: string;
  loaderSize?: "xs" | "sm" | "md" | "lg" | "xl";
  overlayBlur?: number;
}

/**
 * Loading overlay with a custom message displayed below the loader
 * Provides a consistent loading UX across the application
 */
export const LoadingOverlayWithMessage: React.FC<
  LoadingOverlayWithMessageProps
> = ({ visible, message, loaderSize = "xl", overlayBlur = 2 }) => (
  <LoadingOverlay
    visible={visible}
    overlayBlur={overlayBlur}
    loader={
      <Stack justify="center" align="center">
        <Loader size={loaderSize} />
        <Text color="dimmed">{message}</Text>
      </Stack>
    }
  />
);
