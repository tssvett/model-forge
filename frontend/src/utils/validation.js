export const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10 MB
export const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const ALLOWED_EXTENSIONS = '.jpg, .jpeg, .png, .webp'

export function validateFile(file) {
  if (!ALLOWED_TYPES.includes(file.type)) {
    return { valid: false, error: `Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS}` }
  }
  if (file.size > MAX_FILE_SIZE) {
    return { valid: false, error: `File too large. Maximum size: 10 MB` }
  }
  return { valid: true, error: null }
}
