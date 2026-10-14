import type { Dialect, ApiVersion, ReferencesSchema } from './types'

export interface FutarClientConfig {
  apiKey: string
  dialect?: Dialect
  version?: ApiVersion
  appVersion?: string
  baseUrl?: string
}

export interface RequestParams {
  [key: string]: string | number | boolean | string[] | number[] | undefined
}

export interface EndpointOptions {
  dialect?: Dialect
  version?: ApiVersion
  appVersion?: string
  includeReferences?: ReferencesSchema[]
  headers?: Record<string, string>
}

export function createClient(config: FutarClientConfig) {
  const { apiKey, baseUrl = 'https://futar.bkk.hu/api/query/v1/ws' } = config

  async function request<T>(
    path: string,
    params: RequestParams = {},
    options: EndpointOptions = {},
    method: 'GET' | 'POST' = 'GET',
    body?: unknown
  ): Promise<T> {
    const dialect = options.dialect ?? config.dialect ?? 'otp'
    const query = new URLSearchParams()

    query.set('key', apiKey)
    if (options.version ?? config.version) {
      query.set('version', String(options.version ?? config.version))
    }
    if (options.appVersion ?? config.appVersion) {
      query.set('appVersion', options.appVersion ?? config.appVersion!)
    }
    if (options.includeReferences?.length) {
      query.set('includeReferences', options.includeReferences.join(','))
    }

    for (const [key, value] of Object.entries(params)) {
      if (value === undefined) continue
      if (Array.isArray(value)) {
        for (const v of value) {
          query.append(key, String(v))
        }
      } else {
        query.set(key, String(value))
      }
    }

    const url = `${baseUrl}/${dialect}${path}?${query.toString()}`

    const fetchOptions: RequestInit = { method }
    const headers: Record<string, string> = {}
    if (options.headers) {
      Object.assign(headers, options.headers)
    }
    if (body && method === 'POST') {
      headers['Content-Type'] = 'application/json'
      fetchOptions.body = JSON.stringify(body)
    }
    if (Object.keys(headers).length) {
      fetchOptions.headers = headers
    }

    const res = await fetch(url, fetchOptions)

    if (res.status === 304) {
      throw new Error('NOT_MODIFIED')
    }
    if (res.status === 302) {
      return res.headers.get('location') as unknown as T
    }
    if (!res.ok) {
      const text = await res.text().catch(() => '')
      throw new Error(`HTTP ${res.status}: ${text}`)
    }

    return res.json()
  }

  return { request }
}

export type FutarClient = ReturnType<typeof createClient>
