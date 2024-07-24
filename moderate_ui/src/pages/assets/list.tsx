import { Group, Pagination, ScrollArea, Space, Table } from "@mantine/core";
import { IResourceComponentsProps, useTranslate } from "@refinedev/core";
import { DeleteButton, EditButton, List, ShowButton } from "@refinedev/mantine";
import { useTable } from "@refinedev/react-table";
import { ColumnDef, flexRender } from "@tanstack/react-table";
import React from "react";
import { ColumnFilter } from "../../components/table/ColumnFilter";
import { ColumnSorter } from "../../components/table/ColumnSorter";

export const AssetList: React.FC<IResourceComponentsProps> = () => {
  const translate = useTranslate();

  const columns = React.useMemo<ColumnDef<any>[]>(
    () => [
      {
        id: "name",
        accessorKey: "name",
        header: translate("asset.fields.name", "Name"),
        meta: {
          filterOperator: "contains",
        },
      },
      {
        id: "access_level",
        accessorKey: "access_level",
        header: translate("asset.fields.access_level", "Access Level"),
        meta: {
          filterOperator: "contains",
        },
      },
      {
        id: "numObjects",
        accessorKey: "objects",
        header: translate("asset.fields.num_objects", "Number of Datasets"),
        enableSorting: false,
        enableColumnFilter: false,
        cell: function render({ getValue }) {
          return getValue() ? (getValue() as unknown as any).length : 0;
        },
      },
      {
        id: "created_at",
        accessorKey: "created_at",
        enableColumnFilter: false,
        header: translate("asset.fields.created_at", "Date of Creation"),
        meta: {
          filterOperator: "contains",
        },
        cell: function render({ getValue }) {
          return new Date(getValue() as string).toLocaleString();
        },
      },
      {
        id: "actions",
        accessorKey: "id",
        header: translate("table.actions"),
        enableSorting: false,
        enableColumnFilter: false,
        cell: function render({ getValue }) {
          return (
            <Group spacing="xs" noWrap>
              <ShowButton hideText recordItemId={getValue() as string} />
              <EditButton hideText recordItemId={getValue() as string} />
              <DeleteButton hideText recordItemId={getValue() as string} />
            </Group>
          );
        },
      },
    ],
    [translate]
  );

  const {
    getHeaderGroups,
    getRowModel,
    setOptions,
    refineCore: {
      setCurrent,
      pageCount,
      current,
      tableQueryResult: { data: tableData },
    },
  } = useTable({
    columns,
  });

  setOptions((prev) => ({
    ...prev,
    meta: {
      ...prev.meta,
    },
  }));

  return (
    <>
      <List>
        <ScrollArea>
          <Table highlightOnHover>
            <thead>
              {getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => {
                    return (
                      <th key={header.id}>
                        <div style={{ display: "flex" }}>
                          <ColumnSorter column={header.column} />
                          <Space w="xs" />
                          <ColumnFilter column={header.column} />
                          <Space w="xs" />
                          {!header.isPlaceholder &&
                            flexRender(
                              header.column.columnDef.header,
                              header.getContext()
                            )}
                        </div>
                      </th>
                    );
                  })}
                </tr>
              ))}
            </thead>
            <tbody>
              {getRowModel().rows.map((row) => {
                return (
                  <tr key={row.id}>
                    {row.getVisibleCells().map((cell) => {
                      return (
                        <td key={cell.id}>
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext()
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </Table>
        </ScrollArea>
        <br />
        <Pagination
          position="right"
          total={pageCount}
          page={current}
          onChange={setCurrent}
        />
      </List>
    </>
  );
};
