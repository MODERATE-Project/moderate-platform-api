import { LoadingOverlay } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import React from "react";

export const Catalogue: React.FC = () => {
  const translate = useTranslate();

  return (
    <>
      <LoadingOverlay visible={false} overlayBlur={2} />
      <div>This is the catalogue page.</div>
    </>
  );
};
