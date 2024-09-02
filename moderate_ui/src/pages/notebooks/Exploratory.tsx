import { Text } from "@mantine/core";
import React from "react";
import { NotebookContainer } from "../../components/NotebookContainer";

export const NotebookExploratory: React.FC = () => {
  return (
    <NotebookContainer
      notebookSrc="/notebook/public/exploration"
      title={
        <Text fz="lg" color="purple">
          Data exploration
        </Text>
      }
      description={
        <>
          <Text mt="sm" mb="sm" size="sm">
            This notebook allows you to download and visualize one of the
            datasets you have access to, loading it into a DataFrame so that you
            can leverage the native Marimo tools for DataFrame visualization in
            your data exploration.
          </Text>
          <Text mt="sm" mb="sm" size="sm">
            You can copy the download URL of a dataset you have access to and
            paste it into the form below. The notebook will then download the
            dataset and display the visualization components.
          </Text>
        </>
      }
    />
  );
};
