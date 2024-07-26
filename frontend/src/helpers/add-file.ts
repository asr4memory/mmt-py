import type { AddFileOptions } from '@/types'

const baseUrl = `${import.meta.env.VITE_API_URL}`

export default function addFile(options: AddFileOptions): XMLHttpRequest {
  const { fileId, file, filename, onProgress, onEnd, onAbort } = options

  const uploadEndPoint = `${baseUrl}/uploads/${fileId}/upload`

  const request = new XMLHttpRequest()
  request.withCredentials = true

  request.addEventListener('loadend', () => {
    if (typeof onEnd === 'function') {
      onEnd()
    }
  })

  request.addEventListener('abort', () => {
    if (typeof onAbort === 'function') {
      onAbort()
    }
  })

  request.onreadystatechange = () => {
    console.log(request.readyState)
    if (request.readyState === 4) {
      console.log(request.response)
    }
  }

  request.open('POST', uploadEndPoint)

  const formData = new FormData()
  formData.append('file', file, filename)

  const uploadObject = request.upload
  uploadObject.addEventListener('progress', (event) => {
    if (event.lengthComputable && typeof onProgress === 'function') {
      onProgress(event.loaded)
    }
  })

  request.send(formData)

  return request
}
