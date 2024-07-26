import { fetchWrapper } from '@/helpers/fetch-wrapper'
import type { FileInfo } from '@/types'

const baseUrl = import.meta.env.VITE_API_URL

export default function registerUpload(file: File) {
  const fileInfo: FileInfo = {
    filename: file.name,
    content_type: file.type,
    size: file.size
  }

  const resultPromise = fetchWrapper.post(`${baseUrl}/uploads/create`, fileInfo).catch((err) => {
    console.log(err) // TODO: Associate error with upload.
    return null
  })
  return resultPromise
}
