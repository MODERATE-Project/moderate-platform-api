import {
  ActionIcon,
  Badge,
  Code,
  CopyButton,
  Group,
  Paper,
  Table,
  Text,
  Tooltip,
} from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import { IconCheck, IconCopy } from "@tabler/icons-react";
import _ from "lodash";
import React from "react";
import { AssetAccessLevel } from "../api/types";

const STATUS_COLORS: Record<string, string> = {
  active: "green",
  success: "green",
  public: "green",
  visible: "cyan",
  private: "red",
  inactive: "gray",
  pending: "yellow",
  failed: "red",
  error: "red",
};

const ACCESS_LEVEL_TOOLTIPS: Record<string, string> = {
  [AssetAccessLevel.PRIVATE]: "Only you and platform admins can see this asset",
  [AssetAccessLevel.VISIBLE]:
    "Everyone can see metadata, but access requires approval",
  [AssetAccessLevel.PUBLIC]: "Everyone can see and download this asset",
};

const RenderedValue: React.FC<{ value: any; theKey: string }> = ({
  value,
  theKey,
}) => {
  const translate = useTranslate();

  if (value === null || value === undefined) {
    return (
      <Badge color="gray" variant="light" size="sm">
        {translate("labels.nil", "Undefined")}
      </Badge>
    );
  }

  // Handle Access Level specifically
  if (
    theKey === "access_level" &&
    Object.values(AssetAccessLevel).includes(value as AssetAccessLevel)
  ) {
    const tooltip = ACCESS_LEVEL_TOOLTIPS[value as string] || "Access Level";
    const color = STATUS_COLORS[value as string] || "gray";
    return (
      <Tooltip
        label={tooltip}
        withArrow
        position="top-start"
        multiline
        width={220}
      >
        <Badge color={color} variant="light" style={{ cursor: "help" }}>
          {_.upperFirst(value)}
        </Badge>
      </Tooltip>
    );
  }

  if (typeof value === "boolean") {
    return (
      <Badge color={value ? "green" : "gray"} variant="outline" size="sm">
        {value ? "Yes" : "No"}
      </Badge>
    );
  }

  if (typeof value === "object") {
    // Render object as JSON code block to avoid [object Object]
    return (
      <Code block sx={{ fontSize: "0.85em" }}>
        {JSON.stringify(value, null, 2)}
      </Code>
    );
  }

  const stringValue = value.toString();

  // Heuristic for status badges
  if (
    typeof value === "string" &&
    STATUS_COLORS[value.toLowerCase()] &&
    value.length < 20
  ) {
    return (
      <Badge color={STATUS_COLORS[value.toLowerCase()]} variant="light">
        {_.upperFirst(value)}
      </Badge>
    );
  }

  // Check if stringValue looks like a date (ISO format)
  // Simple check: starts with 20\d{2}-\d{2}-\d{2}
  if (
    typeof value === "string" &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(value)
  ) {
    // Try to format date
    try {
      const date = new Date(value);
      return <span>{date.toLocaleString()}</span>;
    } catch (e) {
      // ignore
    }
  }

  return (
    <Group spacing="xs" noWrap>
      <Text size="sm" sx={{ wordBreak: "break-word" }}>
        {stringValue}
      </Text>
      {stringValue.length > 10 && (
        <CopyButton value={stringValue} timeout={2000}>
          {({ copied, copy }) => (
            <Tooltip
              label={copied ? "Copied" : "Copy"}
              withArrow
              position="right"
            >
              <ActionIcon
                color={copied ? "teal" : "gray"}
                onClick={copy}
                size="sm"
                variant="subtle"
              >
                {copied ? <IconCheck size={14} /> : <IconCopy size={14} />}
              </ActionIcon>
            </Tooltip>
          )}
        </CopyButton>
      )}
    </Group>
  );
};

export const KeyValuesStack: React.FC<{
  obj: { [key: string]: any };
  fields?: string[];
  omitFields?: string[];
}> = ({ obj, fields, omitFields = ["id"] }) => {
  const entries = Object.entries(obj).filter(([key]) => {
    if (fields && !fields.includes(key)) {
      return false;
    }
    if (omitFields && omitFields.includes(key)) {
      return false;
    }
    return true;
  });

  if (entries.length === 0) {
    return (
      <Text color="dimmed" size="sm" fs="italic">
        No data available
      </Text>
    );
  }

  return (
    <Paper withBorder radius="md" p={0} sx={{ overflow: "hidden" }}>
      <Table verticalSpacing="sm" highlightOnHover striped fontSize="sm">
        <tbody>
          {entries.map(([key, value]) => (
            <tr key={key}>
              <td width="35%" style={{ verticalAlign: "top" }}>
                <Text weight={500} color="dimmed" size="sm">
                  {_.startCase(key.replace(/_/g, " "))}
                </Text>
              </td>
              <td style={{ verticalAlign: "top" }}>
                <RenderedValue value={value} theKey={key} />
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Paper>
  );
};
