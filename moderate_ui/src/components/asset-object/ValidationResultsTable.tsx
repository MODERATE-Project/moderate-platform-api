import { Badge, Table, Text, Tooltip } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import React, { useMemo } from "react";
import {
  ValidationEntry,
  ValidationEntryWithStats,
  addEntryStats,
} from "../../api/validation";

interface ValidationResultsTableProps {
  entries: ValidationEntry[];
}

/**
 * Get badge color based on pass rate
 */
function getPassRateColor(passRate: number): string {
  if (passRate >= 95) return "green";
  if (passRate >= 80) return "yellow";
  return "red";
}

/**
 * Format feature name for display (remove metricValue. prefix)
 */
function formatFeatureName(feature: string): string {
  return feature.replace(/^metricValue\./, "");
}

/**
 * Get human-readable description for validation rules
 */
function getRuleDescription(
  rule: string,
  t: (key: string, defaultValue: string) => string,
): string {
  const descriptions: Record<string, string> = {
    missing: t("validation.ruleMissing", "Checks for missing/null values"),
    datatype: t("validation.ruleDatatype", "Validates data type consistency"),
    range: t(
      "validation.ruleRange",
      "Checks if values are within expected range",
    ),
    format: t("validation.ruleFormat", "Validates format/pattern compliance"),
    categorical: t(
      "validation.ruleCategorical",
      "Validates categorical values against allowed set",
    ),
    exists: t("validation.ruleExists", "Checks if required values exist"),
    regex: t(
      "validation.ruleRegex",
      "Validates against regular expression pattern",
    ),
    strlen: t("validation.ruleStrlen", "Validates string length constraints"),
    domain: t("validation.ruleDomain", "Validates domain-specific constraints"),
  };

  return descriptions[rule] || t("validation.ruleUnknown", "Validation rule");
}

/**
 * Table component for displaying validation results
 * Shows rule, feature, valid/fail counts, and pass rate
 * Sorted by pass rate (failures first)
 */
export const ValidationResultsTable: React.FC<ValidationResultsTableProps> = ({
  entries,
}) => {
  const t = useTranslate();

  // Add computed stats and sort by pass rate (lowest first)
  const sortedEntries: ValidationEntryWithStats[] = useMemo(() => {
    const withStats = addEntryStats(entries);
    return withStats.sort((a, b) => a.passRate - b.passRate);
  }, [entries]);

  if (entries.length === 0) {
    return (
      <Text color="dimmed" align="center" py="md">
        {t("validation.noResults", "No validation results available")}
      </Text>
    );
  }

  return (
    <Table striped highlightOnHover withBorder withColumnBorders>
      <thead>
        <tr>
          <th>{t("validation.rule", "Rule")}</th>
          <th>{t("validation.feature", "Feature")}</th>
          <th style={{ textAlign: "right" }}>
            {t("validation.valid", "Valid")}
          </th>
          <th style={{ textAlign: "right" }}>{t("validation.fail", "Fail")}</th>
          <th style={{ textAlign: "right" }}>
            {t("validation.total", "Total")}
          </th>
          <th style={{ textAlign: "center" }}>
            {t("validation.passRate", "Pass Rate")}
          </th>
        </tr>
      </thead>
      <tbody>
        {sortedEntries.map((entry, index) => (
          <tr key={`${entry.rule}-${entry.feature}-${index}`}>
            <td>
              <Tooltip label={getRuleDescription(entry.rule, t)}>
                <Badge variant="light" color="blue" size="sm">
                  {entry.rule}
                </Badge>
              </Tooltip>
            </td>
            <td>
              <Text size="sm" sx={{ fontFamily: "monospace" }}>
                {formatFeatureName(entry.feature)}
              </Text>
            </td>
            <td style={{ textAlign: "right" }}>
              <Text
                size="sm"
                color="green"
                weight={entry.valid > 0 ? 500 : undefined}
              >
                {entry.valid.toLocaleString()}
              </Text>
            </td>
            <td style={{ textAlign: "right" }}>
              <Text
                size="sm"
                color={entry.fail > 0 ? "red" : undefined}
                weight={entry.fail > 0 ? 500 : undefined}
              >
                {entry.fail.toLocaleString()}
              </Text>
            </td>
            <td style={{ textAlign: "right" }}>
              <Text size="sm">{entry.total.toLocaleString()}</Text>
            </td>
            <td style={{ textAlign: "center" }}>
              <Badge
                color={getPassRateColor(entry.passRate)}
                variant="filled"
                size="sm"
              >
                {entry.passRate.toFixed(2)}%
              </Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
};
