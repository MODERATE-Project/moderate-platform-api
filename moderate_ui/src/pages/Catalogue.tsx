import {
  ActionIcon,
  Alert,
  Anchor,
  Box,
  Button,
  Grid,
  Group,
  LoadingOverlay,
  Pagination,
  Paper,
  Popover,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useNotification } from "@refinedev/core";
import {
  IconDatabaseSearch,
  IconFolders,
  IconHelp,
  IconMoodSad,
  IconSearch,
  IconSortDescending,
  IconUser,
} from "@tabler/icons-react";
import _ from "lodash";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { searchAssetObjects } from "../api/assets";
import { Asset, AssetObject } from "../api/types";
import { AssetObjectCard } from "../components/AssetObjectCard";
import { routes } from "../utils/routes";
import { catchErrorAndShow } from "../utils";

const PAGE_SIZE_STORAGE_KEY = "catalogue_page_size";
const INCLUDE_MINE_STORAGE_KEY = "catalogue_include_mine";
const GROUP_BY_ASSET_STORAGE_KEY = "catalogue_group_by_asset";
const FILE_FORMAT_FILTER_STORAGE_KEY = "catalogue_file_format_filter";
const DATE_FILTER_STORAGE_KEY = "catalogue_date_filter";
const DEFAULT_PAGE_SIZE = 50;
const PAGE_SIZE_OPTIONS = [
  { value: "20", label: "20" },
  { value: "50", label: "50" },
  { value: "100", label: "100" },
];

// Common file formats for the dropdown
const COMMON_FORMATS = ["csv", "json", "parquet", "xlsx", "xls"];

const ContextHelp: React.FC<{ text: string }> = ({ text }) => (
  <Popover width={200} position="bottom" withArrow shadow="md">
    <Popover.Target>
      <ActionIcon variant="transparent" color="gray" size="sm" ml={4}>
        <IconHelp size={16} />
      </ActionIcon>
    </Popover.Target>
    <Popover.Dropdown>
      <Text size="xs">{text}</Text>
    </Popover.Dropdown>
  </Popover>
);

