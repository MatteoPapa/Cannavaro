import ky from 'ky'


interface IErrorResponse {
  error: true
  errorMessage: string;
}

const isErrorResponse = (obj: unknown): obj is IErrorResponse => {
  return (obj as IErrorResponse)?.error !== undefined
    && typeof (obj as IErrorResponse).error === 'boolean'
    && (obj as IErrorResponse).error
}

export type User = {
  id: number
}

export type LoginFirst = {
  token: string
  timestamp: number
}

export type LoginSecond = {
  nonce: string
}

export type OptionalUser = { logged: false } | ({ logged: true } & User)

export type WorksheetLight = Pick<Worksheet, 'id' | 'title' | 'sharable' | 'owner'>

export type WorksheetCell = { x: number, y: number, content: string }

export type WorksheetShare = {
  token: string
}

export type Worksheet = {
  id: string
  title: string
  sharable: boolean
  owner: {
    id: number
    username: string
  },
  guests: Array<{
    id: number
    username: string
  }>,
  cells: Array<WorksheetCell & {
    evaluated?: string
  }>
  comments: Array<{
    id: number
    x: number
    y: number
    created: number;
    content: string
    owner: {
      id: number
      username: string
    }
  }>
}

export class APIError extends Error {
  error: string

  constructor(resp: IErrorResponse) {
    super(`An error has occurred: ${resp.errorMessage}`)
    this.error = resp.errorMessage
  }
}

class API {
  private ky: typeof ky

  constructor() {
    this.ky = ky.extend({
      throwHttpErrors: false
    })
  }

  private async get(path: string): Promise<unknown> {
    const res = await this.ky.get(`/api${path}`, {})

    const body = await res.json<unknown>()
    if (isErrorResponse(body)) {
      throw new APIError(body)
    }

    return body
  }

  private async post(path: string, data: unknown): Promise<unknown> {
    const res = await this.ky.post(`/api${path}`, {
      body: JSON.stringify(data),
      headers: {
        'Content-Type': 'application/json'
      }
    })

    const body = await res.json<unknown>()
    if (isErrorResponse(body)) {
      throw new APIError(body)
    }

    return body
  }

  async user(): Promise<OptionalUser> {
    return (await this.get('/user')) as OptionalUser
  }

  async loginFirst(username: string): Promise<LoginFirst> {
    return (await this.post('/login/first', {username})) as LoginFirst
  }

  async loginSecond(token: string): Promise<LoginSecond> {
    return (await this.post('/login/second', {token})) as LoginSecond
  }

  async loginThird(nonce: string): Promise<User> {
    return (await this.post('/login/third', {nonce})) as User
  }

  async register(username: string, password: string) {
    await this.post('/register', {username, password})
  }

  async logout(): Promise<User> {
    return (await this.post('/logout', {})) as User
  }

  async getWorksheets(): Promise<Array<WorksheetLight>> {
    return (await this.get('/worksheets')) as Array<WorksheetLight>
  }

  async getWorksheet(id: string): Promise<Worksheet> {
    return (await this.get(`/worksheet/${id}?timestamp=${Date.now()}`)) as Worksheet
  }

  async createWorksheet(title: string, sharable: boolean): Promise<WorksheetLight> {
    return (await this.post('/worksheets', {title, sharable})) as WorksheetLight
  }

  async saveWorksheet(id: string, cells: Array<WorksheetCell>): Promise<Worksheet> {
    return (await this.post(`/worksheet/${id}?timestamp=${Date.now()}`, {cells})) as Worksheet
  }

  async shareWorksheet(id: string): Promise<WorksheetShare> {
    return (await this.post(`/worksheet/${id}/share`, {})) as WorksheetShare
  }

  async acceptWorksheetInvite(id: string, token: string): Promise<void> {
    await this.post(`/worksheet/${id}/invite/${token}`, {})
  }

  async createComment(worksheetId: string, x: number, y: number, content: string): Promise<void> {
    await this.post(`/worksheet/${worksheetId}/comments`, {x, y, content})
  }
}

export default new API()