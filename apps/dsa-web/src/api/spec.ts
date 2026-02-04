import rawSpec from '../../../../docs/architecture/api_spec.json';

type HttpMethod = 'get' | 'post' | 'put' | 'patch' | 'delete';

interface ApiOperation {
  operationId?: string;
}

interface ApiSpec {
  servers?: Array<{ url: string }>;
  paths?: Record<string, Partial<Record<HttpMethod, ApiOperation>>>;
}

// 将 api_spec.json 作为单一真相来源，避免硬编码接口路径
const apiSpec = rawSpec as ApiSpec;

export const apiBaseUrl = (() => {
  const url = apiSpec.servers?.[0]?.url;
  if (!url) {
    throw new Error('api_spec.json 未提供 servers[0].url');
  }
  return url;
})();

export const getOperation = (operationId: string): { path: string; method: HttpMethod } => {
  const methods: HttpMethod[] = ['get', 'post', 'put', 'patch', 'delete'];
  const entries = Object.entries(apiSpec.paths ?? {});

  for (const [path, config] of entries) {
    for (const method of methods) {
      const op = config?.[method];
      if (op?.operationId === operationId) {
        return { path, method };
      }
    }
  }

  throw new Error(`api_spec.json 中未找到 operationId: ${operationId}`);
};
