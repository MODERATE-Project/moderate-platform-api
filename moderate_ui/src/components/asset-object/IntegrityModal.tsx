import { Alert, Code, Modal, Text, Title } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import { IconAlertCircle, IconCheck } from "@tabler/icons-react";
import React from "react";
import { AssetObjectIntegrityResponse } from "../../api/assets";

interface IntegrityModalProps {
  opened: boolean;
  close: () => void;
  integrityResult: AssetObjectIntegrityResponse;
}

/**
 * Modal component displaying cryptographic integrity check results
 */
export const IntegrityModal: React.FC<IntegrityModalProps> = ({
  opened,
  close,
  integrityResult,
}) => {
  const t = useTranslate();

  const defaultBodyOk = `
    This dataset has passed the integrity check,
    so there's a high degree of confidence that it has not been tampered with
    and is the same version that was originally uploaded.`;

  const defaultBodyFailed = `
    This dataset has failed the integrity check.
    This does not necessarily mean that the dataset has been compromised;
    it could also be that the cryptographic proof has not yet been created on the DLT.
    Please wait a few minutes.
    In any case, you should operate under the assumption that the dataset has been tampered with.
    Please see the error message below for more details:`;

  return (
    <Modal
      opened={opened}
      onClose={close}
      size="lg"
      title={
        <Title order={5}>
          {t("assetObjects.integrityCheck", "Cryptographic integrity check")}
        </Title>
      }
    >
      {!!integrityResult && (
        <Alert
          icon={integrityResult.valid ? <IconCheck /> : <IconAlertCircle />}
          color={integrityResult.valid ? "green" : "red"}
          title={
            integrityResult.valid
              ? t(
                  "assetObjects.integrityTitleOk",
                  "All good: integrity check successful",
                )
              : t("assetObjects.integrityTitleFailed", "Integrity check failed")
          }
        >
          {integrityResult.valid ? (
            <Text>{t("assetObjects.integrityBodyOk", defaultBodyOk)}</Text>
          ) : (
            <>
              <Text mb="md">
                {t("assetObjects.integrityBodyFailed", defaultBodyFailed)}
              </Text>
              <Code>{integrityResult.reason}</Code>
            </>
          )}
        </Alert>
      )}
    </Modal>
  );
};
