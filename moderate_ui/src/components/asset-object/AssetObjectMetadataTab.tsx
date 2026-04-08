import { Loader, Title } from "@mantine/core";
import { useTranslate } from "@refinedev/core";
import React from "react";
import { AssetObjectModel } from "../../api/types";
import { useNftMetadata } from "../../hooks";
import { KeyValuesStack } from "../KeyValuesStack";

interface AssetObjectMetadataTabProps {
  assetObjectModel: AssetObjectModel;
}

/**
 * Simple tab component displaying asset object metadata
 */
export const AssetObjectMetadataTab: React.FC<AssetObjectMetadataTabProps> = ({
  assetObjectModel,
}) => {
  const t = useTranslate();
  const { isLoading: isNftLoading, nftMetadata } =
    useNftMetadata(assetObjectModel);

  const fieldHelp: { [key: string]: string } = {
    name: t(
      "assetObjects.metadataHelp.name",
      "The display name of the object.",
    ),
    key: t(
      "assetObjects.metadataHelp.key",
      "The unique path identifier for the object in the storage system.",
    ),
    created_at: t(
      "assetObjects.metadataHelp.createdAt",
      "The timestamp when this object was created.",
    ),
    sha256_hash: t(
      "assetObjects.metadataHelp.sha256Hash",
      "The SHA-256 cryptographic hash of the file, used to verify its data integrity.",
    ),
    proof_id: t(
      "assetObjects.metadataHelp.proofId",
      "The identifier for the digital proof associated with this object in the trust system.",
    ),
    series_id: t(
      "assetObjects.metadataHelp.seriesId",
      "An identifier grouping this object with related objects in a series.",
    ),
    meta: t(
      "assetObjects.metadataHelp.meta",
      "Additional technical metadata associated with the object.",
    ),
    tags: t(
      "assetObjects.metadataHelp.tags",
      "Keywords or labels assigned to the object for categorization.",
    ),
  };

  return (
    <>
      <KeyValuesStack
        obj={assetObjectModel.data}
        omitFields={["description", "id"]}
        fieldHelp={fieldHelp}
      />
      {isNftLoading && <Loader size="xs" mt="md" />}
      {nftMetadata && (
        <>
          <Title order={5} my="md">
            {t("assetObjects.nftMetadata", "NFT Information")}
          </Title>
          <KeyValuesStack
            obj={{
              address: nftMetadata.address,
              asset_id: nftMetadata.asset_id,
              owner_did: nftMetadata.owner_did,
              license: nftMetadata.license,
            }}
            fieldHelp={{
              address: t(
                "assetObjects.nftHelp.address",
                "The blockchain address of the NFT.",
              ),
              asset_id: t(
                "assetObjects.nftHelp.assetId",
                "The asset identifier in the NFT system.",
              ),
              owner_did: t(
                "assetObjects.nftHelp.ownerDid",
                "The decentralized identifier (DID) of the NFT owner.",
              ),
              license: t(
                "assetObjects.nftHelp.license",
                "The license associated with this NFT.",
              ),
            }}
          />
        </>
      )}
    </>
  );
};
