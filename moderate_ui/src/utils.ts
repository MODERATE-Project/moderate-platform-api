import { OpenNotificationParams } from "@refinedev/core";

export function catchErrorAndShow(
  open: ((params: OpenNotificationParams) => void) | undefined,
  message: string | undefined,
  err: any
) {
  if (!open) {
    return;
  }

  open({
    message: message ?? "An error occurred",
    description: err.toString(),
    type: "error",
  });
}
