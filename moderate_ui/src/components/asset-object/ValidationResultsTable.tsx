import {
  Accordion,
  Badge,
  Code,
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

interface RuleHelpItem {
  rule: string;
  label: string;
  description: string;
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
    missing: t(
      "validation.ruleMissing",
      "Checks whether field presence matches the inferred expectation",
    ),
    datatype: t(
      "validation.ruleDatatype",
      "Checks values against inferred primitive type (INTEGER/FLOAT/STRING/BOOLEAN)",
    ),
    range: t("validation.ruleRange", "Legacy alias for numeric range checks"),
    format: t("validation.ruleFormat", "Legacy alias for regex pattern checks"),
    categorical: t(
      "validation.ruleCategorical",
      "Checks values are in the allowed set inferred from the sample",
    ),
    exists: t(
      "validation.ruleExists",
      "Internal rule that feeds Missing Values checks",
    ),
    regex: t(
      "validation.ruleRegex",
      "Checks full value match against regex pattern",
    ),
    strlen: t(
      "validation.ruleStrlen",
      "Checks string length with EXACT/LOWER/UPPER comparators",
    ),
    domain: t(
      "validation.ruleDomain",
      "For numeric fields, checks values against inferred min/max domain",
    ),
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
 * Collapsible help with concise, source-of-truth explanations for each rule.
 * Stays collapsed by default to avoid taking meaningful screen space.
 */
export function DataQualityRulesHelp({
  t,
}: {
  t: (key: string, defaultValue: string) => string;
}): React.JSX.Element {
  const helpItems: RuleHelpItem[] = [
    {
      rule: "missing",
      label: getRuleLabel("missing"),
      description: t(
        "validation.helpMissing",
        "Generated from an internal exists rule. It checks whether each column is present (or absent) as expected from sampled data.",
      ),
    },
    {
      rule: "datatype",
      label: getRuleLabel("datatype"),
      description: t(
        "validation.helpDatatype",
        "Validates values against the inferred main type for that column. Numeric strings may be accepted when permissive numeric checks are enabled.",
      ),
    },
    {
      rule: "domain",
      label: getRuleLabel("domain"),
      description: t(
        "validation.helpDomain",
        "Numeric min/max range inferred from sampled data. In permissive mode, the observed range is widened to reduce brittle failures.",
      ),
    },
    {
      rule: "categorical",
      label: getRuleLabel("categorical"),
      description: t(
        "validation.helpCategorical",
        "Restricts values to an allowed set inferred for low-cardinality columns.",
      ),
    },
    {
      rule: "regex",
      label: getRuleLabel("regex"),
      description: t(
        "validation.helpRegex",
        "Enforces full-string pattern matching when a stable format can be derived (or configured).",
      ),
    },
    {
      rule: "strlen",
      label: getRuleLabel("strlen"),
      description: t(
        "validation.helpStrlen",
        "Checks string length constraints using EXACT, LOWER, or UPPER comparison modes.",
      ),
    },
  ];

  return (
    <Accordion variant="contained" radius="md">
      <Accordion.Item value="rule-help">
        <Accordion.Control>
          <Group position="apart" noWrap>
            <Text size="sm" weight={600}>
              {t("validation.helpTitle", "How to read Data Quality rules")}
            </Text>
            <Badge size="xs" variant="light" color="blue">
              {t("validation.helpQuickGuide", "Quick guide")}
            </Badge>
          </Group>
        </Accordion.Control>
        <Accordion.Panel>
          <Stack spacing="sm">
            <Text size="xs" color="dimmed">
              {t(
                "validation.helpIntro",
                "Rules are inferred from sampled rows and then applied to processed rows. Pass rate = valid / (valid + failed).",
              )}
            </Text>
            <Stack spacing={8}>
              {helpItems.map((item) => (
                <div key={item.rule}>
                  <Group spacing={6} mb={2}>
                    <Text size="sm" weight={600}>
                      {item.label}
                    </Text>
                    <Code>{item.rule}</Code>
                  </Group>
                  <Text size="sm" color="dimmed">
                    {item.description}
                  </Text>
                </div>
              ))}
            </Stack>
          </Stack>
        </Accordion.Panel>
      </Accordion.Item>
    </Accordion>
  );
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
