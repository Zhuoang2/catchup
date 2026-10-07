declare module 'node:fs' {
  export function readFileSync(path: string, encoding: 'utf8'): string
  export function readFileSync(path: string): Uint8Array
  export function mkdtempSync(prefix: string): string
  export function rmSync(path: string, options: { recursive: boolean; force: boolean }): void
}
declare module 'node:os' { export function tmpdir(): string }
declare module 'node:path' { export function join(...parts: string[]): string }
declare module 'node:child_process' {
  export function execFileSync(command: string, args: string[]): Uint8Array
}
declare module 'node:vm' {
  export function runInNewContext(code: string, context: object): unknown
}
