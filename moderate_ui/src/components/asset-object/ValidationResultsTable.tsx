import {
  Badge,
  Divider,
  Group,
  Paper,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  Tooltip,
} from "@mantine/core";
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

interface FeatureGroup {
  feature: string;
  entries: ValidationEntryWithStats[];
  worstPassRate: number;
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
 * Get user-friendly label for validation rule enum values
 */
function getRuleLabel(rule: string): string {
  const labels: Record<string, string> = {
    missing: "Missing Values",
    datatype: "Data Type",
    range: "Range",
    format: "Format",
    categorical: "Categorical",
    exists: "Exists",
    regex: "Regex Pattern",
    strlen: "String Length",
    domain: "Domain",
  };
  return labels[rule] ?? rule;
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
 * Map a pass rate to a short severity label
 */
function getSeverityLabel(passRate: number): string {
  if (passRate >= 99) return "Excellent";
  if (passRate >= 95) return "Good";
  if (passRate >= 80) return "Fair";
  return "Poor";
}

/**
 * Group flat validation entries by feature (column), computing the worst
 * pass rate for each group so cards can be sorted by severity.
 */
function groupByFeature(entries: ValidationEntryWithStats[]): FeatureGroup[] {
  const groups = new Map<string, ValidationEntryWithStats[]>();

  for (const entry of entries) {
    const key = entry.feature;
    const current = groups.get(key);
    if (current) {
      current.push(entry);
      continue;
    }
    groups.set(key, [entry]);
  }

  return Array.from(groups.entries())
    .map(([feature, groupEntries]) => ({
      feature,
      entries: groupEntries.sort((a, b) => a.passRate - b.passRate),
      worstPassRate: Math.min(...groupEntries.map((e) => e.passRate)),
    }))
    .sort((a, b) => a.worstPassRate - b.worstPassRate);
}

/**
 * Card-grid component for displaying validation results grouped by feature.
 * One card per data column; within each card, rules are listed with a
 * progress bar. Cards are sorted by severity (most problematic first).
 */
export const ValidationResultsTable: React.FC<ValidationResultsTableProps> = ({
  entries,
}) => {
  const t = useTranslate();

  const featureGroups: FeatureGroup[] = useMemo(
    () => groupByFeature(addEntryStats(entries)),
    [entries],
  );

  if (entries.length === 0) {
    return (
      <Text color="dimmed" align="center" py="md">
        {t("validation.noResults", "No validation results available")}
      </Text>
    );
  }

  return (
    <SimpleGrid
      cols={3}
      breakpoints={[
        { maxWidth: "md", cols: 2 },
        { maxWidth: "sm", cols: 1 },
      ]}
    >
      {featureGroups.map(
        ({ feature, entries: groupEntries, worstPassRate }) => (
          <Paper key={feature} p="md" withBorder>
            <Stack spacing="sm">
              {/* Card header: column name + overall severity */}
              <Group position="apart" align="flex-start" noWrap>
                <Text
                  size="sm"
                  weight={600}
                  sx={{ fontFamily: "monospace", wordBreak: "break-all" }}
                >
                  {formatFeatureName(feature)}
                </Text>
                <Badge
                  color={getPassRateColor(worstPassRate)}
                  variant="filled"
                  size="sm"
                  sx={{ flexShrink: 0 }}
                >
                  {getSeverityLabel(worstPassRate)}
                </Badge>
              </Group>

              <Divider />

              {/* Rule breakdown */}
              <Stack spacing="xs">
                {groupEntries.map((entry, index) => (
                  <div key={`${entry.rule}-${entry.feature}-${index}`}>
                    <Group position="apart" mb={4}>
                      <Tooltip label={getRuleDescription(entry.rule, t)}>
                        <Text size="xs" color="dimmed">
                          {getRuleLabel(entry.rule)}
                        </Text>
                      </Tooltip>
                      <Text
                        size="xs"
                        weight={500}
                        color={getPassRateColor(entry.passRate)}
                      >
                        {entry.passRate.toFixed(1)}%
                      </Text>
                    </Group>
                    <Progress
                      value={entry.passRate}
                      color={getPassRateColor(entry.passRate)}
                      size="sm"
                    />
                  </div>
                ))}
              </Stack>
            </Stack>
          </Paper>
        ),
      )}
    </SimpleGrid>
  );
};
