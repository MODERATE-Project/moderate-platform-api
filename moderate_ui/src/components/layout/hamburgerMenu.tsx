import { ActionIcon, MediaQuery } from "@mantine/core";
import { useThemedLayoutContext } from "@refinedev/mantine";
import {
  IconIndentDecrease,
  IconIndentIncrease,
  IconMenu2,
} from "@tabler/icons";
import React from "react";

export const HamburgerMenu: React.FC = () => {
  const {
    siderCollapsed,
    setSiderCollapsed,
    mobileSiderOpen,
    setMobileSiderOpen,
  } = useThemedLayoutContext();

  return (
    <>
      <MediaQuery smallerThan="md" styles={{ display: "none" }}>
        <ActionIcon
          variant="subtle"
          color="gray"
          sx={{
            border: "none",
          }}
          size="lg"
          onClick={() => setSiderCollapsed(!siderCollapsed)}
        >
          {siderCollapsed ? (
            <IconIndentIncrease size={20} />
          ) : (
            <IconIndentDecrease size={20} />
          )}
        </ActionIcon>
      </MediaQuery>
      <MediaQuery largerThan="md" styles={{ display: "none" }}>
        <ActionIcon
          variant="subtle"
          color="gray"
          sx={{
            border: "none",
          }}
          size="lg"
          onClick={() => setMobileSiderOpen(!mobileSiderOpen)}
        >
          <IconMenu2 size={20} />
        </ActionIcon>
      </MediaQuery>
    </>
  );
};
