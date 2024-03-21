import axios from "axios";
import { buildApiUrl } from "./utils";

export async function fetchPygwalkerHtml({ objectId }: { objectId: string }) {
  return axios.get(buildApiUrl("visualization", "object", objectId));
}
