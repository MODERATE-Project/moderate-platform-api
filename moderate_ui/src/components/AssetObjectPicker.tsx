import { Alert, Group, Loader, Select, Stack, Text } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconInfoCircle, IconTable } from "@tabler/icons-react";
import React, {
  ComponentPropsWithoutRef,
  forwardRef,
  useEffect,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import { searchAssetObjects } from "../api/assets";
import { AssetModel, AssetObjectModel, UploadedS3Object } from "../api/types";

export interface DatasetSelectOption {
  value: string;
  label: string;
  group: string;
  asset: AssetModel;
  assetObject: AssetObjectModel;
}

type ItemProps = DatasetSelectOption & ComponentPropsWithoutRef<"div">;

const DatasetSelectItem = forwardRef<HTMLDivElement, ItemProps>(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  ({ value, label, group, asset, assetObject, ...others }: ItemProps, ref) => (
    <div ref={ref} {...others}>
      <Group noWrap>
        <div>
          <Text size="sm">{label}</Text>
        </div>
      </Group>
    </div>
  ),
);

interface Props {
  debouncedSearchWaitMs?: number;
  onSelect?: (item: DatasetSelectOption | undefined) => void;
  fileFormat?: string | string[];
  showFormatInfo?: boolean;
  formatInfoMessage?: string;
}

export const AssetObjectPicker: React.FC<Props> = ({
  debouncedSearchWaitMs = 1000,
  onSelect,
  fileFormat,
  showFormatInfo = false,
  formatInfoMessage,
}) => {
  const { t } = useTranslation();

  const [value, setValue] = useState<string | null>(null);

  const [currentOption, setCurrentOption] = useState<
    DatasetSelectOption | undefined
  >(undefined);

  const [foundOptions, setFoundOptions] = useState<DatasetSelectOption[]>([]);
  const [options, setOptions] = useState<DatasetSelectOption[]>([]);
  const [searchValue, onSearchChange] = useState<string>("");
  const [isSearching, setIsSearching] = useState<boolean>(false);

  const [debouncedSearchValue] = useDebouncedValue(
    searchValue,
    debouncedSearchWaitMs,
  );

  useEffect(() => {
    setIsSearching(true);

    searchAssetObjects({
      searchQuery: debouncedSearchValue,
      excludeMine: false,
      fileFormat: fileFormat,
    })
      .then((resp) => {
        const responseOptions = (resp as UploadedS3Object[]).map(
          (item: UploadedS3Object) => {
            const assetModel = new AssetModel(item.asset);
            const assetObjectModel = new AssetObjectModel(item);
            return {
              value: item.id.toString(),
              label: assetObjectModel.humanName,
              group: assetModel.data.name,
              asset: assetModel,
              assetObject: assetObjectModel,
            };
          },
        );

        setFoundOptions(responseOptions);
      })
      .catch((err) => {
        console.error(err);
        setFoundOptions([]);
      })
      .finally(() => {
        setIsSearching(false);
      });
  }, [debouncedSearchValue, fileFormat]);

  useEffect(() => {
    const newOptions = currentOption
      ? [
          ...foundOptions.filter((option) => option.value !== value),
          currentOption,
        ]
      : foundOptions;

    setOptions(newOptions);
  }, [foundOptions, value, currentOption]);

  const handleValueChange = (value: string | null) => {
    const theCurrentOption = options.find((option) => option.value === value);

    setValue(value);
    setCurrentOption(theCurrentOption);

    if (onSelect && theCurrentOption) {
      onSelect(theCurrentOption);
    }
  };

  const formatDisplay = Array.isArray(fileFormat)
    ? fileFormat.join(", ").toUpperCase()
    : fileFormat?.toUpperCase() || "CSV";

  const defaultFormatMessage = t(
    "Only {{format}} files are supported for this analysis",
    {
      format: formatDisplay,
    },
  );

  return (
    <Stack spacing="xs">
      {showFormatInfo && fileFormat && (
        <Alert
          icon={<IconInfoCircle size="1rem" />}
          color="blue"
          variant="light"
        >
          {formatInfoMessage || defaultFormatMessage}
        </Alert>
      )}
      <Select
        label={t("Select a dataset")}
        placeholder={
          fileFormat
            ? t("Start typing to search your {{format}} datasets", {
                format: formatDisplay,
              })
            : t("Start typing to search your dataset catalogue")
        }
        nothingFound={
          fileFormat
            ? t("No {{format}} datasets found", { format: formatDisplay })
            : t("No datasets found")
        }
        itemComponent={DatasetSelectItem}
        value={value}
        onChange={handleValueChange}
        data={options}
        searchable
        clearable
        onSearchChange={onSearchChange}
        searchValue={searchValue}
        icon={isSearching ? <Loader size="xs" /> : <IconTable size="1em" />}
        filter={() => true}
      />
    </Stack>
  );
};
