import { Group, Loader, Select, Text } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconTable } from "@tabler/icons-react";
import React, {
  ComponentPropsWithoutRef,
  forwardRef,
  useEffect,
  useState,
} from "react";
import { useTranslation } from "react-i18next";
import { searchAssets } from "../api/assets";
import { Asset, AssetModel, AssetObjectModel } from "../api/types";

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
  )
);

interface Props {
  debouncedSearchWaitMs?: number;
  onSelect?: (item: DatasetSelectOption | undefined) => void;
}

export const AssetObjectPicker: React.FC<Props> = ({
  debouncedSearchWaitMs = 1000,
  onSelect,
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
    debouncedSearchWaitMs
  );

  useEffect(() => {
    console.debug("Search query:", debouncedSearchValue);
    setIsSearching(true);

    searchAssets({
      searchQuery: debouncedSearchValue,
      excludeMine: false,
    })
      .then((resp) => {
        const responseOptions = (resp as Asset[])
          .map((item: Asset) => {
            return new AssetModel(item);
          })
          .flatMap((assetModel: AssetModel) =>
            assetModel.getObjects().map((assetObject) => ({
              value: assetObject.data.id.toString(),
              label: assetObject.humanName,
              group: assetModel.data.name,
              asset: assetModel,
              assetObject: assetObject,
            }))
          );

        console.debug("Search results:", responseOptions);
        setFoundOptions(responseOptions);
      })
      .catch((err) => {
        console.error(err);
        setFoundOptions([]);
      })
      .then(() => {
        setIsSearching(false);
      });
  }, [debouncedSearchValue]);

  useEffect(() => {
    const newOptions = currentOption
      ? [
          ...foundOptions.filter((option) => option.value !== value),
          currentOption,
        ]
      : foundOptions;

    console.debug("Updating options:", newOptions);
    setOptions(newOptions);
  }, [foundOptions, value, currentOption]);

  const handleValueChange = (value: string | null) => {
    const theCurrentOption = options.find((option) => option.value === value);

    console.debug({
      value,
      currentOption: theCurrentOption,
    });

    setValue(value);
    setCurrentOption(theCurrentOption);

    if (onSelect && theCurrentOption) {
      onSelect(theCurrentOption);
    }
  };

  return (
    <Select
      label={t("Select a dataset")}
      placeholder={t("Start typing to search your dataset catalogue")}
      nothingFound={t("No datasets found")}
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
  );
};
