export interface AddFileOptions {
  fileId: number
  file: File
  filename: string
  onProgress?: (loaded: number) => void
  onEnd?: () => void
  onAbort?: () => void
}

export interface FileInfo {
  filename: string
  content_type: string
  size: number
}

export interface Upload {
  id: number
  filename: string
  content_type: string
  state: string
  created: string
  checksum_client: string
  checksum_server: string
}

export type PendingUpload = {
  jobId: number
  filename: string
  filesize: number
}

export type RegisteredUpload = {
  jobId: number
  serverId: number
  serverFilename: string
  filesize: number
  transferred: number
  checksumProgress: number
  startedAt: Date
}

export interface UserInfo {
  username: string
  email: string
  locale: string
  admin: boolean
  can_upload: boolean
}

export interface DownloadableFile {
  filename: string
  type: string
  size: number
  modified: string
}
