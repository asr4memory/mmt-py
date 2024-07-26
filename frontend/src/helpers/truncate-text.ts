export default function truncateText(text: string, length: number) {
  if (text.length <= length) {
    return text
  }

  return text.slice(0, length) + '\u2026'
}
