import { DependencyList, useCallback } from 'react'
import { APIError } from './api'

export const useAsyncCallback = <T extends (...args: unknown[]) => Promise<void>>(func: T, deps: DependencyList) => {
  return useCallback<(...args: Parameters<T>) => void>((...args: Parameters<T>) => {
    (async () => {
      try {
        await func(args)
      } catch (e) {
        console.error(e)
        if (e instanceof APIError) {
          alert(e.error)
        } else {
          alert(`An unexpected error occurred: ${e}`)
        }
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
}

export const cellXYToCoords = (x: number, y: number): string => {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

  let xx
  const i = Math.floor(x / alphabet.length)
  if (i > 0) {
    xx = `${alphabet[i - 1]}${alphabet[x % alphabet.length]}`
  } else {
    xx = alphabet[x % alphabet.length]
  }

  return xx + (y + 1).toString(10)
}

export const hexEncode = (val: string): string => {
  if (val === undefined) {
    return undefined
  } else if (val === null) {
    return null
  }

  return unescape(encodeURIComponent(val)).split('').map((v) => v.charCodeAt(0).toString(16)).join('')
}

export const hexDecode = (val: string): string => {
  if (val === undefined) {
    return undefined
  } else if (val === null) {
    return null
  }

  let res = ''
  for (let i = 0; i < val.length; i += 2)
    res += String.fromCharCode(parseInt(val.substring(i, i + 2), 16))
  return res
}