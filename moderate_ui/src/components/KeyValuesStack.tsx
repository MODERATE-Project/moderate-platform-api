import { Badge, Box, Stack, Text } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import _ from "lodash";
import React from "react";

const RenderedValue: React.FC<{ value: any }> = ({ value }) => {
  const translate = useTranslate();

  if (value === null || value === undefined) {
    return (
      <Badge color="gray" variant="light">
        {translate("labels.nil", "Undefined")}
      </Badge>
    );
  }

  return <span>{value.toString()}</span>;
};

const KeyValuePair: React.FC<{
  theKey: string;
  value: any;
}> = ({ theKey, value }) => {
  return (
    <Box>
      <Text fz="sm" color="dimmed">
        {_.startCase(theKey.replace(/_/g, " "))}
      </Text>
      <Text>
        <RenderedValue value={value} />
      </Text>
    </Box>
  );
};

export const KeyValuesStack: React.FC<{
  obj: { [key: string]: any };
  fields?: string[];
  omitFields?: string[];
}> = ({ obj, fields, omitFields = ["id"] }) => {
  return (
    <Stack>
      {Object.entries(obj).map(([key, value]) => {
        if (
          (fields && !fields.includes(key)) ||
          (omitFields && omitFields.includes(key))
        ) {
          return null;
        }

        return <KeyValuePair key={key} theKey={key} value={value} />;
      })}
    </Stack>
  );
};
