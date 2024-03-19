import {
  Alert,
  Box,
  Card,
  Code,
  Col,
  Grid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import {
  IResourceComponentsProps,
  useShow,
  useTranslate,
} from "@refinedev/core";
import { Show, TextField } from "@refinedev/mantine";
import { IconBulb, IconExclamationCircle } from "@tabler/icons";
import React from "react";
import { AssetObjectCard } from "../../components/AssetObjectCard";

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
      <Grid gutter="md">
        <Col md={6}>
          <Card p={0}>
            <Title order={5} color="dimmed" fw={300}>
              {translate("asset.fields.name")}
            </Title>
            <Text>
              <TextField value={record?.name} />
            </Text>
          </Card>
        </Col>
        <Col md={6}>
          <Card p={0}>
            <Title order={5} color="dimmed" fw={300}>
              {translate("asset.fields.uuid")}
            </Title>
            <Text>
              <Code>{record?.uuid}</Code>
            </Text>
          </Card>
        </Col>
        <Col md={6}>
          <Card p={0}>
            <Title order={5} color="dimmed" fw={300}>
              {translate("asset.fields.access_level")}
            </Title>
            <Text>
              <TextField value={record?.access_level} />
            </Text>
          </Card>
        </Col>
      </Grid>
      <Title order={5} color="dimmed" fw={300} my="md">
        {translate("asset.fields.objects")}
      </Title>
      <Alert
        p="xs"
        mb="sm"
        icon={<IconBulb size="1em" />}
        color="violet"
        variant="light"
      >
        <Box
          dangerouslySetInnerHTML={{
            __html: translate("assetObject.aboutDescription"),
          }}
        ></Box>
      </Alert>
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
          variant="outline"
        >
          {translate("asset.noObjects")}
        </Alert>
      )}
    </Show>
  );
};
