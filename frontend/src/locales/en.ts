export default {
  components: {
    CurrentUpload: {
      upload: 'Upload',
      checksum: 'Checksum'
    },
    DownloadsTable: {
      filename: 'Filename',
      type: 'Type',
      size: 'Size',
      modified: 'Last modified',
      actions: 'Actions',
      download: 'Download file'
    },
    LoginForm: {
      username: 'Username',
      usernamePlaceholder: 'Enter username',
      password: 'Password',
      passwordPlaceholder: 'Enter password',
      submit: 'Log in'
    },
    RegistrationComplete: {
      title: 'Registration Complete',
      message: 'Thanks {username}, you are now signed up.',
      activation:
        'Please wait for our administrators to review your registration and activate your account.'
    },
    RegistrationForm: {
      title: 'Register',
      username: 'Username',
      usernamePlaceholder: 'Enter username',
      usernameHelp:
        'Your username must be 4–12 characters long, can contain letters, figures, and the - and _ characters.',
      email: 'Email address',
      emailPlaceholder: 'Enter email address',
      password: 'Password',
      passwordPlaceholder: 'Enter password',
      repeatPassword: 'Repeat password',
      repeatPasswordPlaceholder: 'Re-enter your password',
      submit: 'Register'
    },
    SiteFooter: {
      legalNotice: 'Legal Notice',
      privacy: 'Privacy',
      accessibility: 'Accessibility',
      contact: 'Contact'
    },
    SiteHeader: {
      admin: 'Admin',
      downloads: 'Downloads',
      logIn: 'Log in',
      logOut: 'Log out',
      register: 'Register',
      uploads: 'Uploads'
    },
    UploadButton: {
      label: 'Select files to upload'
    },
    UploadQueue: {
      cancel: 'Cancel'
    },
    UploadsTable: {
      id: 'Id',
      filename: 'Filename',
      mediaType: 'Media type',
      state: 'State',
      uploaded: 'Uploaded',
      actions: 'Actions',
      delete: 'Delete',
      created: 'created',
      ok: 'OK?'
    },
    UploadTray: {
      title: 'Uploads',
      expand: 'Expand upload tray'
    },
    UserProfile: {
      username: 'Username',
      email: 'Email',
      locale: 'Locale',
      locales: {
        en: 'English',
        de: 'German'
      },
      admin: 'Administrator rights',
      can_upload: 'Upload permission',
      true: 'yes',
      false: 'no'
    }
  },
  views: {
    AccessibilityView: {
      title: 'Accessibility'
    },
    AdminView: {
      title: 'Administration'
    },
    ContactView: {
      title: 'Contact'
    },
    DownloadsView: {
      title: 'Downloads'
    },
    HomeView: {
      title: 'Welcome to MMT'
    },
    LegalNoticeView: {
      title: 'Legal Notice'
    },
    LoginView: {
      title: 'Login'
    },
    NotFoundView: {
      message: 'Sorry, we could not find this page.',
      back: 'Back to homepage'
    },
    PrivacyView: {
      title: 'Privacy'
    },
    ProfileView: {
      title: 'Profile'
    },
    UploadsView: {
      confirmDelete: 'Do you really want to delete the file {filename}?',
      title: 'Uploads'
    }
  },
  password_mismatch: 'The passwords do not match.',
  username_password_mismatch: 'Username and password do not match.',
  user_not_activated: 'User has not been activated yet.',
  no_downloads_directory: 'Downloads directory does not exist for the user.',
  'TypeError: NetworkError when attempting to fetch resource.':
    'NetworkError when attempting to fetch resource.',
  'TypeError: Failed to fetch': 'NetworkError when attempting to fetch resource.',
  'Not logged in': 'Not logged in.'
}
