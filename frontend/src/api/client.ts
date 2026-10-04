export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, options)
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const error = (
      body && typeof body === 'object' && 'error' in body
        ? body.error
        : null
    ) as { code?: string; message?: string } | null
    throw new ApiError(
      error?.code ?? 'request_failed',
      error?.message ?? `Request failed (${response.status})`,
      response.status,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