export const Catalogue: React.FC = () => {
  const { t } = useTranslation();

  const [searchQuery, setSearchQuery] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [includeMine, setIncludeMine] = useState<boolean>(() => {
    const stored = localStorage.getItem(INCLUDE_MINE_STORAGE_KEY);
    return stored === "true";
  });
  const [groupByAsset, setGroupByAsset] = useState<boolean>(() => {
    const stored = localStorage.getItem(GROUP_BY_ASSET_STORAGE_KEY);
    return stored === "true";
  });
  const [sortBy, setSortBy] = useState<string>("date");
  const [touched, setTouched] = useState<boolean>(false);
  const [pageSize, setPageSize] = useState<number>(() => {
    const stored = localStorage.getItem(PAGE_SIZE_STORAGE_KEY);
    return stored ? parseInt(stored, 10) : DEFAULT_PAGE_SIZE;
  });
  const [fileFormatFilter, setFileFormatFilter] = useState<string | null>(
    () => {
      const stored = localStorage.getItem(FILE_FORMAT_FILTER_STORAGE_KEY);
      return stored || null;
    },
  );
  const [dateFilter, setDateFilter] = useState<
    "always" | "last_week" | "last_month"
  >(() => {
    const stored = localStorage.getItem(DATE_FILTER_STORAGE_KEY);
    return (stored as "always" | "last_week" | "last_month") || "always";
  });

  const [assets, setAssets] = useState<{ [k: string]: any }[] | undefined>(
    undefined,
  );
  const [total, setTotal] = useState<number | undefined>(undefined);
  const [page, setPage] = useState<number>(1);

  const { open } = useNotification();

  const performSearch = useCallback(
    (
      q: string,
      mine: boolean,
      s: string,
      currentPage: number,
      limit?: number,
      fileFormat?: string | null,
      dateFilterParam?: "always" | "last_week" | "last_month",
    ) => {
      if (!open) return;

      setIsLoading(true);

      // If grouping by asset and sorting by name, use 'asset_name' sort
      // to ensure the groups (assets) are sorted by their name, not by the name of their first object.
      const effectiveSort = groupByAsset && s === "name" ? "asset_name" : s;
      const effectiveLimit = limit ?? pageSize;
      const offset = (currentPage - 1) * effectiveLimit;

      searchAssetObjects({
        searchQuery: q,
        excludeMine: !mine,
        sort: effectiveSort,
        limit: effectiveLimit,
        offset,
        fileFormat: fileFormat || undefined,
        dateFilter: dateFilterParam || "always",
      })
        .then((res) => {
          setAssets(res.data);
          setTotal(res.total);
          setIsLoading(false);
        })
        .catch(_.partial(catchErrorAndShow, open, undefined))
        .then(() => {
          setIsLoading(false);
        });
    },
    [open, pageSize, groupByAsset],
  );

  // Reset to page 1 whenever any filter/sort/page-size/grouping/search-query
  // dependency changes, so a new search does not land on a stale offset.
  useEffect(() => {
    setPage(1);
  }, [
    searchQuery,
    includeMine,
    sortBy,
    pageSize,
    groupByAsset,
    fileFormatFilter,
    dateFilter,
  ]);

  const onSearch = useCallback(() => {
    setTouched(true);
    // Search submit always restarts from page 1; performSearch fires via the
    // useEffect below when page (re)becomes 1 or via the explicit call here
    // when page was already 1.
    if (page === 1) {
      performSearch(
        searchQuery,
        includeMine,
        sortBy,
        1,
        undefined,
        fileFormatFilter,
        dateFilter,
      );
    } else {
      setPage(1);
    }
  }, [
    performSearch,
    searchQuery,
    includeMine,
    sortBy,
    fileFormatFilter,
    dateFilter,
    page,
  ]);

  useEffect(() => {
    if (!open) {
      return;
    }

    performSearch(
      searchQuery,
      includeMine,
      sortBy,
      page,
      undefined,
      fileFormatFilter,
      dateFilter,
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, performSearch, sortBy, fileFormatFilter, dateFilter, page]);

  const numResults = useMemo(() => {
    if (assets === undefined) {
      return undefined;
    }

    return total ?? assets.length;
  }, [assets, total]);

  const totalPages = useMemo(() => {
    if (total === undefined || pageSize <= 0) {
      return 1;
    }
    return Math.max(1, Math.ceil(total / pageSize));
  }, [total, pageSize]);

  const groupedAssets = useMemo(() => {
    if (!assets) return undefined;
    if (!groupByAsset) return undefined;

    const groups = new Map<number, { asset: Asset; objects: any[] }>();

    assets.forEach((obj) => {
      const assetId = obj.asset.id;
      let group = groups.get(assetId);
      if (!group) {
        // Important: obj.asset here might contain only ONE object in its 'objects' list
        // (the one that matched or was returned by the search query).
        // If we are grouping, we likely want the asset header to reflect the asset's metadata.
        // We are storing the asset structure from the first object we encounter.
        group = {
          asset: obj.asset,
          objects: [],
        };
        groups.set(assetId, group);
      }
      group.objects.push(obj);
    });

    return Array.from(groups.values());
  }, [assets, groupByAsset]);

  // Extract unique file formats from current results
  const availableFormats = useMemo(() => {
    if (!assets) return [];
    const formats = new Set<string>();
    assets.forEach((obj) => {
      const key = obj.key || "";
      const match = key.match(/\.([a-zA-Z0-9]+)$/);
      if (match && match[1]) {
        formats.add(match[1].toLowerCase());
      }
    });
    return Array.from(formats).sort();
  }, [assets]);

  // Combine common formats with available formats, removing duplicates
  const formatOptions = useMemo(() => {
    const allFormats = new Set([...COMMON_FORMATS, ...availableFormats]);
    return Array.from(allFormats)
      .sort()
      .map((fmt) => ({ value: fmt, label: fmt.toUpperCase() }));
  }, [availableFormats]);

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
              "Browse datasets uploaded to the MODERATE platform",
            )}
          </Text>
        </Stack>
      </Group>
      <Paper shadow="xs" p="md" mt="xl" withBorder radius="md">
        <Group position="left">
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
        <Group mt="md" position="apart">
          <Group spacing="lg">
            <Switch
              checked={includeMine}
              onChange={(event) => {
                const newValue = event.currentTarget.checked;
                setIncludeMine(newValue);
                localStorage.setItem(
                  INCLUDE_MINE_STORAGE_KEY,
                  String(newValue),
                );
                setTouched(true);
                performSearch(
                  searchQuery,
                  newValue,
                  sortBy,
                  1,
                  undefined,
                  fileFormatFilter,
                  dateFilter,
                );
              }}
              label={
                <Group spacing={4}>
                  <IconUser size={16} />
                  <Text>
                    {t("catalogue.includeMine", "Include my own datasets")}
                  </Text>
                  <ContextHelp
                    text={t(
                      "catalogue.help.includeMine",
                      "Toggle this to view private datasets you have uploaded, in addition to public ones.",
                    )}
                  />
                </Group>
              }
            />
            <Switch
              checked={groupByAsset}
              onChange={(event) => {
                const newValue = event.currentTarget.checked;
                setGroupByAsset(newValue);
                localStorage.setItem(
                  GROUP_BY_ASSET_STORAGE_KEY,
                  String(newValue),
                );
              }}
              label={
                <Group spacing={4}>
                  <IconFolders size={16} />
                  <Text>{t("catalogue.groupByAsset", "Group by asset")}</Text>
                  <ContextHelp
                    text={t(
                      "catalogue.help.groupByAsset",
                      "Enable this to group individual files (objects) under their parent dataset entity.",
                    )}
                  />
                </Group>
              }
            />
            <Group spacing={4}>
              <Select
                placeholder={t("catalogue.fileFormat", "File format")}
                data={[
                  {
                    value: "",
                    label: t("catalogue.allFormats", "All formats"),
                  },
                  ...formatOptions,
                ]}
                value={fileFormatFilter || ""}
                onChange={(val) => {
                  const newFormat = val || null;
                  setFileFormatFilter(newFormat);
                  localStorage.setItem(
                    FILE_FORMAT_FILTER_STORAGE_KEY,
                    newFormat || "",
                  );
                  if (assets) {
                    setTouched(true);
                  }
                }}
                size="sm"
                radius="md"
                clearable
                style={{ width: 140 }}
              />
              <ContextHelp
                text={t(
                  "catalogue.help.fileFormat",
                  "Filter results to show only specific file types (e.g., CSV, JSON).",
                )}
              />
            </Group>
          </Group>
          <Group spacing="xs">
            <Text size="sm" color="dimmed">
              {t("catalogue.sortBy", "Sort by")}:
            </Text>
            <Select
              data={[
                { value: "date", label: t("catalogue.sort.date", "Date") },
                { value: "name", label: t("catalogue.sort.name", "Name") },
                {
                  value: "format",
                  label: t("catalogue.sort.format", "Format"),
                },
              ]}
              value={sortBy}
              onChange={(val) => {
                const newSort = val || "date";
                setSortBy(newSort);
                if (assets) {
                  setTouched(true);
                }
              }}
              icon={<IconSortDescending size={14} />}
              size="sm"
              radius="md"
            />
            <Text size="sm" color="dimmed" ml="md">
              {t("catalogue.dateFilter", "Upload date")}:
            </Text>
            <Select
              data={[
                {
                  value: "always",
                  label: t("catalogue.dateFilter.always", "Always"),
                },
                {
                  value: "last_week",
                  label: t("catalogue.dateFilter.lastWeek", "Last week"),
                },
                {
                  value: "last_month",
                  label: t("catalogue.dateFilter.lastMonth", "Last month"),
                },
              ]}
              value={dateFilter}
              onChange={(val) => {
                const newDateFilter =
                  (val as "always" | "last_week" | "last_month") || "always";
                setDateFilter(newDateFilter);
                localStorage.setItem(DATE_FILTER_STORAGE_KEY, newDateFilter);
                if (assets) {
                  setTouched(true);
                }
              }}
              size="sm"
              radius="md"
              style={{ width: 120 }}
            />
            <Text size="sm" color="dimmed" ml="md">
              {t("catalogue.maxResults", "Max results")}:
            </Text>
            <Select
              data={PAGE_SIZE_OPTIONS}
              value={pageSize.toString()}
              onChange={(val) => {
                const newPageSize = val ? parseInt(val, 10) : DEFAULT_PAGE_SIZE;
                setPageSize(newPageSize);
                localStorage.setItem(
                  PAGE_SIZE_STORAGE_KEY,
                  newPageSize.toString(),
                );
                if (assets) {
                  setTouched(true);
                }
              }}
              size="sm"
              radius="md"
              style={{ width: 80 }}
            />
          </Group>
        </Group>
      </Paper>
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
            {!groupByAsset &&
              assets.map((obj) => (
                <Grid.Col md={4} key={obj.id}>
                  <AssetObjectCard
                    asset={obj.asset as Asset}
                    assetObject={obj as AssetObject}
                    maxHeight
                  />
                </Grid.Col>
              ))}

            {groupByAsset &&
              groupedAssets?.map((group) => (
                <Grid.Col span={12} key={group.asset.id}>
                  <Stack spacing="sm">
                    <Title
                      order={4}
                      sx={{
                        borderBottom: "1px solid #eee",
                        paddingBottom: "8px",
                      }}
                    >
                      <Anchor
                        component={Link}
                        to={routes.assetShow(group.asset.id)}
                        inherit
                        underline={false}
                        sx={(theme) => ({
                          color: "inherit",
                          "&:hover": {
                            color: theme.colors.blue[6],
                            textDecoration: "underline",
                          },
                        })}
                      >
                        {group.asset.name}
                      </Anchor>
                      <Text
                        component="span"
                        size="sm"
                        color="dimmed"
                        ml="xs"
                        weight="normal"
                      >
                        ({group.objects.length}{" "}
                        {group.objects.length === 1
                          ? t("catalogue.file", "file")
                          : t("catalogue.files", "files")}
                        )
                      </Text>
                    </Title>
                    <Grid>
                      {group.objects.map((obj) => (
                        <Grid.Col md={4} key={obj.id}>
                          <AssetObjectCard
                            asset={group.asset}
                            assetObject={obj as AssetObject}
                            maxHeight
                          />
                        </Grid.Col>
                      ))}
                    </Grid>
                  </Stack>
                </Grid.Col>
              ))}
          </Grid>
          {totalPages > 1 && (
            <Group position="center" mt="md">
              <Pagination
                total={totalPages}
                page={page}
                onChange={setPage}
                withEdges
              />
            </Group>
          )}
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
            "Please try refining your search query",
          )}
        </Alert>
      )}
    </>
  );
};
