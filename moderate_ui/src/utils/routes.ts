/**
 * Centralized route construction utilities
 * Single source of truth for all application routes
 */

export const routes = {
  // Home routes
  home: () => "/",
  catalogue: () => "/catalogue",
  login: () => "/login",

  // Asset routes
  assetList: () => "/assets",
  assetShow: (assetId: string | number) => `/assets/show/${assetId}`,
  assetEdit: (assetId: string | number) => `/assets/edit/${assetId}`,
  assetCreate: () => "/assets/create",

  // Asset object routes
  assetObjectShow: (assetId: string | number, objectId: string | number) =>
    `/assets/${assetId}/objects/show/${objectId}`,

  assetObjectExplore: (assetId: string | number, objectId: string | number) =>
    `/assets/${assetId}/objects/explore/${objectId}`,

  // Workflow/Notebook routes
  workflowExploratory: () => "/workflows/exploratory",
  workflowMatrixProfile: () => "/workflows/matrix-profile",
  workflowSyntheticLoad: () => "/workflows/synthetic-load",
};
