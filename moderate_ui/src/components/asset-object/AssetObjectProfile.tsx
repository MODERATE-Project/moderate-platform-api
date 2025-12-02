import { Progress, Table, createStyles } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import _ from "lodash";
import React, { useCallback } from "react";
import { AssetObjectProfileResult } from "../../api/assets";

const useStyles = createStyles(() => ({
  percentColumn: {
    minWidth: "70px",
    width: "260px",
  },
}));

interface AssetObjectProfileProps {
  profile: AssetObjectProfileResult;
}

/**
 * Component to display asset object profiling data in a table format
 * Shows column statistics including null, unique, and distinct proportions
 */
export const AssetObjectProfile: React.FC<AssetObjectProfileProps> = ({
  profile,
}) => {
  const t = useTranslate();
  const { classes } = useStyles();

  const getPercent = useCallback(
    (column: { [key: string]: any }, proportionKey: string): number => {
      const proportionVal = _.get(
        column,
        `profile.${proportionKey}`,
        undefined,
      );

      return proportionVal !== undefined ? Math.round(proportionVal * 100) : 0;
    },
    [],
  );

  return (
    <Table highlightOnHover>
      <thead>
        <tr>
          <th>{t("assetObjects.profileColumn.name", "Name")}</th>
          <th>{t("assetObjects.profileColumn.dataType", "Data type")}</th>
          <th className={classes.percentColumn}>
            {t("assetObjects.profileColumn.null", "Null")}
          </th>
          <th className={classes.percentColumn}>
            {t("assetObjects.profileColumn.unique", "Unique")}
          </th>
          <th className={classes.percentColumn}>
            {t("assetObjects.profileColumn.distinct", "Distinct")}
          </th>
        </tr>
      </thead>
      <tbody>
        {profile.profile?.columns.map((column) => (
          <tr key={column.fullyQualifiedName}>
            <td>{column.displayName}</td>
            <td>
              <code>{column.dataTypeDisplay}</code>
            </td>
            <td>
              {getPercent(column, "nullProportion")}%
              <Progress
                size="lg"
                striped
                value={getPercent(column, "nullProportion")}
              />
            </td>
            <td>
              {getPercent(column, "uniqueProportion")}%
              <Progress
                size="lg"
                striped
                value={getPercent(column, "uniqueProportion")}
              />
            </td>
            <td>
              {getPercent(column, "distinctProportion")}%
              <Progress
                size="lg"
                striped
                value={getPercent(column, "distinctProportion")}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
};
