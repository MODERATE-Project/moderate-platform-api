import {
  Alert,
  Badge,
  Box,
  Button,
  Card,
  Grid,
  Group,
  LoadingOverlay,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useNotification } from "@refinedev/core";
import {
  IconBox,
  IconClock,
  IconDatabaseSearch,
  IconExternalLink,
  IconLockAccess,
  IconMoodSad,
  IconSearch,
} from "@tabler/icons-react";
import _ from "lodash";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { searchAssets } from "../api/assets";
import { Asset, AssetModel, AssetObject } from "../api/types";
import { catchErrorAndShow } from "../utils";

const AssetObjectCard: React.FC<{
  asset: Asset;
  assetObject: AssetObject;
  maxHeight?: boolean;
}> = ({ asset, assetObject, maxHeight }) => {
  const { t } = useTranslation();

  const [assetModel, assetObjectModel] = useMemo(() => {
    const assetModel = new AssetModel(asset);
    const assetObjectModel = assetModel.getObject(assetObject.id);

    if (!assetObjectModel) {
      throw new Error("Asset object not found");
    }

    return [assetModel, assetObjectModel];
  }, [asset, assetObject.id]);

  const features = useMemo(() => {
    return [
      {
        label: t("catalogue.card.asset", "Asset"),
        value: assetModel.data.name,
        icon: IconBox,
      },
      {
        label: t("catalogue.card.createdAt", "Uploaded"),
        value: assetObjectModel.createdAt.toLocaleString(),
        icon: IconClock,
      },
      {
        label: t("catalogue.card.accessLevel", "Access level"),
        value: <Badge color="gray">{assetModel.data.access_level}</Badge>,
        icon: IconLockAccess,
      },
    ];
  }, [t, assetModel, assetObjectModel]);

  return (
    <Card
      shadow="sm"
      p="lg"
      radius="md"
      withBorder
      style={{ height: maxHeight ? "100%" : "inherit" }}
    >
      <Group position="apart" mb="xs">
        <Text weight={500} truncate>
          {assetObjectModel.humanName}
        </Text>
        {assetObjectModel.parsedKey?.ext && (
          <Badge color="pink" variant="light">
            {assetObjectModel.parsedKey.ext.toUpperCase()}
          </Badge>
        )}
      </Group>
      <Button
        variant="light"
        leftIcon={<IconExternalLink size="1em" />}
        fullWidth
        mt="md"
        mb="md"
        radius="md"
        target="_blank"
        component={Link}
        to={`/assets/${asset.id}/objects/show/${assetObject.id}`}
      >
        {t("catalogue.card.view", "View details")}
      </Button>
      <Stack spacing="xs">
        {features.map((feature) => (
          <Group spacing={0} position="left">
            <Text
              color="dimmed"
              size="sm"
              style={{ display: "flex", alignItems: "center" }}
              mr="xs"
            >
              <feature.icon size="1rem" style={{ marginRight: "0.25rem" }} />
              {feature.label}
            </Text>
            <Text size="sm" truncate>
              {feature.value}
            </Text>
          </Group>
        ))}
      </Stack>
      {assetObjectModel.description && (
        <Text mt="md" size="sm" color="dimmed" lineClamp={5}>
          {assetObjectModel.description}
        </Text>
      )}
    </Card>
  );
};

export const Catalogue: React.FC = () => {
  const { t } = useTranslation();

  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [includeMine, setIncludeMine] = useState<boolean>(false);
  const [touched, setTouched] = useState<boolean>(false);

  const [assets, setAssets] = useState<{ [k: string]: any }[] | undefined>(
    undefined
  );

  const { open } = useNotification();

  const onSearch = useCallback(() => {
    if (!open) {
      return;
    }

    setIsLoading(true);
    setTouched(true);

    searchAssets({
      searchQuery,
      excludeMine: !includeMine,
    })
      .then((res) => {
        console.debug(res);
        setAssets(res);
        setIsLoading(false);
      })
      .catch(_.partial(catchErrorAndShow, open, undefined))
      .then(() => {
        setIsLoading(false);
      });
  }, [searchQuery, includeMine, open]);

  useEffect(() => {
    if (!open) {
      return;
    }

    setIsLoading(true);
    setIncludeMine(false);

    searchAssets({
      searchQuery: "",
      excludeMine: true,
    })
      .then((res) => {
        console.debug(res);
        setAssets(res);
        setIsLoading(false);
      })
      .catch(_.partial(catchErrorAndShow, open, undefined))
      .then(() => {
        setIsLoading(false);
      });
  }, [open]);

  const numResults = useMemo(() => {
    if (!assets) {
      return undefined;
    }

    return _.chain(assets)
      .map((asset) => (asset.objects && asset.objects.length) || 0)
      .sum()
      .value();
  }, [assets]);

  return (
    <>
      <LoadingOverlay visible={isLoading} />
      <Group mt="xl" position="left" style={{ flexWrap: "nowrap" }}>
        <Box mr="lg">
          <IconDatabaseSearch size={72} color="gray" />
        </Box>
        <Stack>
          <Title>{t("catalogue.title", "Catalogue of datasets")}</Title>
          <Text color="dimmed">
            {t(
              "catalogue.description",
              "Browse datasets uploaded to the MODERATE platform"
            )}
          </Text>
        </Stack>
      </Group>
      <Group mt="xl" position="left">
        <TextInput
          style={{ flexGrow: 0.88 }}
          size="lg"
          radius="md"
          icon={<IconSearch size={14} />}
          placeholder={t("catalogue.placeholder", "Search query")}
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.currentTarget.value)}
        />
        <Button
          variant="light"
          size="lg"
          radius="md"
          uppercase
          style={{ flexGrow: 0.12 }}
          onClick={onSearch}
        >
          {t("catalogue.button", "Search")}
        </Button>
      </Group>
      <Switch
        mt="md"
        checked={includeMine}
        onChange={(event) => setIncludeMine(event.currentTarget.checked)}
        label={t("catalogue.includeMine", "Include my own datasets")}
      />
      {assets !== undefined && assets.length > 0 && (
        <Stack mt="xl">
          {numResults !== undefined && (
            <Group position="apart" grow>
              <Title order={3}>
                {touched
                  ? t("catalogue.searchResults", "Search results")
                  : t("catalogue.latest", "Latest datasets")}
              </Title>
              <Text color="dimmed" align="right">
                {numResults} {t("catalogue.numFound", "results found")}
              </Text>
            </Group>
          )}
          <Grid>
            {assets.map((asset) =>
              asset.objects.map((assetObject: { [k: string]: any }) => (
                <Grid.Col md={4} key={`${asset.id}-${assetObject.id}`}>
                  <AssetObjectCard
                    asset={asset as Asset}
                    assetObject={assetObject as AssetObject}
                    maxHeight
                  />
                </Grid.Col>
              ))
            )}
          </Grid>
        </Stack>
      )}
      {assets !== undefined && assets.length === 0 && (
        <Alert
          mt="xl"
          icon={<IconMoodSad size={32} />}
          title={
            <Title order={3}>
              {t("catalogue.noResults", "No results found")}
            </Title>
          }
          color="purple"
        >
          {t(
            "catalogue.noResultsDescription",
            "Please try refining your search query"
          )}
        </Alert>
      )}
    </>
  );
};
