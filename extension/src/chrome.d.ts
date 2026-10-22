interface CatchUpTab { id?: number; url?: string; title?: string }
interface CatchUpChrome {
  storage: { local: {
    get(keys?: string[]): Promise<Record<string, unknown>>
    set(values: Record<string, string>): Promise<void>
  } }
  tabs: {
    query(query: { active: true; currentWindow: true }): Promise<CatchUpTab[]>
    create(details: { url: string }): Promise<unknown>
  }
  scripting: {
    executeScript<T>(details: { target: { tabId: number }; func: () => T }): Promise<{ result?: T }[]>
  }
  runtime: { openOptionsPage(): void }
}
declare const chrome: CatchUpChrome
