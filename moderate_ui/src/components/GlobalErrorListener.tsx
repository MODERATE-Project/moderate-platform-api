import { useGlobalErrorListener } from "../hooks/useGlobalErrorListener";

/**
 * Component that activates the global error listener hook.
 * Should be placed inside the NotificationsProvider.
 */
export const GlobalErrorListener = () => {
  useGlobalErrorListener();
  return null;
};
