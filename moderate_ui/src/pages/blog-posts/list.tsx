import { IResourceComponentsProps } from "@refinedev/core";
import { MantineListInferencer } from "@refinedev/inferencer/mantine";
import { usePing } from "../../api/ping";

export const BlogPostList: React.FC<IResourceComponentsProps> = () => {
  return <MantineListInferencer />;
};
