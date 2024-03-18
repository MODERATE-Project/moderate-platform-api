import { DataProvider } from "@refinedev/core";
import axios, { AxiosInstance } from "axios";
import { stringify } from "query-string";
import { axiosInstance, getHeadersWithCommon, validateFilters } from "./utils";

type MethodTypes = "get" | "delete" | "head" | "options";
type MethodTypesWithBody = "post" | "put" | "patch";

export const dataProvider = (
  apiUrl: string,
  httpClient: AxiosInstance = axiosInstance
): Omit<
  Required<DataProvider>,
  "createMany" | "updateMany" | "deleteMany" | "getMany"
> => ({
  getList: async ({ resource, pagination, filters, sorters, meta }) => {
    const url = `${apiUrl}/${resource}`;

    const { current = 1, pageSize = 10, mode = "server" } = pagination ?? {};
    const paginationOffset = pageSize * (current - 1);

    const { method } = meta ?? {};
    const headersFromMeta = getHeadersWithCommon(meta);
    const requestMethod = (method as MethodTypes) ?? "get";

    const query: {
      offset?: number;
      limit?: number;
      sorts?: string;
      filters?: string;
    } = {};

    if (mode === "server") {
      query.offset = paginationOffset;
      query.limit = pageSize;
    }

    if (sorters) {
      query.sorts = JSON.stringify(sorters);
    }

    if (filters) {
      validateFilters(filters);
      query.filters = JSON.stringify(filters);
    }

    const urlWithQuery = !!Object.keys(query).length
      ? `${url}?${stringify(query)}`
      : url;

    const { data, headers } = await httpClient[requestMethod](urlWithQuery, {
      headers: headersFromMeta,
    });

    const total = +headers["x-total-count"];

    return {
      data,
      total: total || data.length,
    };
  },

  getOne: async ({ resource, id, meta }) => {
    const url = `${apiUrl}/${resource}/${id}`;

    const { method } = meta ?? {};
    const headersFromMeta = getHeadersWithCommon(meta);
    const requestMethod = (method as MethodTypes) ?? "get";

    const { data } = await httpClient[requestMethod](url, {
      headers: headersFromMeta,
    });

    return {
      data,
    };
  },

  create: async ({ resource, variables, meta }) => {
    const url = `${apiUrl}/${resource}`;

    const { method } = meta ?? {};
    const headersFromMeta = getHeadersWithCommon(meta);
    const requestMethod = (method as MethodTypesWithBody) ?? "post";

    const { data } = await httpClient[requestMethod](url, variables, {
      headers: headersFromMeta,
    });

    return {
      data,
    };
  },

  update: async ({ resource, id, variables, meta }) => {
    const url = `${apiUrl}/${resource}/${id}`;

    const { method } = meta ?? {};
    const headersFromMeta = getHeadersWithCommon(meta);
    const requestMethod = (method as MethodTypesWithBody) ?? "patch";

    const { data } = await httpClient[requestMethod](url, variables, {
      headers: headersFromMeta,
    });

    return {
      data,
    };
  },

  deleteOne: async ({ resource, id, variables, meta }) => {
    const url = `${apiUrl}/${resource}/${id}`;

    const { method } = meta ?? {};
    const headersFromMeta = getHeadersWithCommon(meta);
    const requestMethod = (method as MethodTypesWithBody) ?? "delete";

    const { data } = await httpClient[requestMethod](url, {
      data: variables,
      headers: headersFromMeta,
    });

    return {
      data,
    };
  },

  getApiUrl: () => {
    return apiUrl;
  },

  custom: async ({
    url,
    method,
    filters,
    sorters,
    payload,
    query,
    headers,
  }) => {
    let requestUrl = `${url}?`;

    if (sorters) {
      const sortQuery = { sorts: JSON.stringify(sorters) };
      requestUrl = `${requestUrl}&${stringify(sortQuery)}`;
    }

    if (filters) {
      const filterQuery = { filters: JSON.stringify(filters) };
      requestUrl = `${requestUrl}&${stringify(filterQuery)}`;
    }

    if (query) {
      requestUrl = `${requestUrl}&${stringify(query)}`;
    }

    const headersWithCommon = Object.assign(
      axios.defaults.headers.common,
      headers
    );

    let axiosResponse;

    switch (method) {
      case "put":
      case "post":
      case "patch":
        axiosResponse = await httpClient[method](url, payload, {
          headers: headersWithCommon,
        });
        break;
      case "delete":
        axiosResponse = await httpClient.delete(url, {
          data: payload,
          headers: headersWithCommon,
        });
        break;
      default:
        axiosResponse = await httpClient.get(requestUrl, {
          headers: headersWithCommon,
        });
        break;
    }

    const { data } = axiosResponse;

    return Promise.resolve({ data });
  },
});
