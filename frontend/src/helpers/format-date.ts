export default function formatDate(
  date: Date | string,
  locale: string,
  useLongForm: boolean = false
): string {
  let input: Date
  if (typeof date === 'string') {
    input = new Date(date)
  } else {
    input = date
  }

  let result: string
  if (useLongForm) {
    result = `${input.toLocaleDateString(locale)} ${input.toLocaleTimeString(locale)}`
  } else {
    result = input.toLocaleDateString(locale)
  }

  return result
}
