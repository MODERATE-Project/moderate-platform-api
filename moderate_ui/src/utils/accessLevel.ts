import { AssetAccessLevel } from "../api/types";

/**
 * Color mapping for access level badges
 * Extracted to ensure consistency across all components
 */
export const ACCESS_LEVEL_COLORS: Record<AssetAccessLevel, string> = {
  [AssetAccessLevel.PRIVATE]: "red",
  [AssetAccessLevel.VISIBLE]: "cyan",
  [AssetAccessLevel.PUBLIC]: "green",
};

/**
 * Tooltip text for access level badges
 * Unified descriptions matching existing UI patterns
 */
export const ACCESS_LEVEL_TOOLTIPS: Record<AssetAccessLevel, string> = {
  [AssetAccessLevel.PRIVATE]: "Private: Only visible and downloadable by you",
  [AssetAccessLevel.VISIBLE]:
    "Visible: Searchable by everyone, but only downloadable by you",
  [AssetAccessLevel.PUBLIC]: "Public: Visible and downloadable by everyone",
};

/**
 * Translation keys for access level tooltips
 * Used with i18n for internationalization support
 * Reuses existing translation keys for backward compatibility
 */
export const ACCESS_LEVEL_TOOLTIP_KEYS: Record<AssetAccessLevel, string> = {
  [AssetAccessLevel.PRIVATE]: "asset.fields.accessLevelPrivate",
  [AssetAccessLevel.VISIBLE]: "asset.fields.accessLevelVisible",
  [AssetAccessLevel.PUBLIC]: "asset.fields.accessLevelPublic",
};
