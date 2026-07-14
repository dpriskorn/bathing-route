import { describe, expect, it } from 'vitest'
import { useRoute } from '../composables/useRoute'

describe('useRoute', () => {
  it('should be defined', () => {
    const { analyze } = useRoute()
    expect(analyze).toBeDefined()
  })
})
