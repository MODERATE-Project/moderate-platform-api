import { CrudFilters, HttpError, MetaQuery } from "@refinedev/core";
import axios from "axios";

export const getHeadersFromMeta = (
  meta: MetaQuery | undefined
): { [k: string]: string } => {
  const { headers: headersFromMeta } = meta ?? {};
  return Object.assign(axios.defaults.headers.common, headersFromMeta);
};

export const validateFilters = (filters?: CrudFilters) => {
  const supportedOperators: string[] = [
    "eq",
    "ne",
    "lt",
    "gt",
    "lte",
    "gte",
    "in",
    "nin",
    "contains",
  ];

  for (const filter of filters || []) {
    if (!supportedOperators.includes(filter.operator)) {
      const errMsg = `Operator "${filter.operator}" is not supported`;
      console.warn(errMsg);

      const customError: HttpError = {
        message: errMsg,
        statusCode: 400,
      };

      throw customError;
    }
  }
};

export { axiosInstance } from "./axios";
