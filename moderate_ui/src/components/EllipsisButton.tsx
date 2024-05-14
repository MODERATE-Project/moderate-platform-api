import { ActionIcon, Group, Menu } from "@mantine/core";
import { IconDotsVertical } from "@tabler/icons-react";

export function EllipsisButton({
  children,
  mainButtonProps,
}: {
  children?: React.ReactNode;
  mainButtonProps?: React.ComponentProps<typeof ActionIcon>;
}) {
  return (
    <Group noWrap spacing={0}>
      <Menu transition="pop" position="bottom-end">
        <Menu.Target>
          <ActionIcon
            color="blue"
            variant="light"
            size={36}
            {...mainButtonProps}
          >
            <IconDotsVertical size={16} />
          </ActionIcon>
        </Menu.Target>
        <Menu.Dropdown>{children}</Menu.Dropdown>
      </Menu>
    </Group>
  );
}
