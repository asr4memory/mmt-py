import { defineStore } from 'pinia'
import getNextFileId from '@/helpers/get-next-file-id'
import addFile from '@/helpers/add-file'
import registerUpload from '@/helpers/register-upload'
import submitChecksum from '@/helpers/submit-checksum'
import createChecksum from '@/helpers/create-checksum'
import FileStorage from '@/helpers/file-storage'
import type { PendingUpload, RegisteredUpload } from '@/types'

const storedFiles = new FileStorage()

let xhrRef: XMLHttpRequest | null = null

export const useQueueStore = defineStore({
  id: 'queue',
  state: () => {
    return {
      pending: [] as Array<PendingUpload>,
      active: null as null | RegisteredUpload,
      trayOpen: false,
    }
  },
  getters: {
    itemCount(state): number {
      let result = state.pending.length
      if (state.active) {
        result += 1
      }
      return result
    },
    percentageFile(state): number {
      if (!state.active) {
        return 0
      }
      return (state.active.transferred / state.active.filesize) * 100
    },
    percentageChecksum(state): number {
      if (!state.active) {
        return 0
      }
      return (state.active.checksumProgress / 1) * 100
    },
    isEmpty(): boolean {
      return this.itemCount === 0
    },
  },
  actions: {
    addJobsFromFiles(files: Array<File>) {
      const newPendingUploads = files.map((file: File) => {
        const id = getNextFileId()
        storedFiles.storeFile(id, file)
        return {
          jobId: id,
          filename: file.name,
          filesize: file.size
        }
      })
      this.pending = this.pending.concat(newPendingUploads)
      this.startNextJob()
      this.trayOpen = true
    },
    removeActive() {
      const activeJob = this.active
      if (activeJob) {
        storedFiles.removeFile(activeJob.jobId)
      }
      this.active = null
    },
    removeJob(idToRemove: number) {
      const index = this.pending.findIndex((upload) => upload.jobId === idToRemove)
      if (index === -1) {
        return
      }
      const firstPart = this.pending.slice(0, index)
      const lastPart = this.pending.slice(index + 1)
      this.pending = firstPart.concat(lastPart)
    },
    async startNextJob() {
      if (this.active || this.pending.length === 0) {
        return
      }

      const nextJob = this.pending[0]
      const nextJobId = nextJob.jobId
      const nextJobFile = storedFiles.getFile(nextJobId)

      const registeredUpload = await registerUpload(nextJobFile)
      if (!registeredUpload) {
        // Something did not work during upload registration
        return
      }

      const registeredJob: RegisteredUpload = {
        jobId: nextJobId,
        serverId: registeredUpload.id,
        serverFilename: registeredUpload.filename,
        filesize: nextJobFile.size,
        transferred: 0,
        checksumProgress: 0,
        startedAt: new Date()
      }

      this.active = registeredJob
      this.pending = this.pending.slice(1)

      const request = addFile({
        fileId: registeredJob.serverId,
        file: nextJobFile,
        filename: registeredJob.serverFilename,
        onProgress: (updatedTransferredValue) => {
          if (this.active) {
            this.active = {
              ...this.active,
              transferred: updatedTransferredValue
            }
          }
        },
        onEnd: () => {
          this.active = null
          this.startNextJob()
          xhrRef = null
        },
        onAbort: () => {
          // onEnd will also catch aborted uploads.
          console.log('onAbort executed')
        }
      })
      xhrRef = request

      const checksum = await createChecksum(nextJobFile, (progress) => {
        if (this.active) {
          this.active = {
            ...this.active,
            checksumProgress: progress
          }
        }
      })
      // Set checksum progress to 100% after checksum is calculated.
      if (this.active) {
        this.active = {
          ...this.active,
          checksumProgress: 1
        }
      }

      const result = await submitChecksum(registeredJob.serverId, checksum)
    }
  }
})
