import { Text } from "@mantine/core";
import React from "react";
import { useTranslation } from "react-i18next";
import { NotebookContainer } from "../../components/NotebookContainer";

export const NotebookExploratory: React.FC = () => {
  const { t } = useTranslation();

  return (
    <NotebookContainer
      notebookSrc="/notebook/public/exploration"
      title={
        <span>{t("notebooks.exploratory.title", "Dataset exploration")}</span>
      }
      description={
        <Text mt="sm" mb="sm" size="sm" color="dimmed">
          {t("notebooks.exploratory.description", "Explore the dataset")}
        </Text>
      }
    />
  );
};
