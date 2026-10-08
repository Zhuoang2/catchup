export function parseDate(value: string): Date {
  // Date-only feed values are calendar dates, not UTC instants.
  return new Date(/^\d{4}-\d\d-\d\d$/.test(value) ? `${value}T00:00:00` : value)
}

export function longDate(value: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  }).format(parseDate(value))
}

export function shortTime(value: string): string {
  return new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit' }).format(parseDate(value))
}

export function shortDateTime(value: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(parseDate(value))
}

export function shortDate(value: string): string {
  return new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).format(parseDate(value))
}

export function localDateISO(date: Date): string {
  return [date.getFullYear(), String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0')].join('-')
}

export function dateTime(value: string): string {
  return `${longDate(value)}, ${shortTime(value)}`
}

export function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? '' : 's'}`
}

export function tokenTotals(prompt?: number | null, completion?: number | null): string {
  return prompt == null || completion == null ? 'Tokens: not reported'
    : `Tokens: ${prompt.toLocaleString('en-US')} in / ${completion.toLocaleString('en-US')} out`
}
