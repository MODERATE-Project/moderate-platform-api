import { Text } from "@mantine/core";
import React from "react";
import { Link } from "react-router-dom";
import { NotebookContainer } from "../../components/NotebookContainer";

export const NotebookSyntheticLoad: React.FC = () => {
  return (
    <NotebookContainer
      notebookSrc="/notebook-synthetic-load"
      title={<Text fz="lg">Synthetic load model</Text>}
      description={
        <>
          <Text mt="sm" mb="sm" size="sm" color="dimmed">
            Please see the original repository for further details:{" "}
            <Link
              target="_blank"
              to="https://github.com/MODERATE-Project/Synthetic-Load-Profiles"
            >
              MODERATE-Project/Synthetic-Load-Profiles
            </Link>
          </Text>
        </>
      }
    />
  );
};
