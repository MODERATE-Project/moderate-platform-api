import { ActionIcon } from "@mantine/core";
import { IconChevronDown, IconChevronUp, IconSelector } from "@tabler/icons";
import type { Column } from "@tanstack/react-table";

export const ColumnSorter: React.FC<{ column: Column<any, any> }> = ({
  column,
}) => {
  if (!column.getCanSort()) {
    return null;
  }

  const sorted = column.getIsSorted();

  return (
    <ActionIcon
      size="xs"
      variant="light"
      display="inline-flex"
      onClick={column.getToggleSortingHandler()}
    >
      {!sorted && <IconSelector />}
      {sorted === "asc" && <IconChevronDown />}
      {sorted === "desc" && <IconChevronUp />}
    </ActionIcon>
  );
};
