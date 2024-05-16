export enum AssetAccessLevel {
  PRIVATE = "private",
  PUBLIC = "public",
  VISIBLE = "visible",
}

export interface AssetObject {
  created_at: string;
  id: number;
  key: string;
  meta: { [k: string]: any } | null;
  proof_id: string | null;
  series_id: string | null;
  sha256_hash: string;
  tags: { [k: string]: any } | null;
  description: string | null;
}

export interface AssetObjectParsedKey {
  bucket: string;
  filename: string;
  uuid: string;
  ext: string;
}

export interface Asset {
  access_level: AssetAccessLevel;
  created_at: string;
  description: string;
  id: number;
  meta: { [k: string]: any } | null;
  name: string;
  objects: AssetObject[];
  username: string;
  uuid: string;
}

const REGEX_ASSET_OBJECT_KEY =
  /^([\w.-]+)\/([\w.-]+)-([\w]{8}-[\w]{4}-[\w]{4}-[\w]{4}-[\w]{12})\.(\w+)$/;

export class AssetObjectModel {
  data: AssetObject;

  constructor(data: AssetObject) {
    this.data = data;
  }

  get parsedKey(): AssetObjectParsedKey | undefined {
    const execResult = REGEX_ASSET_OBJECT_KEY.exec(this.data.key);

    if (execResult === null) {
      return undefined;
    }

    return {
      bucket: execResult[1],
      filename: execResult[2],
      uuid: execResult[3],
      ext: execResult[4],
    };
  }

  get humanName(): string {
    const parsedKey = this.parsedKey;

    if (parsedKey === undefined) {
      return this.data.key;
    }

    return parsedKey.filename
      .split("-")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  }

  get description(): string | undefined {
    const topLevelValue = this.data.description;
    const metaValue = this.data.meta?.description;
    return topLevelValue ?? metaValue ?? undefined;
  }

  get createdAt(): Date {
    return new Date(this.data.created_at);
  }
}

export class AssetModel {
  data: Asset;

  constructor(data: Asset) {
    this.data = data;
  }

  getObject(assetObjectId: number): AssetObjectModel | undefined {
    const theObject = this.data.objects.find(
      (assetObject) => assetObject.id === assetObjectId
    );

    if (theObject === undefined) {
      return undefined;
    }

    return new AssetObjectModel(theObject);
  }
}
