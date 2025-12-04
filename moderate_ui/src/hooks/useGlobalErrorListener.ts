import { showNotification } from "@mantine/notifications";
import { useEffect } from "react";

/**
 * Hook to listen for global unhandled errors and promise rejections.
 * Displays a notification when an error occurs.
 */
export function useGlobalErrorListener() {
  useEffect(() => {
    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      // Prevent the default console error if desired, currently we keep it for logging
      // event.preventDefault();

      console.error("Unhandled Promise Rejection:", event.reason);

      showNotification({
        title: "Unexpected Error",
        message: String(
          event.reason?.message || event.reason || "Unknown error occurred",
        ),
        color: "red",
        autoClose: false, // Keep open until user dismisses
      });
    };

    const handleError = (event: ErrorEvent) => {
      console.error("Global Error:", event.error);

      showNotification({
        title: "Application Error",
        message: String(event.message || "An unexpected error occurred"),
        color: "red",
        autoClose: false,
      });
    };

    window.addEventListener("unhandledrejection", handleUnhandledRejection);
    window.addEventListener("error", handleError);

    return () => {
      window.removeEventListener(
        "unhandledrejection",
        handleUnhandledRejection,
      );
      window.removeEventListener("error", handleError);
    };
  }, []);
}
