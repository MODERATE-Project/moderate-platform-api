import { Alert, Box, Stack, Title } from "@mantine/core";
import {
  IResourceComponentsProps,
  useShow,
  useTranslate,
} from "@refinedev/core";
import { Show } from "@refinedev/mantine";
import { IconExclamationCircle } from "@tabler/icons-react";
import React from "react";
import { AssetObjectCard } from "../../components/AssetObjectCard";
import { KeyValuesStack } from "../../components/KeyValuesStack";

export const AssetShow: React.FC<IResourceComponentsProps> = () => {
  const translate = useTranslate();
  const { queryResult } = useShow();
  const { data, isLoading } = queryResult;

  const record = data?.data;

  return (
    <Show
      isLoading={isLoading}
      contentProps={{ mb: "-sm", pt: "md" }}
      title={record && <Title order={3}>{record.name}</Title>}
      goBack={null}
    >
      {record && <KeyValuesStack obj={record} omitFields={["objects", "id"]} />}
      <Title order={5} my="md">
        {translate("asset.fields.objects", "Datasets linked to this asset")}
      </Title>
      {record?.objects?.length > 0 ? (
        <Stack spacing="md">
          {record?.objects?.map(
            (object: { [key: string]: any }, index: number) => (
              <Box key={index}>
                <AssetObjectCard asset={record} assetObject={object} />
              </Box>
            )
          )}
        </Stack>
      ) : (
        <Alert
          p="xs"
          mb="sm"
          icon={<IconExclamationCircle size="1em" />}
          color="gray"
          variant="light"
        >
          {translate(
            "asset.noObjects",
            "No objects uploaded to this asset yet"
          )}
        </Alert>
      )}
    </Show>
  );
};
