import CryptoJS from 'crypto-js'

const deriveKey = (password: string) => {
  return CryptoJS.SHA256(password)
}

const numberToBytes = (val: number) => {
  const arr = BigUint64Array.from([BigInt(val)])
  return CryptoJS.lib.WordArray.create(new Uint8Array(arr.buffer).slice(0, 8))
}

export const generateLoginToken = (password: string, timestamp: number) => {
  const nonce = CryptoJS.lib.WordArray.random(24)
  const timestampBytes = numberToBytes(timestamp)

  const data = nonce.clone().concat(timestampBytes)
  const iv = CryptoJS.lib.WordArray.random(16)
  const key = deriveKey(password)

  const encrypted = CryptoJS.AES.encrypt(data, key, {
    iv: iv,
    mode: CryptoJS.mode.CBC
  })

  return [
    nonce.toString(CryptoJS.enc.Hex),
    iv.clone().concat(encrypted.ciphertext).toString(CryptoJS.enc.Hex)
  ]
}

export const verifyLoginToken = (password: string, timestamp: number, tokenHex: string, nonceHex: string) => {
  const nonce = CryptoJS.enc.Hex.parse(nonceHex)
  const token = CryptoJS.enc.Hex.parse(tokenHex)
  const iv = CryptoJS.lib.WordArray.create(token.words.slice(0, 4))

  const ciphertext = CryptoJS.lib.WordArray.create(token.words.slice(4))
  const key = deriveKey(password)

  const decrypted = CryptoJS.AES.decrypt(CryptoJS.lib.CipherParams.create({
    ciphertext
  }), key, {
    iv: iv,
    mode: CryptoJS.mode.CBC
  })

  const decryptedNonce = CryptoJS.lib.WordArray.create(decrypted.words.slice(0, 6))
  const decryptedTimestamp = CryptoJS.lib.WordArray.create(decrypted.words.slice(6, 8))

  return nonce.toString() === decryptedNonce.toString() && numberToBytes(timestamp).toString() === decryptedTimestamp.toString()
}